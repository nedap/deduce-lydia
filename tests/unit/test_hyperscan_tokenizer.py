import docdeid as dd
import pytest

from deduce.tokenizer_hyperscan import HyperscanDeduceTokenizer


@pytest.fixture
def hyperscan_tokenizer():
    return HyperscanDeduceTokenizer()


class TestTokenizer:
    def test_split_alpha(self, hyperscan_tokenizer):
        text = "Pieter van der Zee"
        expected_tokens = [
            dd.Token(text="Pieter", start_char=0, end_char=6),
            dd.Token(text="van", start_char=7, end_char=10),
            dd.Token(text="der", start_char=11, end_char=14),
            dd.Token(text="Zee", start_char=15, end_char=18),
        ]

        assert hyperscan_tokenizer._split_text(text=text) == expected_tokens

    def test_split_nonalpha(self, hyperscan_tokenizer):
        text = "prematuur (<p3)"

        expected_tokens = [
            dd.Token(text="prematuur", start_char=0, end_char=9),
            dd.Token(text="(", start_char=10, end_char=11),
            dd.Token(text="<", start_char=11, end_char=12),
            dd.Token(text="p3", start_char=12, end_char=14),
            dd.Token(text=")", start_char=14, end_char=15),
        ]

        assert hyperscan_tokenizer._split_text(text=text) == expected_tokens

    def test_split_newline(self, hyperscan_tokenizer):
        text = "regel 1 \n gevolgd door regel 2"

        expected_tokens = [
            dd.Token(text="regel", start_char=0, end_char=5),
            dd.Token(text="1", start_char=6, end_char=7),
            dd.Token(text="\n", start_char=8, end_char=9),
            dd.Token(text="gevolgd", start_char=10, end_char=17),
            dd.Token(text="door", start_char=18, end_char=22),
            dd.Token(text="regel", start_char=23, end_char=28),
            dd.Token(text="2", start_char=29, end_char=30),
        ]

        assert hyperscan_tokenizer._split_text(text=text) == expected_tokens

    def test_join_tokens(self):
        text = "Patient was eerder opgenomen"

        tokens = [
            dd.Token(text="Patient", start_char=0, end_char=7),
            dd.Token(text="was", start_char=8, end_char=11),
            dd.Token(text="eerder", start_char=12, end_char=18),
            dd.Token(text="opgenomen", start_char=19, end_char=28),
            dd.Token(text="(", start_char=29, end_char=30),
            dd.Token(text="vorig", start_char=30, end_char=35),
            dd.Token(text="jaar", start_char=36, end_char=40),
            dd.Token(text=")", start_char=40, end_char=41),
            dd.Token(text="alhier", start_char=42, end_char=48),
            dd.Token(text=".", start_char=48, end_char=49),
        ]
        joined_token = HyperscanDeduceTokenizer._join_tokens(text, tokens[0:4])
        expected_token = dd.Token(text=text, start_char=0, end_char=28)

        assert joined_token == expected_token

    def test_unicode(self, hyperscan_tokenizer):
        expected_tokens = [
            dd.Token(text="Danée", start_char=0, end_char=5),
            dd.Token(text="is", start_char=6, end_char=8),
            dd.Token(text="cool", start_char=9, end_char=13),
        ]

        text = "Danée is cool"
        assert hyperscan_tokenizer._split_text(text=text) == expected_tokens

    def test_unicode_in_various_positions(self, hyperscan_tokenizer):
        test_sentences = ["Danée", "Daneé", "éeeee", "hoi alleé", "ésldk haiédi dksié"]
        for ts in test_sentences:
            result = hyperscan_tokenizer._split_text(text=ts)
            assert len(result) == len(ts.split(" "))

    def test_multi_patterns(self, hyperscan_tokenizer):
        # testing various combinations of special characters and whitespace at different points
        # in the text including special characters surrounded by normal chars.
        test_sentences = [
            ("abc\nuwv", "abc \n uwv"),
            ("sd#sdlk and & sdlfk&", "sd # sdlk and & sdlfk &"),
            ("abc$$def", "abc $ $ def"),
            ("! sldfi (", "! sldfi ("),
            ("sdlkfj!", "sdlkfj !"),
            ("kdi,dfg", "kdi , dfg"),
            ("sdf!!!", "sdf ! ! !"),
            ("!!!sdlfkj", "! ! ! sdlfkj"),
            ("sdflk ! dsfk", "sdflk ! dsfk"),
        ]

        for text, expeceted_outcome in test_sentences:
            result = hyperscan_tokenizer._split_text(text=text)
            chained_result = " ".join(token.text for token in result)
            assert chained_result == expeceted_outcome
