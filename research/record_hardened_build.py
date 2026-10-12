"""Capture pinned-build provenance, matched benchmarks and three ASM fragments.

Windows GNU only. Recording assembly does not certify its timing or erase copies.
The previous measurements and their exact input sources are retained separately.
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


def fragment(pattern, marker, directory):
    path = max(directory.glob(pattern), key=lambda p: p.stat().st_mtime_ns)
    source = path.read_text(encoding='utf8')
    match = re.search(r'^([^\s:]*' + re.escape(marker) + r'):$', source, re.MULTILINE)
    if match is None:
        raise RuntimeError(f'Function {marker} not found in {path}')
    after = source[match.start():]
    boundary = re.search(r'^\s*\.def\s', after, re.MULTILINE)
    if boundary is not None:
        after = after[:boundary.start()]
    end = re.search(r'^\s*\.seh_endproc\s*$', after, re.MULTILINE)
    if end is None:
        returns = list(re.finditer(r'^\s*retq\s*$', after, re.MULTILINE))
        end = returns[-1] if returns else None
    if end is None:
        raise RuntimeError('Expected a Windows x86_64 GNU function ending with retq')
    # Preserve all basic blocks through endproc (or the last return for leaves).
    return after[:end.end()].rstrip() + '\n'


def record(cargo, toolchain):
    prefix = [cargo, '+' + toolchain]

    def command(args):
        result = subprocess.run(prefix + args, cwd=ROOT, text=True, encoding='utf8',
                                capture_output=True, check=True, timeout=120)
        return result.stdout

    benchmarks = {}
    for example in ('bench', 'compare_sboxes'):
        stdout = command(['run', '--release', '--locked', '-p', 'nastyx-engine', '--example', example])
        benchmarks[example] = {'stdout': stdout, 'repetitions': [
            {name: float(value) if 'seconds' in name else int(value)
             for name, value in re.findall(r'(\w+)=([0-9.]+)', line)}
            for line in stdout.splitlines() if line.startswith('repetition=')]}
        print(stdout, flush=True)
    for package in ('nastyx-engine', 'nastyx-message'):
        command(['rustc', '--release', '--locked', '-p', package, '--', '--emit=asm'])
    command(['rustc', '--release', '--locked', '-p', 'nastyx-engine', '--example', 'memory_probe', '--', '--emit=asm'])
    fragments = {}
    for name, pattern, marker, directory in (
        ('round', 'nastyx_engine-*.s', 'round_function', 'deps'),
        ('tag', 'nastyx_message-*.s', 'tags_equal', 'deps'),
        ('erase', 'memory_probe-*.s', 'destroy', 'examples'),
    ):
        asm = fragment(pattern, marker, ROOT / 'target/release' / directory)
        out = ROOT / f'research/results/hardened-{name}-x86_64-gnu.s'
        out.write_text(asm, encoding='utf8')
        fragments[name] = {'path': out.relative_to(ROOT).as_posix(), 'sha256_utf8_lf': digest(out),
                           'branch_or_call_lines': [line.strip() for line in asm.splitlines()
                                                    if re.search(r'^\s+(j\w+|call\w*)\s', line)]}
    files = ['Cargo.toml', 'Cargo.lock', 'research/record_hardened_build.py', 'research/generate_sbox_circuit.py']
    for package in ('nastyx-engine', 'nastyx-message', 'nastyx-session'):
        files += [f'crates/{package}/Cargo.toml', f'crates/{package}/src/lib.rs']
    files += ['crates/nastyx-engine/src/boolean_substitution.rs']
    files += [f'crates/nastyx-engine/examples/{name}.rs' for name in ('bench', 'compare_sboxes', 'memory_probe')]
    files += ['research/snapshots/boolean-v1/crates/nastyx-engine/src/boolean_substitution.rs']
    report = {'format': 'nastyx-hardened-build-v1', 'date': '2026-10-12',
              'platform': platform.platform(), 'toolchain': toolchain, 'cargo_version': command(['--version']).strip(),
              'profile': 'default release, no target-cpu override',
              'sources_sha256_utf8_lf': {name: digest(ROOT / name) for name in files},
              'benchmarks': benchmarks, 'assembly': fragments,
              'scope': 'Public serial probes, alternating microbenchmark order. Frequency/load not controlled. One target, one compiler; no timing certification or guarantee of erasing all copies.'}
    (ROOT / 'research/results/hardened-build-v1.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cargo', default='cargo')
    parser.add_argument('--toolchain', default='stable-x86_64-pc-windows-gnu')
    args = parser.parse_args()
    record(args.cargo, args.toolchain)
