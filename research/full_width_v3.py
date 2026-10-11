"""Bounded full-width v0.3 analysis. Samples are not attack bounds."""
import hashlib
import random
import sys
import platform
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'reference_cipher'))
from engine_v3 import Engine, SBOX, round_function
from lab import ddt, walsh, format_report


def degree(mask):
    coefficients = [(mask & value).bit_count() % 2 for value in SBOX]
    for bit in range(8):
        for i in range(256):
            if i & (1 << bit): coefficients[i] ^= coefficients[i ^ (1 << bit)]
    return max((i.bit_count() for i,v in enumerate(coefficients) if v),default=0)


def run(samples=512):
    start = time.perf_counter()
    rng = random.Random(20261011)
    report = {'format':'nastyx-full-width-v3-v1','seed':20261011,'samples':samples,
              'python':platform.python_version(),'platform':platform.platform(),
              'warning':'Bounded sample probes, not exhaustive cryptanalysis or proof of security.',
              'sources':{name:hashlib.sha256((Path(__file__).parent/name).read_text(encoding='utf-8').encode()).hexdigest()
                         for name in ('full_width_v3.py','reference_cipher/engine_v3.py')},
              'hash_convention':'UTF-8 source with newlines normalized to LF'}
    d,w = ddt(SBOX),walsh(SBOX)
    report['sbox']={'du':max(max(row) for row in d[1:]),'max_abs_walsh':max(abs(v) for row in w for v in row[1:]),
                    'component_degrees':[degree(mask) for mask in range(1,256)],
                    'fixed_points':[x for x in range(256) if SBOX[x]==x],
                    'opposite_fixed_points':[x for x in range(256) if SBOX[x]==(x ^ 255)]}
    report['round_function'] = []
    for k in (0,(1 << 64)-1,0x0123456789abcdef):
        counts = [[0]*64 for _ in range(64)]
        in_hist,out_hist = [0]*64,[0]*64
        for sample in range(samples):
            x = rng.getrandbits(64)
            y = round_function(x,k)
            for bit in range(64):
                if x >> bit & 1: in_hist[bit] |= 1 << sample
                if y >> bit & 1: out_hist[bit] |= 1 << sample
                diff = y ^ round_function(x ^ (1 << bit),k)
                for output in range(64): counts[bit][output] += diff >> output & 1
        linear = [[samples-2*(a ^ b).bit_count() for b in out_hist] for a in in_hist]
        peak = max(abs(v) for row in linear for v in row)
        report['round_function'].append({'round_key_hex':f'{k:016x}','sac_counts':counts,
              'mean_changed_bits':sum(sum(row) for row in counts)/(64*samples),
              'single_bit_linear_signed_sums':linear,'max_sample_single_bit_correlation':peak/samples,
              'mask_scope':'64 one-bit input x 64 one-bit output masks; sampled inputs only'})
    print('64-bit round function probes complete',flush=True)
    family = [bytes([b])*32 for b in range(256)] + [bytes(32)]
    family += [(1 << bit).to_bytes(32,'big') for bit in range(256)]
    family += [rng.randbytes(32) for _ in range(512)]
    family = list(dict.fromkeys(family))
    schedules = [tuple(Engine(key).keys) for key in family]
    report['key_family']={'unique_master_keys':len(family),'distinct_schedules':len(set(schedules)),
                         'within_schedule_repeated_word_cases':sum(len(set(s))<len(s) for s in schedules),
                         'scope':'all repeated bytes, all one-bit keys, zero, 512 deterministic random keys; not all keys'}
    dependencies = []
    for baseline_key in (bytes(32),bytes([255])*32,bytes(range(32))):
        base = Engine(baseline_key).keys
        totals = [0]*24
        unchanged = [0]*24
        for bit in range(256):
            altered = bytearray(baseline_key); altered[bit//8] ^= 1 << (bit%8)
            changed = Engine(bytes(altered)).keys
            for i,(a,b) in enumerate(zip(base,changed)):
                totals[i] += (a ^ b).bit_count(); unchanged[i] += a==b
        dependencies.append({'master_hex':baseline_key.hex(),'mean_changed_bits_per_word':[v/256 for v in totals],
                             'unchanged_word_counts':unchanged})
    report['key_dependencies'] = dependencies
    report['cipher_diffusion'] = []
    public_pairs = [(rng.randbytes(32),rng.randbytes(16)) for _ in range(32)]
    for rounds in (8,12,16,20,24):
        counts = [[0]*128 for _ in range(128)]
        for key,block in public_pairs:
            engine = Engine(key,rounds)
            baseline = int.from_bytes(engine.encrypt(block),'little')
            for bit in range(128):
                changed = bytearray(block); changed[bit//8] ^= 1 << (bit%8)
                diff = baseline ^ int.from_bytes(engine.encrypt(bytes(changed)),'little')
                for output in range(128): counts[bit][output] += diff >> output & 1
        report['cipher_diffusion'].append({'rounds':rounds,'samples_per_bit':32,'sac_counts':counts,
                                           'mean_changed_bits':sum(sum(row) for row in counts)/(128*32)})
        print(f'full 128-bit cipher rounds={rounds} complete',flush=True)
    report['elapsed_seconds'] = time.perf_counter()-start
    return report


if __name__ == '__main__':
    (Path(__file__).parent/'results/full-width-v3.json').write_text(format_report(run()),encoding='utf-8')
