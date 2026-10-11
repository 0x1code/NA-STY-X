"""Generate shared research fixtures; Rust tests must independently match them."""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "reference_cipher"))
from reference import SUPPORTED_ROUNDS, encrypt_block


def vectors(seed=20261011):
    rng = random.Random(seed)
    cases = [(bytes(32), bytes(16)), (bytes([255])*32, bytes([255])*16),
             (bytes(range(32)), bytes.fromhex('00112233445566778899aabbccddeeff')),
             (bytes([0x55, 0xaa])*16, bytes([0xaa, 0x55])*8),
             (bytes([0x80])+bytes(31), bytes([0x80])+bytes(15))]
    cases.extend((rng.randbytes(32), rng.randbytes(16)) for _ in range(32))
    return [{"rounds": rounds, "key_hex": key.hex(), "plaintext_hex": block.hex(),
             "ciphertext_hex": encrypt_block(key, block, rounds=rounds).hex()}
            for rounds in SUPPORTED_ROUNDS for key, block in cases]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]/'tests/vectors'
    cases = vectors()
    document = {"format": "nastyx-multi-round-v1", "seed": 20261011,
                "warning": "Public deterministic test inputs only; not secret keys.", "vectors": cases}
    outputs = {root/'research-rounds.json': json.dumps(document, indent=2)+'\n',
               root/'research-rounds.tsv': '# rounds\tkey\tplaintext\tciphertext\n'+''.join(
                   '\t'.join(str(case[k]) for k in ['rounds', 'key_hex', 'plaintext_hex', 'ciphertext_hex'])+'\n'
                   for case in cases)}
    for path, content in outputs.items():
        if args.check:
            if path.read_text(encoding='utf-8') != content:
                raise SystemExit(f'fixture mismatch: {path}')
        else:
            path.write_text(content, encoding='utf-8')
    print(f'{len(cases)} vectors: '+('verified' if args.check else 'generated'))
