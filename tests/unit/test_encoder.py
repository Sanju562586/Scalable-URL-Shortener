"""Unit tests for the Base-62 encoder/decoder."""

import pytest
from app.core.encoder import encode, encode_padded, decode


class TestEncode:
    """Tests for encode()."""

    def test_encode_one(self):
        assert encode(1) == "1"

    def test_encode_62_is_base_rollover(self):
        assert encode(62) == "10"

    def test_encode_large_number(self):
        result = encode(238_328)
        assert result == "1000"

    def test_encode_produces_only_base62_chars(self):
        alphabet = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        for n in [1, 61, 62, 63, 1000, 999_999]:
            assert set(encode(n)).issubset(alphabet)

    def test_encode_rejects_zero(self):
        with pytest.raises(ValueError):
            encode(0)

    def test_encode_rejects_negative(self):
        with pytest.raises(ValueError):
            encode(-5)

    def test_encode_rejects_non_integer(self):
        with pytest.raises(ValueError):
            encode("abc")  # type: ignore[arg-type]


class TestEncodePadded:
    """Tests for encode_padded()."""

    def test_pads_short_codes(self):
        code = encode_padded(1, min_length=4)
        assert len(code) >= 4

    def test_does_not_truncate_long_codes(self):
        code = encode_padded(999_999_999, min_length=4)
        assert len(code) >= 4

    def test_default_min_length_is_four(self):
        code = encode_padded(1)
        assert len(code) == 4


class TestDecode:
    """Tests for decode()."""

    def test_roundtrip_small(self):
        for n in range(1, 200):
            assert decode(encode(n)) == n

    def test_roundtrip_large(self):
        for n in [62**2, 62**3, 62**4 - 1]:
            assert decode(encode(n)) == n

    def test_decode_rejects_empty_string(self):
        with pytest.raises(ValueError):
            decode("")

    def test_decode_rejects_invalid_chars(self):
        with pytest.raises(ValueError):
            decode("abc!")  # '!' not in alphabet

    def test_padded_roundtrip(self):
        code = encode_padded(42, min_length=4)
        assert decode(code) == 42
