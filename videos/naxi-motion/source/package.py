"""Package the standalone NAXI motion kit."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
output = root.parents[1] / 'artifacts/NAXI-motion-kit.zip'
output.parent.mkdir(exist_ok=True)
folders = {'assets', 'source', 'after-effects', 'renders'}
top_files = {'README.md', 'preview.html', 'index.html', 'package.json', 'package-lock.json', 'hyperframes.json'}
with ZipFile(output, 'w', ZIP_DEFLATED) as kit:
    for file in sorted(root.rglob('*')):
        if not file.is_file():
            continue
        rel = file.relative_to(root)
        if (rel.parts[0] in folders or str(rel) in top_files) and not file.name.endswith(('.log', 'status.txt', '.pyc')) and '__pycache__' not in rel.parts:
            kit.write(file, 'NAXI-motion/' + rel.as_posix())
print(output, output.stat().st_size, 'bytes')
