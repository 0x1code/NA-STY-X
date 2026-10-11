"""Transparent bounded screening of public NA&STY-X S-box candidates."""
import json
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'reference_cipher'))
from sbox import DESIGN_SEED, DESIGN_ROUNDS, make_sbox
from lab import ddt, walsh, format_report


def screen():
    attempts = []
    for candidate in range(256):
        table = make_sbox(candidate)
        differential = ddt(table)
        linear = walsh(table)
        du = max(max(row) for row in differential[1:])
        peak = max(abs(row[b]) for row in linear for b in range(1, 256))
        nonlinearity = 128 - peak // 2
        attempts.append({'candidate': candidate, 'differential_uniformity': du,
                         'max_abs_walsh': peak, 'minimum_component_nonlinearity': nonlinearity})
        if candidate % 64 == 63:
            print(f'screened {candidate + 1}/256 candidates', flush=True)
    best = min(attempts, key=lambda r: (r['max_abs_walsh'], r['differential_uniformity'], r['candidate']))
    return {'format': 'nastyx-sbox-design-v1', 'algorithm_version': '0.2',
            'seed': DESIGN_SEED, 'nibble_feistel_rounds': DESIGN_ROUNDS,
            'rule': 'all 256 candidates; minimize (max_abs_walsh, differential_uniformity, candidate)',
            'initial_target': 'DU <= 10 and component NL >= 100',
            'initial_target_met': any(r['differential_uniformity'] <= 10 and r['minimum_component_nonlinearity'] >= 100 for r in attempts),
            'warning': 'Screening criteria are not security proofs; generator is public, not a cryptographic RNG.',
            'selected_candidate': best['candidate'], 'attempts': attempts,
            'table': make_sbox(best['candidate'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    target = Path(__file__).parent / 'results/sbox-v0.2-design.json'
    report = screen()
    if args.check:
        if json.loads(target.read_text(encoding='utf-8')) != json.loads(format_report(report)):
            raise SystemExit('S-box design report mismatch')
        print('S-box design report verified')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(format_report(report), encoding='utf-8')
