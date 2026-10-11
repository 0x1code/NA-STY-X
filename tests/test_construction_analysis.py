import hashlib
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research'))
from construction_analysis import structural, schedules, mac_campaign, key_derivation, predicted_deltas, feistel
from generate_sbox_circuit import coefficients, evaluate_byte, SBOX


class ConstructionAnalysisTests(unittest.TestCase):
    def test_boolean_build_evidence_source_and_assembly_hashes(self):
        report = json.loads((ROOT / 'research/results/sbox-boolean-build-v1.json').read_text(encoding='utf8'))
        for name, digest in report['sources_sha256_utf8_lf'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_text(encoding='utf8').encode()).hexdigest(), digest)
        asm = (ROOT / report['assembly_fragment']).read_text(encoding='utf8')
        self.assertEqual(hashlib.sha256(asm.encode()).hexdigest(), report['assembly_sha256_utf8_lf'])
        self.assertEqual(len(report['repetitions']), 3)
        # Provenance is checked; this does not certify timing properties of the binary.

    def test_boolean_transform_exact_for_all_inputs_and_identity(self):
        for table in (list(range(256)), list(SBOX)):
            coeff = coefficients(table)
            self.assertEqual([evaluate_byte(x, coeff) for x in range(256)], table)
        identity = coefficients(list(range(256)))
        self.assertEqual([i for i, value in enumerate(identity) if value], [1, 2, 4, 8, 16, 32, 64, 128])

    def test_round_key_identity_and_period_three(self):
        report = structural(8, random.Random(20261012))
        self.assertEqual(report['checked_public_samples'], 8)
        deltas, output = predicted_deltas(1, 2, 24)
        self.assertEqual(deltas, [2, 3, 1] * 8)
        self.assertEqual(output, (1 << 64) | 2)

    def test_attack_harness_positive_controls_and_format_valid_forgery_attempts(self):
        report = mac_campaign(12, random.Random(20261012))
        self.assertEqual(report['total_attempts'], 132)
        self.assertEqual(report['accepted_total'], 0)
        self.assertEqual(report['unsafe_unframed_chain_positive_controls_succeeded'], 12)
        self.assertEqual(report['raw_segment_ambiguity_controls_succeeded'], 12)

    def test_schedule_and_derivation_scope(self):
        report = schedules(1, random.Random(20261012))
        self.assertEqual(report['master_pairs'], 256)
        self.assertEqual(sum(report['third_round_mismatch_bit_histogram'].values()), 256)
        report = key_derivation(4, random.Random(20261012))
        self.assertEqual(report['outputs_checked'], 20)
        self.assertEqual(report['compromised_chain_future_messages_decrypted'], 32)

    def test_published_results_provenance_and_exact_network_witness(self):
        report = json.loads((ROOT / 'research/results/construction-analysis-v1.json').read_text(encoding='utf8'))
        for name, digest in report['sources_sha256_utf8_lf'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_text(encoding='utf8').encode()).hexdigest(), digest)
        witness = report['structural']['full_24_round_witness']
        original = feistel(bytes.fromhex(witness['block']), [int(x, 16) for x in witness['round_keys']])
        self.assertEqual(original.hex(), witness['ciphertext'])
        keys = [int(x, 16) ^ int(d, 16) for x, d in zip(witness['round_keys'], witness['round_key_xor_deltas'])]
        changed = feistel(bytes.fromhex(witness['changed_block']), keys)
        self.assertEqual(changed.hex(), witness['changed_ciphertext'])
        self.assertEqual(int.from_bytes(original, 'big') ^ int.from_bytes(changed, 'big'), int(witness['output_xor'], 16))


if __name__ == '__main__':
    unittest.main()
