import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/reference_cipher'))
sys.path.insert(0, str(ROOT / 'research'))
from session_v1 import Pairing, Message, step, HEADER, MAX_PLAINTEXT, MAX_SKIP
from generate_session_vectors import generate


def pair(seed=3):
    secret, a, b = bytes([7]) * 32, bytes([1]) * 16, bytes([2]) * 16
    ia, offer = Pairing(secret, a, b).initiate(bytes([seed]) * 16, bytes([4]) * 16)
    ib, reply = Pairing(secret, a, b).respond(offer, bytes([5]) * 16)
    ua, confirm = ia.complete(reply)
    ub = ib.complete(confirm)
    ac, bc = ua.verification, ub.verification
    return ua.verify_peer(bc), ub.verify_peer(ac)


class SessionTests(unittest.TestCase):
    def test_verification_is_required_and_wrong_code_closes_candidate(self):
        p = Pairing(bytes([7]) * 32, bytes([1]) * 16, bytes([2]) * 16)
        a, offer = p.initiate(bytes([3]) * 16, bytes([4]) * 16)
        b, reply = Pairing(bytes([7]) * 32, bytes([1]) * 16, bytes([2]) * 16).respond(offer, bytes([5]) * 16)
        candidate, confirm = a.complete(reply)
        self.assertFalse(hasattr(candidate, 'seal'))
        with self.assertRaises(ValueError):
            candidate.verify_peer(bytes(16))
        self.assertIsNone(candidate.session)
        peer = b.complete(confirm)
        self.assertIsNotNone(peer.session)

    def test_independent_fixture(self):
        self.assertEqual((ROOT / 'tests/vectors/session-v1.hex').read_text(encoding='utf8'), generate())

    def test_pairing_is_consumed_and_wrong_secret_is_rejected(self):
        p = Pairing(bytes([7]) * 32, bytes([1]) * 16, bytes([2]) * 16)
        _, offer = p.initiate(bytes([3]) * 16, bytes([4]) * 16)
        with self.assertRaises(ValueError):
            p.initiate(bytes([3]) * 16, bytes([4]) * 16)
        with self.assertRaises(ValueError):
            Pairing(bytes([8]) * 32, bytes([1]) * 16, bytes([2]) * 16).respond(offer, bytes([5]) * 16)

    def test_reordering_replay_and_reflection(self):
        a, b = pair()
        packets = [a.seal(bytes([n])) for n in range(3)]
        for n in (2, 0, 1):
            self.assertEqual(b.open(packets[n]), bytes([n]))
            with self.assertRaises(ValueError):
                b.open(packets[n])
        self.assertEqual(a.open(b.seal(b'reply')), b'reply')
        with self.assertRaises(ValueError):
            a.open(packets[0])

    def test_mutation_never_advances_state(self):
        a, b = pair()
        packet = a.seal(b'payload')
        before = b.receiving
        for index in range(len(packet)):
            changed = bytearray(packet)
            changed[index] ^= 1
            with self.assertRaises(ValueError):
                b.open(bytes(changed))
            self.assertEqual((b.receiving, b.received, b.skipped), (before, 0, {}))
        self.assertEqual(b.open(packet), b'payload')

    def test_parser_random_inputs_and_lengths(self):
        a, b = pair()
        packet = a.seal(b'payload')
        inputs = [packet[:i] for i in range(len(packet))] + [packet + b'\x00']
        rng = random.Random(20261012)  # Public test data only.
        inputs += [rng.randbytes(rng.randrange(0, 300)) for _ in range(5000)]
        for data in inputs:
            with self.assertRaises(ValueError):
                b.open(data)
            self.assertEqual(b.received, 0)
        self.assertEqual(b.open(packet), b'payload')

    def test_discard_limits_and_closed_state(self):
        a, b = pair()
        with self.assertRaises(ValueError):
            a.seal(bytes(MAX_PLAINTEXT + 1))
        self.assertEqual(a.sent, 0)
        packets = [a.seal(b'') for _ in range(MAX_SKIP + 2)]
        with self.assertRaises(ValueError):
            b.open(packets[MAX_SKIP + 1])
        self.assertEqual(b.open(packets[MAX_SKIP]), b'')
        self.assertEqual(len(b.skipped), MAX_SKIP)
        b.discard_skipped()
        with self.assertRaises(ValueError):
            b.open(packets[0])
        b.close()
        with self.assertRaises(ValueError):
            b.open(packets[MAX_SKIP + 1])
        self.assertIsNone(b.receiving)

    def test_new_session_rejects_old_and_current_key_is_different(self):
        a, b = pair()
        old = a.seal(b'old')
        self.assertEqual(b.open(old), b'old')
        key, _ = step(a.sending, 0, 1)
        with self.assertRaises(ValueError):
            Message(key).open(old[HEADER:], old[:HEADER])
        fresh_a, fresh_b = pair(9)
        with self.assertRaises(ValueError):
            fresh_b.open(old)
        self.assertEqual(fresh_b.open(fresh_a.seal(b'new')), b'new')


if __name__ == '__main__':
    unittest.main()
