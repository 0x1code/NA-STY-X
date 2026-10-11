import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'research'))
sys.path.insert(0, str(ROOT/'research/reference_cipher'))
from lab import bic, ddt, sbox_report, walsh
from reference import SUPPORTED_ROUNDS, decrypt_block, encrypt_block, expand_key


class LabTests(unittest.TestCase):
    def test_exact_sbox_metrics(self):
        result = sbox_report()
        self.assertTrue(result['bijective'])
        self.assertEqual(result['differential_uniformity'], 4)
        self.assertEqual(result['max_abs_walsh_nonzero_output_mask'], 32)
        self.assertEqual(result['minimum_component_nonlinearity'], 112)
        self.assertTrue(all(sum(row) == 256 for row in result['ddt']))
        self.assertTrue(all(sum(value*value for value in row) == 65536 for row in result['walsh']))

    def test_walsh_convention_against_exhaustive_definition(self):
        table = (0, 2, 3, 1)
        result = walsh(table)
        for a in range(4):
            for b in range(4):
                expected = sum((-1)**(((a & x).bit_count() ^ (b & table[x]).bit_count()) & 1) for x in range(4))
                self.assertEqual(result[a][b], expected)

    def test_ddt_identity(self):
        result = ddt(tuple(range(16)))
        for a, row in enumerate(result):
            self.assertEqual(row[a], 16)
            self.assertEqual(sum(row), 16)

    def test_invalid_rounds(self):
        for rounds in (0, 1, 9, 25, 16.0, True):
            with self.assertRaises(ValueError):
                expand_key(bytes(32), rounds)

    def test_all_round_variants_round_trip(self):
        rng = random.Random(20261011)
        for rounds in SUPPORTED_ROUNDS:
            for _ in range(64):
                key, block = rng.randbytes(32), rng.randbytes(16)
                self.assertEqual(decrypt_block(key, encrypt_block(key, block, rounds=rounds), rounds=rounds), block)
        self.assertEqual(expand_key(bytes(32), 24)[:16], expand_key(bytes(32)))

    def test_shared_fixtures(self):
        document = json.loads((ROOT/'tests/vectors/research-rounds.json').read_text())
        self.assertEqual(len(document['vectors']), 185)
        for case in document['vectors']:
            key, block, cipher = (bytes.fromhex(case[k]) for k in ('key_hex','plaintext_hex','ciphertext_hex'))
            self.assertEqual(encrypt_block(key, block, rounds=case['rounds']), cipher)
            self.assertEqual(decrypt_block(key, cipher, rounds=case['rounds']), block)

    def test_bic_independent_and_degenerate(self):
        # Two balanced independent bit histories, other columns constant.
        result = bic([[0b1100, 0b1010]+[0]*126], 4)
        self.assertEqual(result['defined_pairs'], 1)
        self.assertEqual(result['max_absolute_correlation'], 0)
        self.assertEqual(result['undefined_constant_pairs'], 8127)


if __name__ == '__main__':
    unittest.main()
