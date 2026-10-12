import hashlib
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research'))
from advanced_analysis import (Engine, trace, related_masters, differential_linear,
                               derivation_and_mac, key_establishment)
from generate_sbox_circuit import circuit, coefficients, evaluate_circuit, generate, SBOX


class AdvancedAnalysisTests(unittest.TestCase):
    def test_generated_source_and_all_truth_table_values(self):
        nodes, root = circuit(coefficients(SBOX))
        self.assertEqual([evaluate_circuit(x, nodes, root) for x in range(256)], list(SBOX))
        self.assertEqual(generate()[0], (ROOT / 'crates/nastyx-engine/src/boolean_substitution.rs').read_text())

    def test_round_trace_uses_the_real_cipher(self):
        engine = Engine(bytes(range(32)))
        for x in (0, 1, (1 << 128) - 1, 123456789):
            self.assertEqual(trace(x, engine.keys)[-1], int.from_bytes(engine.encrypt(x.to_bytes(16, 'big')), 'big'))

    def test_constructed_master_pair_preserves_first_key(self):
        result = related_masters(1, 8, 8, random.Random(1), False)
        self.assertEqual(result['pairs_by_family']['first_round_key_preserving'], 32)
        for pair in result['first_round_preserving_controls']:
            a = Engine(bytes.fromhex(pair['master'])).keys
            b = Engine(bytes.fromhex(pair['related_master'])).keys
            self.assertEqual(a[0], b[0])
            self.assertNotEqual(a, b)

    def test_full_width_exact_controls(self):
        result = differential_linear(16, random.Random(2))
        keys = Engine(bytes.fromhex(result['master'])).keys
        for entry in result['differential']:
            delta = int(entry['input_xor'], 16)
            x = int(entry['witness']['plaintext'], 16)
            observed = [a ^ b for a, b in zip(trace(x, keys[:8]), trace(x ^ delta, keys[:8]))]
            self.assertEqual(observed, [int(d, 16) for d in entry['witness']['xor_path']])
            if delta & ((1 << 64) - 1) == 0:
                self.assertEqual(entry['rounds'][0]['max_observed_joint_trail_count'], 16)
                self.assertEqual(observed[0], delta >> 64)
        one = result['linear_selected'][0]
        self.assertEqual(one['discovery_signed_sum'], 16)
        self.assertEqual(one['holdout_signed_sum'], 16)

    def test_forgery_and_low_entropy_recovery_controls(self):
        result = derivation_and_mac(2, 4, random.Random(3))
        self.assertEqual(result['tag_bit_forgery_attempts'], 256)
        self.assertEqual(result['accepted_forgeries'], 0)
        self.assertEqual(result['positive_controls']['same_key_nonce_plaintext_xor_leaked'], 2)
        self.assertEqual(result['positive_controls']['past_key_dictionary']['recovered_past_plaintext'], 'past message control')

    def test_rejected_exchange_and_refresh_counterexample(self):
        result = key_establishment(4, random.Random(4))
        self.assertEqual(result['agreements'], 0)
        witness = result['counterexample']
        self.assertNotEqual(witness['proposed'], witness['bob_result'])
        a, b = Engine(bytes.fromhex(witness['alice_lab_key'])), Engine(bytes.fromhex(witness['bob_lab_key']))
        proposed = bytes.fromhex(witness['proposed'])
        self.assertEqual(b.decrypt(a.decrypt(b.encrypt(a.encrypt(proposed)))).hex(), witness['bob_result'])
        self.assertTrue(result['refresh_control']['new_root_predicted'])

    def test_published_analysis_provenance(self):
        result = json.loads((ROOT / 'research/results/advanced-analysis-v1.json').read_text())
        self.assertFalse(result['smoke'])
        for name, digest in result['sources_sha256_utf8_lf'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_text(encoding='utf8').encode()).hexdigest(), digest)

    def test_hardened_build_source_and_assembly_provenance(self):
        result = json.loads((ROOT / 'research/results/hardened-build-v1.json').read_text())
        for name, digest in result['sources_sha256_utf8_lf'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_text(encoding='utf8').encode()).hexdigest(), digest)
        for fragment in result['assembly'].values():
            source = (ROOT / fragment['path']).read_text(encoding='utf8')
            self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), fragment['sha256_utf8_lf'])
        self.assertEqual(len(result['benchmarks']['compare_sboxes']['repetitions']), 6)


if __name__ == '__main__':
    unittest.main()
