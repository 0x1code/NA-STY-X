"""Exact selected-difference/mask analysis of a 16-bit NA&STY-X toy model.

This is NOT the 128-bit cipher and gives no security bound for it.
"""
import argparse
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'reference_cipher'))
from engine_v3 import SBOX as NASTYX_SBOX
from lab import format_report

DOMAIN = 1 << 16
KEYS = (0, 0x76543210)
ROUNDS = (1, 2, 3, 4, 6, 8)


def rotate8(x, amount):
    amount %= 8
    return ((x << amount) | (x >> ((8-amount) % 8))) & 255


def expand_toy_key(key, rounds):
    if type(key) is not int or not 0 <= key < 1 << 32:
        raise ValueError('toy key must be a 32-bit unsigned integer')
    if type(rounds) is not int or not 1 <= rounds <= 24:
        raise ValueError('toy rounds must be in 1..24')
    state = [(key >> shift) & 255 for shift in (24, 16, 8, 0)]
    result = []
    for i in range(rounds):
        a, b, c, d = state
        constant = (0x15*(i+1)) & 255
        k = round_table(constant)[round_table(c ^ constant)[a ^ rotate8(b,13)] ^ d]
        result.append(k)
        state = [b ^ rotate8(a,7), (c + rotate8(k,11)) & 255, d ^ rotate8(b,29), (k+a) & 255]
    return result


def round_table(key):
    result = []
    for x in range(256):
        z = NASTYX_SBOX[x ^ key]
        y = ((z + rotate8(z,17)) & 255) ^ rotate8(z,41)
        y = ((y + rotate8(y,31)) & 255) ^ rotate8(y,23)
        result.append(((y + rotate8(y,11)) & 255) ^ rotate8(y,37) ^ key)
    return result


def permute(value, tables, decrypt=False):
    if type(value) is not int or not 0 <= value < DOMAIN:
        raise ValueError('toy block must be a 16-bit unsigned integer')
    left, right = value >> 8, value & 255
    if decrypt:
        for table in reversed(tables):
            left, right = right ^ table[left], left
    else:
        for table in tables:
            left, right = right, left ^ table[right]
    return (left << 8) | right


def difference_row(permutation, difference):
    n = len(permutation)
    if n < 2 or n & (n-1) or not 0 < difference < n:
        raise ValueError('require a power-of-two domain and a nonzero input difference')
    counts = [0]*n
    for x, y in enumerate(permutation):
        counts[y ^ permutation[x ^ difference]] += 1
    return counts


def walsh_column(permutation, output_mask):
    n = len(permutation)
    if n < 2 or n & (n-1) or not 0 < output_mask < n:
        raise ValueError('require a power-of-two domain and a nonzero output mask')
    row = [1 if (value & output_mask).bit_count() % 2 == 0 else -1 for value in permutation]
    step = 1
    while step < n:
        for start in range(0, n, 2*step):
            for j in range(start, start+step):
                a, b = row[j], row[j+step]
                row[j], row[j+step] = a+b, a-b
        step *= 2
    return row


def analyze(permutation, differences, masks):
    if len(set(permutation)) != len(permutation) or set(permutation) != set(range(len(permutation))):
        raise ValueError('analysis requires a permutation')
    differential = []
    for delta in differences:
        counts = difference_row(permutation, delta)
        peak = max(counts)
        witness = counts.index(peak)
        differential.append({'input_difference': delta, 'output_difference': witness,
                             'count': peak, 'probability': peak/len(permutation),
                             'peak_multiplicity': counts.count(peak)})
    linear = []
    for mask in masks:
        row = walsh_column(permutation, mask)
        peak = max(abs(value) for value in row[1:])
        witness = next(i for i in range(1, len(row)) if abs(row[i]) == peak)
        linear.append({'input_mask': witness, 'output_mask': mask,
                       'signed_walsh': row[witness], 'absolute_correlation': peak/len(permutation),
                       'peak_multiplicity': sum(abs(value) == peak for value in row[1:])})
    return {'bijective': True, 'differentials': differential, 'linear': linear,
            'max_selected_differential_probability': max(r['probability'] for r in differential),
            'max_selected_absolute_linear_correlation': max(r['absolute_correlation'] for r in linear)}


def run():
    start = time.perf_counter()
    source = Path(__file__)
    inputs = [1 << bit for bit in range(16)]
    result = {'format': 'nastyx-toy-v3-analysis-v1', 'model': '16-bit block / 32-bit key / 8-bit words',
              'warning': 'Toy model only. Selected differences and masks are not exhaustive global maxima. No bounds for the full cipher.',
              'domain_size': DOMAIN, 'keys': list(KEYS), 'round_counts': list(ROUNDS),
              'input_differences': inputs, 'output_masks': inputs,
              'input_mask_scope': 'all 65535 nonzero masks for each selected output mask',
              'plaintext_scope': 'all 65536 inputs for each fixed key and round count',
              'python': platform.python_version(), 'platform': platform.platform(),
              'source_sha256': hashlib.sha256(source.read_text(encoding='utf-8').encode()).hexdigest(),
              'sbox_source_sha256': hashlib.sha256((source.parent/'reference_cipher/engine_v3.py').read_text(encoding='utf-8').encode()).hexdigest(),
              'hash_convention': 'UTF-8 with universal newlines normalized to LF', 'cases': []}
    baseline = list(range(DOMAIN))
    random.Random(20261011).shuffle(baseline)
    result['random_permutation_reference'] = {
        'seed': 20261011, 'rng': 'Python random.Random; public experiment only',
        'warning': 'One illustrative random permutation, not an ideal-cipher security threshold.',
        **analyze(baseline, inputs, inputs)}
    print('random permutation reference complete', flush=True)
    for key in KEYS:
        tables = [round_table(k) for k in expand_toy_key(key, max(ROUNDS))]
        permutation = list(range(DOMAIN))
        for index, table in enumerate(tables, 1):
            permutation = [((value & 255) << 8) | ((value >> 8) ^ table[value & 255]) for value in permutation]
            if index not in ROUNDS:
                continue
            case = analyze(permutation, inputs, inputs)
            case.update({'key_hex': f'{key:08x}', 'rounds': index})
            result['cases'].append(case)
            print(f"key={key:08x} rounds={index} DP={case['max_selected_differential_probability']:.6f} |C|={case['max_selected_absolute_linear_correlation']:.6f}", flush=True)
    result['elapsed_seconds'] = time.perf_counter()-start
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(format_report(report), encoding='utf-8')
