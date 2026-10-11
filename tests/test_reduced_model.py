import sys
import json
import hashlib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'research'))
from lab import ddt, walsh
from reduced_model import (analyze, difference_row, expand_toy_key, permute,
                           round_table, walsh_column)


class ReducedModelTests(unittest.TestCase):
    def test_exact_tables_against_independent_small_definition(self):
        permutation = [3, 6, 1, 4, 7, 0, 5, 2]
        differential, linear = ddt(permutation), walsh(permutation)
        for mask in range(1, 8):
            self.assertEqual(difference_row(permutation, mask), differential[mask])
            self.assertEqual(walsh_column(permutation, mask), [row[mask] for row in linear])
            direct = [sum(1 if ((a & x).bit_count() + (mask & permutation[x]).bit_count()) % 2 == 0 else -1
                          for x in range(8)) for a in range(8)]
            self.assertEqual(walsh_column(permutation, mask), direct)

    def test_identity_witnesses(self):
        result = analyze(list(range(16)), [1, 2, 4, 8], [1, 2, 4, 8])
        self.assertEqual(result['max_selected_differential_probability'], 1)
        self.assertEqual(result['max_selected_absolute_linear_correlation'], 1)
        for row in result['differentials']:
            self.assertEqual(row['input_difference'], row['output_difference'])
        for row in result['linear']:
            self.assertEqual(row['input_mask'], row['output_mask'])

    def test_round_trip_entire_toy_domain(self):
        tables = [round_table(k) for k in expand_toy_key(0x76543210, 8)]
        for value in range(65536):
            encrypted = permute(value, tables)
            self.assertEqual(permute(encrypted, tables, decrypt=True), value)

    def test_one_round_structural_relation(self):
        tables = [round_table(k) for k in expand_toy_key(0, 1)]
        permutation = [permute(value, tables) for value in range(65536)]
        # A left-half difference passes into the right half with certainty.
        row = difference_row(permutation, 0x0100)
        self.assertEqual(row[1], 65536)
        # Output left bit zero equals input right bit zero, exactly.
        self.assertEqual(walsh_column(permutation, 0x0100)[1], 65536)

    def test_validation(self):
        for key in (-1, 1 << 32, True):
            with self.assertRaises(ValueError):
                expand_toy_key(key, 8)
        for rounds in (0, 25, True):
            with self.assertRaises(ValueError):
                expand_toy_key(0, rounds)
        with self.assertRaises(ValueError):
            analyze([0, 0], [1], [1])
        with self.assertRaises(ValueError):
            permute(65536, [])

    def test_published_witnesses_and_source_hashes(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root/'research/results/reduced-model-v1.json').read_text(encoding='utf-8'))
        for path, field in [('research/reduced_model.py', 'source_sha256'),
                            ('research/reference_cipher/sbox.py', 'sbox_source_sha256')]:
            digest = hashlib.sha256((root/path).read_text(encoding='utf-8').encode()).hexdigest()
            self.assertEqual(digest, report[field])
        self.assertEqual(len(report['cases']), 12)
        case = report['cases'][-1]
        tables = [round_table(k) for k in expand_toy_key(int(case['key_hex'], 16), case['rounds'])]
        permutation = [permute(value, tables) for value in range(65536)]
        differential = max(case['differentials'], key=lambda row: row['count'])
        count = sum(permutation[x] ^ permutation[x ^ differential['input_difference']] == differential['output_difference']
                    for x in range(65536))
        self.assertEqual(count, differential['count'])
        linear = max(case['linear'], key=lambda row: abs(row['signed_walsh']))
        signed = sum(1 if ((linear['input_mask'] & x).bit_count() +
                          (linear['output_mask'] & permutation[x]).bit_count()) % 2 == 0 else -1
                     for x in range(65536))
        self.assertEqual(signed, linear['signed_walsh'])


if __name__ == '__main__':
    unittest.main()
