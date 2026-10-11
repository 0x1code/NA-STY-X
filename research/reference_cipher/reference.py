"""Reference implementation of the NA&STY-X v0.2 research cipher.

WARNING: experimental construction, not suitable for protecting real data.
"""

ALGORITHM_VERSION = '0.2'
BLOCK_SIZE = 16
KEY_SIZE = 32
ROUNDS = 16
SUPPORTED_ROUNDS = (8, 12, 16, 20, 24)
MASK64 = (1 << 64) - 1
GOLDEN_RATIO = 0x9E3779B97F4A7C15
BYTE_PERMUTATION = (2, 5, 0, 7, 4, 1, 6, 3)


from sbox import NASTYX_SBOX


def _rotl64(value: int, amount: int) -> int:
    return ((value << amount) | (value >> (64 - amount))) & MASK64


def expand_key(key: bytes, rounds: int = ROUNDS) -> tuple[int, ...]:
    if len(key) != KEY_SIZE:
        raise ValueError("key must be exactly 32 bytes")
    if type(rounds) is not int or rounds not in SUPPORTED_ROUNDS:
        raise ValueError("rounds must be one of 8, 12, 16, 20, 24")
    state = [int.from_bytes(key[i * 8:(i + 1) * 8], "big") for i in range(4)]
    round_keys = []
    for i in range(rounds):
        s0, s1, s2, s3 = state
        constant = (GOLDEN_RATIO * (i + 1)) & MASK64
        round_key = (s0 + _rotl64(s1, 13) + constant) & MASK64
        round_key ^= _rotl64(s2, 29) ^ s3
        round_keys.append(round_key)
        state = [s1, s2, s3, (round_key + _rotl64(s0, 7)) & MASK64]
    return tuple(round_keys)


def _round_function(value: int, round_key: int) -> int:
    mixed = (value ^ round_key).to_bytes(8, "little")
    substituted = bytes(NASTYX_SBOX[mixed[index]] for index in BYTE_PERMUTATION)
    x = int.from_bytes(substituted, "little")
    return (((x + _rotl64(x, 17)) & MASK64) ^ _rotl64(x, 41) ^ round_key) & MASK64


def encrypt_block(key: bytes, block: bytes, *, rounds: int = ROUNDS) -> bytes:
    if len(block) != BLOCK_SIZE:
        raise ValueError("block must be exactly 16 bytes")
    left = int.from_bytes(block[:8], "big")
    right = int.from_bytes(block[8:], "big")
    for round_key in expand_key(key, rounds):
        left, right = right, left ^ _round_function(right, round_key)
    return left.to_bytes(8, "big") + right.to_bytes(8, "big")


def decrypt_block(key: bytes, block: bytes, *, rounds: int = ROUNDS) -> bytes:
    if len(block) != BLOCK_SIZE:
        raise ValueError("block must be exactly 16 bytes")
    left = int.from_bytes(block[:8], "big")
    right = int.from_bytes(block[8:], "big")
    for round_key in reversed(expand_key(key, rounds)):
        left, right = right ^ _round_function(left, round_key), left
    return left.to_bytes(8, "big") + right.to_bytes(8, "big")
