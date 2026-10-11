"""Reproducible, small-sample avalanche probe; not a security test."""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "reference_cipher"))
from reference import encrypt_block  # noqa: E402


def hamming(left: bytes, right: bytes) -> int:
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def run(samples: int, seed: int) -> tuple[float, int, int]:
    rng = random.Random(seed)
    changed, total, minimum, maximum = 0, 0, 128, 0
    for _ in range(samples):
        key = rng.randbytes(32)
        block = rng.randbytes(16)
        baseline = encrypt_block(key, block)
        for bit in range(128):
            changed_block = bytearray(block)
            changed_block[bit // 8] ^= 1 << (bit % 8)
            distance = hamming(baseline, encrypt_block(key, bytes(changed_block)))
            changed += distance
            total += 128
            minimum = min(minimum, distance)
            maximum = max(maximum, distance)
    return changed / total, minimum, maximum


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261011)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    mean, minimum, maximum = run(args.samples, args.seed)
    print("WARNING: descriptive diffusion probe only; not evidence of cryptographic security.")
    print(f"seed={args.seed} samples={args.samples} flipped_output_bits={mean * 128:.4f}/128 ")
    print(f"mean_changed_fraction={mean:.6f} per_input_bit_min={minimum} per_input_bit_max={maximum}")
