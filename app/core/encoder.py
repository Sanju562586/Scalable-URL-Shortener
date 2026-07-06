"""
Base-62 encoding/decoding for short code generation.

Alphabet: digits (0-9) + uppercase (A-Z) + lowercase (a-z) = 62 symbols.

Strategy
--------
The auto-increment primary key from PostgreSQL is encoded into Base-62.
This guarantees:
  • Uniqueness — each ID maps to exactly one code.
  • No collision checks needed at insert time.
  • Monotonically growing length (codes stay short for a long time).
  • Reversibility for debugging/admin purposes.

Example outputs:
  encode(1)       → "1"
  encode(62)      → "10"
  encode(3844)    → "100"
  encode(238_328) → "1000"

To pad codes to a minimum length (e.g. 4 chars), use encode_padded().
"""

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(BASE62_ALPHABET)  # 62

# Reverse lookup table for O(1) decode
_CHAR_TO_INDEX: dict[str, int] = {ch: i for i, ch in enumerate(BASE62_ALPHABET)}


def encode(n: int) -> str:
    """
    Encode a positive integer to its Base-62 string representation.

    Args:
        n: A positive integer (typically a DB row ID).

    Returns:
        A non-empty Base-62 string.

    Raises:
        ValueError: If n is not a positive integer.
    """
    if not isinstance(n, int) or n <= 0:
        raise ValueError(f"encode() requires a positive integer, got {n!r}")

    chars: list[str] = []
    while n:
        n, remainder = divmod(n, BASE)
        chars.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def encode_padded(n: int, min_length: int = 4) -> str:
    """
    Same as encode() but left-pads with '0' to at least *min_length* chars.

    Args:
        n: A positive integer.
        min_length: Minimum code length (default 4).

    Returns:
        A Base-62 string of at least *min_length* characters.
    """
    code = encode(n)
    return code.zfill(min_length) if len(code) < min_length else code


def decode(code: str) -> int:
    """
    Decode a Base-62 string back to its integer representation.

    Args:
        code: A non-empty Base-62 string produced by encode().

    Returns:
        The original positive integer.

    Raises:
        ValueError: If the code contains characters outside the alphabet.
    """
    if not code:
        raise ValueError("decode() requires a non-empty string")

    result = 0
    for char in code:
        if char not in _CHAR_TO_INDEX:
            raise ValueError(
                f"Invalid Base-62 character {char!r} in code {code!r}"
            )
        result = result * BASE + _CHAR_TO_INDEX[char]
    return result
