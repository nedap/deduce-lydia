from typing import Any, Iterable, Optional

import docdeid as dd
import hyperscan

from deduce.tokenizer import DeduceTokenizer

HYPERSCAN_DB = hyperscan.Database()
# HS_FLAG_SOM_LEFTMOST set so the left offset is also reported in the match
# HS_FLAG_UCP to deal with unicode, which needs HS_FLAG_UTF8 as a dependency
patterns = (
    # expression,  id, flags
    (
        "( +)".encode("utf-8"),
        0,
        hyperscan.HS_FLAG_SOM_LEFTMOST | hyperscan.HS_FLAG_UCP | hyperscan.HS_FLAG_UTF8,
    ),
    (
        "([^\w\s]|[\n\r\t])".encode("utf-8"),
        1,
        hyperscan.HS_FLAG_SOM_LEFTMOST | hyperscan.HS_FLAG_UCP | hyperscan.HS_FLAG_UTF8,
    ),
)
expressions, ids, flags = zip(*patterns)
HYPERSCAN_DB.compile(
    expressions=expressions, ids=ids, elements=len(patterns), flags=flags
)


print("finished compiling")


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
        super().__init__(merge_terms=merge_terms)

        self._pattern = HYPERSCAN_DB

    def _split_text(self, text: str) -> list[dd.tokenize.Token]:
        """
        Split text, based on the regexp pattern.

        Args:
            text: The input text.

        Returns:
            A list of tokens.
        """

        special_chars, white_space_result = self.__get_hyperscan_matches(text)

        offset = 0
        words = []

        for from_ch, to_ch in white_space_result:
            if from_ch == 0:
                offset = to_ch
                continue

            # do different if any special chars in this token
            if special_chars and special_chars[0] < from_ch:
                words.extend(
                    self.__split_special_chars(text, offset, from_ch, special_chars)
                )
            else:
                w = text[offset:from_ch]
                words.append((w, offset, from_ch))
                print(f"Found match from {offset} to {from_ch} in text: {w}")

            offset = to_ch

        # append remaining token
        if offset < len(text):
            if special_chars:
                words.extend(
                    self.__split_special_chars(text, offset, len(text), special_chars)
                )
            else:
                w = text[offset : len(text)]
                words.append((w, offset, len(text)))
                print(f"Added match from {offset} to {len(text)} in text: {w}")

        tokens = [
            dd.Token(
                text=w,
                start_char=start_ch,
                end_char=end_ch,
            )
            for (w, start_ch, end_ch) in words
        ]

        if self._trie is not None:
            tokens = self._merge(text, tokens)

        return tokens

    def __get_hyperscan_matches(self, text):
        encoded_text = text.encode("utf-8")
        pos_folding = self.__create_unicode_fold_pos_dict(text)
        print(len(text), len(encoded_text))

        white_space_result = {}
        special_chars = []

        # define function to be called on match
        def on_match(
            id: int,
            from_byte: int,
            to_byte: int,
            flags: int,
            context: Optional[Any] = None,
        ) -> Optional[bool]:
            # id 0 is whitespace, id 1 is special chars
            if id == 0:
                char_pos_result = pos_folding[from_byte], pos_folding[to_byte]
                if from_byte in white_space_result:
                    # overwrite if this is the longest current match
                    cur_size = (
                        white_space_result[from_byte][1]
                        - white_space_result[from_byte][0]
                    )
                    if to_byte - from_byte > cur_size:
                        white_space_result[from_byte] = char_pos_result
                else:
                    white_space_result[from_byte] = char_pos_result
            else:
                special_chars.append(from_byte)

        HYPERSCAN_DB.scan(encoded_text, match_event_handler=on_match)

        # convert to positions in text when this is a str
        # since unicode chars are double the size of ascii chars in bytes
        special_chars = sorted(pos_folding[i] for i in special_chars)
        white_space_result = sorted(white_space_result.values())
        return special_chars, white_space_result

    def __split_special_chars(self, text, from_ch, to_ch, special_chars):
        if not special_chars:
            raise ValueError(
                "unexpected call, should already be established that there are special chars"
            )

        special_ch = special_chars.pop(0)
        if not from_ch <= special_ch < to_ch:
            raise ValueError(
                "unexpected call, should already be established that there is a special char in word"
            )

        words = []
        word_offset = from_ch
        while word_offset != to_ch:
            # if special char is reached, add as a single char
            if word_offset == special_ch:
                words.append((text[special_ch], special_ch, special_ch + 1))
                word_offset += 1
                print(
                    f"Found match inside sequence from {special_ch} to {special_ch + 1} in text: {text[special_ch]}"
                )
                # see if more special char are part of the sequence
                if special_chars and special_chars[0] < to_ch:
                    special_ch = special_chars.pop(0)
                else:
                    special_ch = None

            # add remainder of the word if there is no special char in it
            if special_ch is None and word_offset < to_ch:
                words.append((text[word_offset:to_ch], word_offset, to_ch))
                print(
                    f"Found match inside sequence from {word_offset} to {to_ch} in text: {text[word_offset:to_ch]}"
                )
                word_offset = to_ch

            # add word up until special char
            if special_ch is not None and word_offset < special_ch:
                words.append((text[word_offset:special_ch], word_offset, special_ch))
                print(
                    f"Found match inside sequence from {word_offset} to {special_ch} in text: {text[word_offset:special_ch]}"
                )
                word_offset = special_ch
        return words

    def __create_unicode_fold_pos_dict(self, text):
        positions = []
        for index, char in enumerate(text):
            positions.append(index)
            # if ord is larger than 127, it is a unicode char and requires 2 bytes in utf-8
            if ord(char) > 127:
                positions.append(index)
        return {i: v for i, v in enumerate(positions)}
