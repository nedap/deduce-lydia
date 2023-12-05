from typing import Iterable, Optional

import docdeid as dd
import hyperscan

from deduce.tokenizer import DeduceTokenizer


def on_match(match):
    return


HYPERSCAN_DB = hyperscan.Database()
# HS_FLAG_SOM_LEFTMOST set so the left offset is also reported in the match
patterns = (
    # expression,  id, flags
    (
        r"\w+|[\n\r\t]|.(?<! )",
        0,
        hyperscan.HS_FLAG_SOM_LEFTMOST | hyperscan.FLAG_CASELESS,
    ),
)
expressions, ids, flags = zip(*patterns)
HYPERSCAN_DB.compile(
    expressions=expressions, ids=ids, elements=len(patterns), flags=flags
)

print(HYPERSCAN_DB.info().decode())

print("finished compiling")


# todo: check if more readable version is truly equivalent
# _TOKENIZER_PATTERN_HYPERSCAN = regex.compile(r"\w+|[\n\r\t]|.(?<! )", flags=re.I | re.M)
# _TOKENIZER_PATTERN_HYPERSCAN = regex.compile(r"\w+|[\n\r\t]|[^ ]]", flags=re.I | re.M)


class HyperscanDeduceTokenizer(DeduceTokenizer):  # pylint: disable=R0903
    """
    Tokenizes text, where a token is any sequence of alphanumeric characters (case
    insensitive), a single newline/tab character, or a single special character. It does
    not include whitespaces as tokens.

    Arguments:
        merge_terms: An iterable of strings that should not be split (i.e. always
        returned as tokens).
    """

    def __init__(self, merge_terms: Optional[Iterable] = None) -> None:
        super().__init__()

        self._pattern = HYPERSCAN_DB

    @staticmethod
    def _join_tokens(text: str, tokens: list[dd.tokenize.Token]) -> dd.tokenize.Token:
        """
        Join a list of tokens into a single token. Does this by creating a new token,
        that ranges from the first token start char to the last token end char.

        Args:
            text: The original text.
            tokens: The input tokens.

        Returns:
            The output token.
        """

        return dd.Token(
            text=text[tokens[0].start_char : tokens[-1].end_char],
            start_char=tokens[0].start_char,
            end_char=tokens[-1].end_char,
        )

    def _merge(
        self, text: str, tokens: list[dd.tokenize.Token]
    ) -> list[dd.tokenize.Token]:
        """
        Merge a list of tokens based on the trie.

        Args:
            tokens: A list of tokens, with merge_terms split.

        Returns:
            A list of tokens, with merge_terms joined in single tokens.
        """

        tokens_text = [token.text for token in tokens]
        tokens_merged = []
        i = 0

        while i < len(tokens):
            longest_matching_prefix = self._trie.longest_matching_prefix(
                tokens_text[i:]
            )

            if longest_matching_prefix is None:
                tokens_merged.append(tokens[i])
                i += 1

            else:
                num_tokens_to_merge = len(longest_matching_prefix)
                tokens_merged.append(
                    self._join_tokens(text, tokens[i : i + num_tokens_to_merge])
                )
                i += num_tokens_to_merge

        return tokens_merged

    def _split_text(self, text: str) -> list[dd.tokenize.Token]:
        """
        Split text, based on the regexp pattern.

        Args:
            text: The input text.

        Returns:
            A list of tokens.
        """

        tokens = []
        result = []

        # define function to be called on match
        def on_match(id: int, froms: int, to: int, flags: int) -> Optional[bool]:
            result.append((froms, to))

        HYPERSCAN_DB.scan(text.encode("utf-8"), match_event_handler=on_match)

        for start_ch, end_ch in result:
            tokens.append(
                dd.Token(
                    text=text[start_ch:end_ch],
                    start_char=start_ch,
                    end_char=end_ch,
                )
            )

        if self._trie is not None:
            tokens = self._merge(text, tokens)

        return tokens
