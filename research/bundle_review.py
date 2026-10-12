"""Create a local reproducible, text-only external-review package.

Only explicitly allowed source/document trees are included. No .git metadata,
environment files, private registry, design artwork, build output or private logs.
No upload, email, reviewer assignment or claim of external review is performed.
"""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TREES = ('.github/', 'crates/', 'docs/', 'research/', 'tests/', 'demos/')
TOP = {'README.md', 'LICENSE', 'Cargo.toml', 'Cargo.lock', '.gitignore'}
EXTENSIONS = {'.rs', '.py', '.md', '.json', '.toml', '.lock', '.yml', '.yaml', '.tsv', '.hex', '.s'}


def build(output):
    raw = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    names = sorted(set(raw.decode('utf8').rstrip('\0').split('\0')))
    content = {}
    for name in names:
        relative = Path(name)
        allowed = name in TOP or (name.startswith(TREES) and relative.suffix in EXTENSIONS)
        if not allowed or '..' in relative.parts or relative.is_absolute():
            continue
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            continue
        content[name] = path.read_text(encoding='utf8').encode('utf8')
    manifest = {'format': 'nastyx-external-review-package-v1',
                'status': 'Prepared locally. No external reviewer, submission or assessment yet.',
                'encoding': 'UTF-8, LF normalization',
                'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                          for name, data in content.items()}}
    content['REVIEW_MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(content.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 12, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    # Verify every packaged byte against the independent manifest after closing.
    with zipfile.ZipFile(output) as archive:
        for name, item in manifest['files'].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != item['sha256']:
                raise RuntimeError(f'Archive mismatch: {name}')
    receipt = {'archive': output.name, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'files': len(manifest['files']), 'bytes': output.stat().st_size,
               'status': manifest['status']}
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/review/NA-STY-X-review-2026-10-12.zip')
    build(parser.parse_args().output)
