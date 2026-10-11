"""NA&STY-X Lab: reproducible descriptive experiments, not security proofs."""
import argparse
import hashlib
import json
import math
import platform
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "reference_cipher"))
from reference import AES_SBOX, SUPPORTED_ROUNDS, encrypt_block, expand_key, _round_function


def ddt(sbox):
    """DDT[a][b] counts S(x) XOR S(x XOR a) == b, over all x."""
    n = len(sbox)
    if n < 2 or n & (n-1) or any(type(x) is not int or not 0 <= x < n for x in sbox):
        raise ValueError("S-box must map a power-of-two domain to itself")
    table = [[0]*n for _ in range(n)]
    for a in range(n):
        for x in range(n):
            table[a][sbox[x] ^ sbox[x ^ a]] += 1
    return table


def walsh(sbox):
    """W[a][b] = sum_x (-1)^(parity(a&x) XOR parity(b&S(x)))."""
    n = len(sbox)
    ddt(sbox)  # Validate the domain before transforming.
    table = [[0]*n for _ in range(n)]
    for b in range(n):
        row = [1 if (b & y).bit_count() % 2 == 0 else -1 for y in sbox]
        step = 1
        while step < n:
            for start in range(0, n, 2*step):
                for k in range(start, start+step):
                    x, y = row[k], row[k+step]
                    row[k], row[k+step] = x+y, x-y
            step *= 2
        for a, value in enumerate(row):
            table[a][b] = value
    return table


def sbox_report():
    differential, linear = ddt(AES_SBOX), walsh(AES_SBOX)
    components = [128-max(abs(linear[a][b]) for a in range(256))//2 for b in range(1, 256)]
    return {"name": "AES S-box (standard component)", "bijective": len(set(AES_SBOX)) == 256,
            "differential_uniformity": max(max(row) for row in differential[1:]),
            "max_nonzero_input_differential_probability": max(max(row) for row in differential[1:])/256,
            "max_abs_walsh_nonzero_output_mask": max(abs(row[b]) for row in linear for b in range(1, 256)),
            "minimum_component_nonlinearity": min(components),
            "component_nonlinearity": components, "ddt": differential, "walsh": linear,
            "lat_convention": "signed Walsh correlation sum, not bias counts"}


def bic(histories, samples):
    """Pairwise Pearson correlation conditional on each flipped input bit."""
    maximum, undefined, pairs, worst = 0.0, 0, 0, None
    for input_bit, row in enumerate(histories):
        counts = [value.bit_count() for value in row]
        for i in range(128):
            for j in range(i+1, 128):
                ni, nj = counts[i], counts[j]
                variance = ni*(samples-ni)*nj*(samples-nj)
                if not variance:
                    undefined += 1
                    continue
                n11 = (row[i] & row[j]).bit_count()
                correlation = (samples*n11-ni*nj)/math.sqrt(variance)
                pairs += 1
                if abs(correlation) > maximum:
                    maximum, worst = abs(correlation), [input_bit, i, j, correlation]
    return {"max_absolute_correlation": maximum if pairs else None, "worst_pair": worst,
            "defined_pairs": pairs, "undefined_constant_pairs": undefined,
            "warning": "Exploratory sample estimate; extreme correlations and constant bits require larger samples."}


def diffusion(rounds, samples, seed, key_bits=False):
    rng = random.Random(seed)
    width = 256 if key_bits else 128
    histories = [[0]*128 for _ in range(width)]
    distance_sum, minimum, maximum = 0, 128, 0
    for sample in range(samples):
        key, block = rng.randbytes(32), rng.randbytes(16)
        baseline = encrypt_block(key, block, rounds=rounds)
        for bit in range(width):
            source = bytearray(key if key_bits else block)
            source[bit//8] ^= 1 << (bit % 8)
            output = encrypt_block(bytes(source), block, rounds=rounds) if key_bits else encrypt_block(key, bytes(source), rounds=rounds)
            difference = int.from_bytes(bytes(a ^ b for a, b in zip(baseline, output)), "little")
            distance = difference.bit_count()
            distance_sum += distance
            minimum, maximum = min(minimum, distance), max(maximum, distance)
            while difference:
                lowest = difference & -difference
                histories[bit][lowest.bit_length()-1] |= 1 << sample
                difference ^= lowest
    counts = [[value.bit_count() for value in row] for row in histories]
    return {"kind": "key" if key_bits else "plaintext", "rounds": rounds, "samples_per_input_bit": samples,
            "trials": width*samples, "mean_changed_output_bits": distance_sum/(width*samples),
            "min_changed_bits": minimum, "max_changed_bits": maximum,
            "sac_counts": counts, "sac_max_absolute_bias": max(abs(n/samples-.5) for row in counts for n in row),
            "bic": bic(histories, samples)}


def round_dependencies(samples, seed):
    """Mean Hamming distance after each round; no claim about a trail bound."""
    rng = random.Random(seed)
    totals = [0]*24
    for _ in range(samples):
        key, block = rng.randbytes(32), rng.randbytes(16)
        keys = expand_key(key, 24)
        baseline = (int.from_bytes(block[:8], "big"), int.from_bytes(block[8:], "big"))
        for bit in range(128):
            changed = bytearray(block)
            changed[bit//8] ^= 1 << (bit % 8)
            left, right = baseline
            alt_left, alt_right = int.from_bytes(changed[:8], "big"), int.from_bytes(changed[8:], "big")
            for index, k in enumerate(keys):
                left, right = right, left ^ _round_function(right, k)
                alt_left, alt_right = alt_right, alt_left ^ _round_function(alt_right, k)
                totals[index] += (left ^ alt_left).bit_count()+(right ^ alt_right).bit_count()
    return [{"round": i+1, "mean_changed_bits": total/(128*samples)} for i, total in enumerate(totals)]


def key_schedule_probe():
    schedules = [expand_key(bytes([value])*32, 24) for value in range(256)]
    return {"key_family": "all 256 repeated-byte 256-bit keys", "samples": len(schedules),
            "distinct_full_schedules": len(set(schedules)),
            "repeated_round_words_in_schedule": sum(len(set(s)) < len(s) for s in schedules),
            "warning": "No collision in this tiny family does not exclude weak, equivalent or related keys."}


def run(samples, seed, variants=SUPPORTED_ROUNDS):
    if type(samples) is not int or samples < 2:
        raise ValueError("samples must be an integer >= 2")
    started = time.perf_counter()
    result = {"format": "nastyx-lab-v1", "warning": "Unaudited research only; metrics are not security proofs.",
              "seed": seed, "samples": samples, "rng": "Python random.Random; reproducible experiment inputs only",
              "bit_order": "byte zero first, least significant bit first within each byte",
              "python": platform.python_version(), "platform": platform.platform(),
              "reference_sha256": hashlib.sha256((Path(__file__).parent/'reference_cipher/reference.py').read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
              "hash_convention": "SHA-256 of UTF-8 source with universal newlines normalized to LF",
              "sbox": sbox_report(), "diffusion": [], "round_dependencies": round_dependencies(samples, seed),
              "key_schedule": key_schedule_probe()}
    for rounds in variants:
        print(f"rounds={rounds}: plaintext and key SAC/BIC", flush=True)
        result["diffusion"].extend([diffusion(rounds, samples, seed), diffusion(rounds, samples, seed, True)])
    result["elapsed_seconds"] = time.perf_counter()-started
    return result


def format_report(report):
    """Keep integer table rows on one line so raw results remain reviewable."""
    document = json.dumps(report, indent=2, allow_nan=False)
    return re.sub(r'\[\s+(-?\d+(?:,\s+-?\d+)*)\s+\]',
                  lambda match: '['+re.sub(r'\s+', ' ', match[1])+']', document)+'\n'


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20261011)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.samples < 2:
        parser.error("--samples must be >= 2")
    report = run(args.samples, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(format_report(report), encoding="utf-8")
    print(f"saved {args.output}; elapsed={report['elapsed_seconds']:.3f}s")
