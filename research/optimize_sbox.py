"""Public deterministic local search; no claim of cryptographic security."""
import argparse
import json
import hashlib
import platform
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent/'reference_cipher'))
from sbox import NASTYX_SBOX
from lab import ddt, walsh, format_report


def optimize(iterations=30000, seed=20261011):
    table = list(NASTYX_SBOX)
    counts = ddt(table)
    energy = sum(c**4 for row in counts[1:] for c in row)
    initial = energy
    rng = random.Random(seed)
    accepted = 0
    for iteration in range(iterations):
        x, y = rng.sample(range(256), 2)
        changes = []
        delta = 0
        for a in range(1, 256):
            updates = {}
            for v in {x, y, x ^ a, y ^ a}:
                old = table[v] ^ table[v ^ a]
                t = v ^ a
                new_v = table[y] if v == x else table[x] if v == y else table[v]
                new_t = table[y] if t == x else table[x] if t == y else table[t]
                new = new_v ^ new_t
                updates[old] = updates.get(old, 0)-1
                updates[new] = updates.get(new, 0)+1
            for b, change in updates.items():
                if change:
                    before = counts[a][b]
                    delta += (before+change)**4-before**4
                    changes.append((a, b, change))
        if delta <= 0:
            table[x], table[y] = table[y], table[x]
            for a, b, change in changes:
                counts[a][b] += change
            energy += delta
            accepted += 1
        if iteration % 5000 == 4999:
            print(f'{iteration+1}/{iterations}: energy={energy}, accepted={accepted}', flush=True)
    assert counts == ddt(table)
    linear = walsh(table)
    peak = max(abs(row[b]) for row in linear for b in range(1, 256))
    return {'generator_sha256': hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(), 'python': platform.python_version(), 'format': 'nastyx-sbox-local-search-v1', 'seed': seed, 'iterations': iterations,
            'initial_energy': initial, 'final_energy': energy, 'accepted_swaps': accepted,
            'objective': 'sum DDT[a,b]^4 over a != 0; accept delta <= 0',
            'warning': 'Public heuristic search; no security proof or unbiased sampling.',
            'table': table, 'differential_uniformity': max(max(row) for row in counts[1:]),
            'max_abs_walsh': peak, 'minimum_component_nonlinearity': 128-peak//2}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=30000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100000:
        parser.error('iterations must be in 1..100000')
    result = optimize(args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(format_report(result), encoding='utf-8')
    print({k: result[k] for k in ('differential_uniformity', 'max_abs_walsh', 'minimum_component_nonlinearity')})
