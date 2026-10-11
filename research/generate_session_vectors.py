"""Public deterministic interoperability fixtures; never generate secret keys here."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/reference_cipher'))
from session_v1 import Pairing


def generate():
    secret = bytes(range(32))
    a, b, sid, na, nb = (bytes([value]) * 16 for value in (1, 2, 3, 4, 5))
    initiator, offer = Pairing(secret, a, b).initiate(sid, na)
    responder, reply = Pairing(secret, a, b).respond(offer, nb)
    ua, confirm = initiator.complete(reply)
    ub = responder.complete(confirm)
    fingerprint = ua.verification
    sa, sb = ua.verify_peer(ub.verification), ub.verify_peer(fingerprint)
    fields = [secret, a, b, sid, na, nb, offer, reply, confirm, fingerprint]
    for sender, receiver, plaintext in [(sa, sb, b''), (sa, sb, b'hello'),
                                         (sb, sa, 'Привет NAXi'.encode()),
                                         (sa, sb, bytes(range(255)))]:
        packet = sender.seal(plaintext)
        assert receiver.open(packet) == plaintext
        fields += [plaintext, packet]
    return '# NXS1 public vector; ordered fields specified in SESSION_SPEC_V1.md\n' + '\n'.join(x.hex() for x in fields) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'tests/vectors/session-v1.hex'
    content = generate()
    if args.check:
        if path.read_text(encoding='utf8') != content:
            raise SystemExit('session vectors differ')
        print('NXS1 handshake and 4 message vectors verified')
    else:
        path.write_text(content, encoding='utf8')
        print('NXS1 fixtures generated')
