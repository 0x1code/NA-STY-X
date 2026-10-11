"""Deterministic Walsh-energy local search following DDT screening."""
import json
import hashlib
import platform
import random
from pathlib import Path
from lab import ddt, walsh, format_report


def run(iterations=4000):
    start = json.loads((Path(__file__).parent/'results/sbox-optimized-v1.json').read_text(encoding='utf-8'))
    table = start['table'][:]
    w = walsh(table)
    initial = energy = sum(v**8 for row in w[1:] for v in row[1:])
    rng = random.Random(20261012)
    accepted = 0
    for i in range(iterations):
        x, y = rng.sample(range(256), 2)
        input_masks = [(a, 1 if (a & x).bit_count() % 2 == 0 else -1)
                       for a in range(1, 256) if (a & (x ^ y)).bit_count() % 2]
        output_masks = [(b, 1 if (b & table[x]).bit_count() % 2 == 0 else -1)
                        for b in range(1, 256) if (b & (table[x] ^ table[y])).bit_count() % 2]
        updates = []
        delta = 0
        for a, sa in input_masks:
            for b, sb in output_masks:
                old = w[a][b]
                new = old-4*sa*sb
                delta += new**8-old**8
                updates.append((a, b, new))
        if delta <= 0:
            table[x], table[y] = table[y], table[x]
            for a, b, new in updates:
                w[a][b] = new
            energy += delta
            accepted += 1
        if i % 500 == 499:
            print(f'{i+1}/{iterations}: accepted={accepted}', flush=True)
    assert w == walsh(table)
    d = ddt(table)
    peak = max(abs(v) for row in w for v in row[1:])
    return {'generator_sha256': hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(), 'python': platform.python_version(), 'format': 'nastyx-sbox-linear-search-v1', 'seed': 20261012,
            'iterations': iterations, 'starting_table': start['table'], 'table': table,
            'initial_energy': initial, 'final_energy': energy, 'accepted_swaps': accepted,
            'objective': 'sum Walsh[a,b]^8 for a,b != 0; accept delta <= 0',
            'differential_uniformity': max(max(row) for row in d[1:]),
            'max_abs_walsh': peak, 'minimum_component_nonlinearity': 128-peak//2,
            'warning': 'Local heuristic optimization does not establish cipher security.'}


if __name__ == '__main__':
    report = run()
    (Path(__file__).parent/'results/sbox-linear-optimized-v1.json').write_text(format_report(report), encoding='utf-8')
    print({k: report[k] for k in ('differential_uniformity','max_abs_walsh','minimum_component_nonlinearity')})
