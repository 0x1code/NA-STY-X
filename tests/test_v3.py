import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/reference_cipher'))
sys.path.insert(0,str(ROOT/'research'))
from engine_v3 import Engine, SBOX
from message_v3 import Message
from lab import ddt, walsh
from optimize_sbox import optimize
from optimize_linear import run as optimize_linear
from full_width_v3 import degree


class V3Tests(unittest.TestCase):
    def test_sbox_metrics_and_provenance(self):
        import hashlib
        report = json.loads((ROOT/'research/results/sbox-linear-optimized-v1.json').read_text(encoding='utf-8'))
        self.assertEqual(tuple(report['table']),SBOX)
        self.assertEqual(len(set(SBOX)),256)
        differential,linear = ddt(SBOX),walsh(SBOX)
        self.assertEqual(max(max(row) for row in differential[1:]),8)
        self.assertEqual(max(abs(v) for row in linear for v in row[1:]),52)
        for source,report_file in [('optimize_sbox.py','sbox-optimized-v1.json'),('optimize_linear.py','sbox-linear-optimized-v1.json')]:
            data = json.loads((ROOT/'research/results'/report_file).read_text(encoding='utf-8'))
            self.assertEqual(hashlib.sha256((ROOT/'research'/source).read_text(encoding='utf-8').encode()).hexdigest(),data['generator_sha256'])

    def test_all_block_vectors(self):
        lines = (ROOT/'tests/vectors/v0.3-blocks.tsv').read_text().splitlines()[1:]
        self.assertEqual(len(lines),185)
        for line in lines:
            rounds,key,block,cipher = line.split('\t')
            engine = Engine(bytes.fromhex(key),int(rounds))
            self.assertEqual(engine.encrypt(bytes.fromhex(block)).hex(),cipher)
            self.assertEqual(engine.decrypt(bytes.fromhex(cipher)).hex(),block)

    def test_messages_and_tampering(self):
        vectors = json.loads((ROOT/'tests/vectors/v0.3-messages.json').read_text())['vectors']
        for case in vectors:
            key,nonce,plain,aad,record = [bytes.fromhex(case[k]) for k in ('key','nonce','plaintext','aad','record')]
            message = Message(key)
            self.assertEqual(message.seal_for_vector(nonce,plain,aad),record)
            self.assertEqual(message.open(record,aad),plain)
            for index in range(len(record)):
                changed = bytearray(record); changed[index] ^= 1
                with self.assertRaises(ValueError): message.open(bytes(changed),aad)
            with self.assertRaises(ValueError): Message(bytes(32)).open(record,aad)
            with self.assertRaises(ValueError): message.open(record,aad+b'x')

    def test_input_validation(self):
        for size in (0,31,33):
            with self.assertRaises(ValueError): Engine(bytes(size))
        for rounds in (0,9,True,16.0):
            with self.assertRaises(ValueError): Engine(bytes(32),rounds)
        with self.assertRaises(ValueError): Engine(bytes(32)).encrypt(bytes(15))

    def test_incremental_optimizers_and_algebraic_degree(self):
        result = optimize(iterations=8)
        self.assertLessEqual(result['final_energy'],result['initial_energy'])
        linear = optimize_linear(iterations=8)
        self.assertLessEqual(linear['final_energy'],linear['initial_energy'])
        for mask in (1,2,3,255):
            self.assertIn(degree(mask),range(1,8))

    def test_full_width_report_source_hashes(self):
        import hashlib
        report = json.loads((ROOT/'research/results/full-width-v3.json').read_text())
        for name,digest in report['sources'].items():
            self.assertEqual(hashlib.sha256((ROOT/'research'/name).read_text(encoding='utf-8').encode()).hexdigest(),digest)
        self.assertEqual(report['key_family']['unique_master_keys'],1024)
        self.assertEqual(report['key_family']['distinct_schedules'],1024)

    def test_v3_toy_model_all_blocks_and_report(self):
        import hashlib
        from reduced_model_v3 import expand_toy_key,round_table,permute
        report = json.loads((ROOT/'research/results/reduced-model-v3.json').read_text())
        self.assertEqual(hashlib.sha256((ROOT/'research/reduced_model_v3.py').read_text(encoding='utf-8').encode()).hexdigest(),report['source_sha256'])
        self.assertEqual(report['format'],'nastyx-toy-v3-analysis-v1')
        self.assertEqual(len(report['cases']),12)
        tables = [round_table(k) for k in expand_toy_key(0x76543210,8)]
        for value in range(65536):
            self.assertEqual(permute(permute(value,tables),tables,decrypt=True),value)
