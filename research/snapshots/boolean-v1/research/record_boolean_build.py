"""Record one target's public-input benchmark and assembly for manual review.

Not a constant-time verifier. Windows GNU assembly extraction is target-specific.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_text(encoding='utf8').encode()).hexdigest()


def record(cargo, toolchain):
    prefix = [cargo, '+' + toolchain]

    def command(arguments):
        result = subprocess.run(prefix + arguments, cwd=ROOT, text=True, encoding='utf8',
                                capture_output=True, check=True, timeout=120)
        return result.stdout

    bench = command(['run', '--release', '-p', 'nastyx-engine', '--example', 'bench'])
    command(['rustc', '--release', '-p', 'nastyx-engine', '--', '--emit=asm'])
    assemblies = list((ROOT / 'target/release/deps').glob('nastyx_engine-*.s'))
    path = max(assemblies, key=lambda item: item.stat().st_mtime_ns)
    source = path.read_text(encoding='utf8')
    match = re.search(r'^([^\s:]*round_function):$', source, re.MULTILINE)
    if match is None or '.seh_endproc' not in source[match.end():]:
        raise RuntimeError('This recorder expects Windows GNU assembly; extract other targets explicitly.')
    end = source.index('.seh_endproc', match.end()) + len('.seh_endproc')
    fragment = source[match.start():end] + '\n'
    output = ROOT / 'research/results/sbox-boolean-x86_64-gnu.s'
    output.write_text(fragment, encoding='utf8')
    parsed = []
    for line in bench.splitlines():
        if line.startswith('repetition='):
            parsed.append({name: float(value) if 'seconds' in name else int(value)
                           for name, value in re.findall(r'(\w+)=([0-9.]+)', line)})
    if len(parsed) != 3:
        raise RuntimeError('unexpected benchmark output')
    files = ['crates/nastyx-engine/src/lib.rs', 'crates/nastyx-engine/src/boolean_substitution.rs',
             'crates/nastyx-engine/examples/bench.rs', 'research/generate_sbox_circuit.py',
             'research/record_boolean_build.py', 'Cargo.toml']
    report = {'format': 'nastyx-boolean-build-v1', 'date': '2026-10-12',
              'toolchain': toolchain, 'cargo_version': command(['--version']).strip(),
              'platform': platform.platform(), 'profile': 'default Cargo release',
              'sources_sha256_utf8_lf': {name: digest(ROOT / name) for name in files},
              'assembly_fragment': str(output.relative_to(ROOT)).replace('\\', '/'),
              'assembly_sha256_utf8_lf': digest(output), 'benchmark_stdout': bench,
              'repetitions': parsed, 'cipher_state_bytes': 200,
              'scope': 'Public serial microprobe; no controlled frequency/load or statistical timing test. Assembly for manual review, not certification.'}
    (ROOT / 'research/results/sbox-boolean-build-v1.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(bench)
    print('Build evidence and round-function assembly recorded; manual review required.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cargo', default='cargo')
    parser.add_argument('--toolchain', default='stable-x86_64-pc-windows-gnu')
    args = parser.parse_args()
    record(args.cargo, args.toolchain)
