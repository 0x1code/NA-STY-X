"""Generate public v0.3 engine/message interoperability fixtures."""
import json
import random
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'reference_cipher'))
from engine_v3 import Engine, SBOX
from message_v3 import Message


if __name__ == '__main__':
    rng = random.Random(20261011)
    root = Path(__file__).resolve().parents[1]/'tests/vectors'
    vectors = []
    for rounds in (8,12,16,20,24):
        for i in range(37):
            key = bytes(32) if i==0 else bytes([255])*32 if i==1 else rng.randbytes(32)
            block = bytes(16) if i==0 else bytes([255])*16 if i==1 else rng.randbytes(16)
            encrypted = Engine(key, rounds).encrypt(block)
            vectors.append(f'{rounds}\t{key.hex()}\t{block.hex()}\t{encrypted.hex()}\n')
    messages = []
    for size in (0,1,15,16,17,31,32,33,255,1024):
        key,nonce = rng.randbytes(32),rng.randbytes(12)
        plaintext,aad = rng.randbytes(size),rng.randbytes(size % 37)
        record = Message(key).seal_for_vector(nonce,plaintext,aad)
        messages.append({'key':key.hex(),'nonce':nonce.hex(),'plaintext':plaintext.hex(),'aad':aad.hex(),'record':record.hex()})
    outputs = {root/'v0.3-blocks.tsv':'# rounds\tkey\tplaintext\tciphertext\n'+''.join(vectors),
               root/'v0.3-messages.json':json.dumps({'format':'nastyx-message-v3-vectors','warning':'Public test keys only.','vectors':messages},indent=2)+'\n',
               root/'v0.3-messages.tsv':'# key\tnonce\tplaintext\taad\trecord\n'+''.join('\t'.join(case[k] for k in ('key','nonce','plaintext','aad','record'))+'\n' for case in messages),
               root/'sbox-v0.3.hex':bytes(SBOX).hex()+'\n'}
    check = '--check' in sys.argv
    for path, content in outputs.items():
        if check:
            if path.read_text(encoding='utf-8') != content:
                raise SystemExit(f'vector mismatch: {path}')
        else:
            path.write_text(content,encoding='utf-8')
    print('185 engine / 10 message vectors '+('verified' if check else 'generated'))
