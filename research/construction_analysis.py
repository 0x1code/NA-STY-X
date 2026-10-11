"""Bounded adversarial analysis of the current original constructions.

Public deterministic lab data only. Exact round-key identities are distinct from
attacks on the master-key schedule; failed attempts do not establish MAC security.
"""
import argparse
import hashlib
import json
import platform
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/reference_cipher'))
from engine_v3 import Engine, round_function
from message_v3 import Message
from session_v1 import expand, step

MASK = (1 << 64) - 1
SEED = 20261012


def feistel(block, keys):
    left, right = int.from_bytes(block[:8], 'big'), int.from_bytes(block[8:], 'big')
    for key in keys:
        left, right = right, left ^ round_function(right, key)
    return left.to_bytes(8, 'big') + right.to_bytes(8, 'big')


def predicted_deltas(left, right, rounds):
    keys = []
    for _ in range(rounds):
        keys.append(right)
        left, right = right, left ^ right
    return keys, (left << 64) | right


def structural(samples, rng):
    witness = None
    for _ in range(samples):
        x, key, delta = (rng.getrandbits(64) for _ in range(3))
        assert round_function(x ^ delta, key ^ delta) == round_function(x, key) ^ delta
        keys = [rng.getrandbits(64) for _ in range(24)]
        left, right = rng.getrandbits(64), rng.getrandbits(64)
        block = rng.randbytes(16)
        deltas, out_delta = predicted_deltas(left, right, 24)
        changed = (int.from_bytes(block, 'big') ^ (left << 64) ^ right).to_bytes(16, 'big')
        cipher = feistel(block, keys)
        altered = feistel(changed, [k ^ d for k, d in zip(keys, deltas)])
        assert int.from_bytes(cipher, 'big') ^ int.from_bytes(altered, 'big') == out_delta
        if witness is None:
            witness = {'block': block.hex(), 'changed_block': changed.hex(),
                       'round_keys': [f'{k:016x}' for k in keys],
                       'round_key_xor_deltas': [f'{d:016x}' for d in deltas],
                       'ciphertext': cipher.hex(), 'changed_ciphertext': altered.hex(),
                       'input_xor': f'{((left << 64) | right):032x}',
                       'output_xor': f'{out_delta:032x}'}
    return {'round_function_identity': 'F(x XOR d,k XOR d) = F(x,k) XOR d',
            'proof': 'F(x,k)=G(P(S(x XOR k))) XOR k; simultaneous XOR leaves the argument to G unchanged.',
            'network_condition': 'round-key deltas equal right-half deltas; (a,b) evolves to (b,a XOR b), period 3',
            'status': 'Exact for arbitrary 64-bit deltas and supplied round keys; not a master-key attack.',
            'checked_public_samples': samples, 'full_24_round_witness': witness}


def schedules(bases, rng):
    masters = [bytes(32), bytes([255]) * 32, bytes(range(32))]
    masters += [rng.randbytes(32) for _ in range(max(0, bases - 3))]
    probes, periodic, collisions = 0, 0, 0
    third_histogram = Counter()
    witness = None
    for master in masters[:bases]:
        original = Engine(master).keys
        for bit in range(256):
            altered = bytearray(master)
            altered[bit // 8] ^= 1 << (bit % 8)
            changed = Engine(bytes(altered)).keys
            diff = [a ^ b for a, b in zip(original, changed)]
            expected = [diff[0], diff[1], diff[0] ^ diff[1]]
            third_histogram[(diff[2] ^ expected[2]).bit_count()] += 1
            match = all(value == expected[i % 3] for i, value in enumerate(diff))
            probes += 1
            collisions += not any(diff)
            periodic += match and any(diff)
            if match and witness is None:
                witness = {'master': master.hex(), 'related_master': bytes(altered).hex(),
                           'deltas': [f'{d:016x}' for d in diff]}
    return {'base_master_keys': bases, 'master_pairs': probes,
            'scope': 'Every one-bit master-key XOR for each stated public baseline; no other master relations.',
            'equivalent_schedule_pairs': collisions, 'period_3_related_schedule_pairs': periodic,
            'first_match': witness, 'third_round_mismatch_bit_histogram': dict(sorted(third_histogram.items()))}


def raw_chain(engine, data):
    """Intentionally unsafe positive control: no length binding/finalization."""
    if not data or len(data) % 16:
        raise ValueError('whole nonempty blocks required')
    state = bytes(16)
    for offset in range(0, len(data), 16):
        state = engine.encrypt(bytes(a ^ b for a, b in zip(state, data[offset:offset + 16])))
    return state


def frame(record, aad, ciphertext, tag=None, nonce=None):
    header = bytearray(record[:28])
    if nonce is not None:
        header[8:20] = nonce
    header[20:24] = len(aad).to_bytes(4, 'big')
    header[24:28] = len(ciphertext).to_bytes(4, 'big')
    return bytes(header) + ciphertext + (record[-16:] if tag is None else tag)


def valid_frame(record, aad):
    return (len(record) >= 44 and record[:8] == b'NXM3' + bytes([3, 1, 0, 0])
            and int.from_bytes(record[20:24], 'big') == len(aad)
            and int.from_bytes(record[24:28], 'big') == len(record) - 44)


def mac_campaign(cases, rng):
    accepted, attempts = Counter(), Counter()
    positive_controls = 0
    raw_ambiguities = 0
    for index in range(cases):
        key = rng.randbytes(32)
        message = Message(key)
        size = (0, 1, 15, 16, 17, 31, 32, 33, 64, 128, 255)[index % 11]
        aad = rng.randbytes((0, 1, 15, 16, 17, 32)[index % 6])
        record = message.seal_for_vector(index.to_bytes(12, 'big'), rng.randbytes(size), aad)
        other = message.seal_for_vector((index + cases).to_bytes(12, 'big'), rng.randbytes(size), aad)
        cipher, tag = record[28:-16], record[-16:]
        forged = [(name, frame(record, aad, body), aad) for name, body in (
            ('append_zero_block', cipher + bytes(16)),
            ('append_padding_like_block', cipher + b'\x80' + bytes(15)),
            ('truncate_ciphertext', cipher[:-1] if cipher else b'\x00'),
            ('splice_other_ciphertext', other[28:-16] if size else b'\x00'),
            ('replace_ciphertext_with_tag', tag),
            ('naive_tag_chain_extension', cipher + bytes(a ^ b for a, b in zip(tag, cipher[:16].ljust(16, b'\x00')))),
        )]
        forged += [('substitute_tag', frame(record, aad, cipher, tag=other[-16:]), aad),
                   ('alter_nonce', frame(record, aad, cipher, nonce=(index + 2 * cases).to_bytes(12, 'big')), aad),
                   ('transfer_to_other_key', record, aad)]
        # Keep aad||cipher bytes equal while changing the declared partition.
        if aad:
            shifted_aad, shifted_cipher = aad[:-1], aad[-1:] + cipher
        else:
            shifted_aad, shifted_cipher = b'\x00', cipher
        forged.append(('change_context_partition', frame(record, shifted_aad, shifted_cipher), shifted_aad))
        changed_aad = bytes([aad[0] ^ 1]) + aad[1:] if aad else b'\x01'
        forged.append(('change_context', frame(record, changed_aad, cipher), changed_aad))
        for name, packet, context in forged:
            assert valid_frame(packet, context), 'must reach authentication, not only parser rejection'
            attempts[name] += 1
            target = Message(bytes(a ^ 1 for a in key)) if name == 'transfer_to_other_key' else message
            try:
                target.open(packet, context)
                accepted[name] += 1
            except ValueError:
                pass
        # Proves attack harness detects the known raw-chain extension mechanism.
        engine, block = Engine(key), rng.randbytes(16)
        raw_tag = raw_chain(engine, block)
        extension = block + bytes(a ^ b for a, b in zip(block, raw_tag))
        assert raw_chain(engine, extension) == raw_tag
        positive_controls += 1
        # Raw tag helper does not delimit segments; public wrappers MUST bind lengths.
        assert message.tag(record[:28], b'a', b'bc') == message.tag(record[:28], b'ab', b'c')
        raw_ambiguities += 1
    return {'records': cases, 'attempts': dict(attempts), 'accepted': dict(accepted),
            'total_attempts': sum(attempts.values()), 'accepted_total': sum(accepted.values()),
            'all_forged_frames_syntactically_valid': True,
            'unsafe_unframed_chain_positive_controls_succeeded': positive_controls,
            'raw_segment_ambiguity_controls_succeeded': raw_ambiguities,
            'scope': 'Specific public-record manipulation families only. No cryptographic forgery bound or proof.'}


def key_derivation(samples, rng):
    outputs = set()
    collisions = 0
    for _ in range(samples):
        key, context = rng.randbytes(32), rng.randbytes(80)
        for label in (10, 20, 21, 30, 31):
            value = expand(key, label, context)
            collisions += value in outputs
            outputs.add(value)
    # Current-chain compromise predicts future keys exactly; do not label that PCS.
    chain = rng.randbytes(32)
    attacker = chain
    successes = 0
    for n in range(32):
        message_key, chain = step(chain, 0, n)
        stolen_key, attacker = step(attacker, 0, n)
        packet = Message(message_key).seal_for_vector(bytes(12), b'public compromise witness', b'context')
        assert Message(stolen_key).open(packet, b'context') == b'public compromise witness'
        successes += 1
    return {'public_master_context_pairs': samples, 'labels': [10, 20, 21, 30, 31],
            'outputs_checked': samples * 5, 'sample_output_collisions': collisions,
            'compromised_chain_future_messages_decrypted': successes,
            'scope': 'Sample collisions only, not PRF/one-way proof. Future prediction is an exact consequence of deterministic steps.'}


def run(samples=128, bases=32, cases=128):
    if samples < 1 or bases < 1 or cases < 1:
        raise ValueError('positive counts required')
    start = time.perf_counter()
    rng = random.Random(SEED)
    sources = ['research/construction_analysis.py', 'research/reference_cipher/engine_v3.py',
               'research/reference_cipher/message_v3.py', 'research/reference_cipher/session_v1.py']
    report = {'format': 'nastyx-construction-analysis-v1', 'seed': SEED,
              'warning': 'Bounded research. Structural witnesses and failed attempts do not establish real-data security.',
              'python': platform.python_version(), 'platform': platform.platform(),
              'sources_sha256_utf8_lf': {name: hashlib.sha256((ROOT / name).read_text(encoding='utf8').encode()).hexdigest()
                                        for name in sources}}
    report['structural'] = structural(samples, rng)
    print('Exact full-width related-round-key witnesses checked', flush=True)
    report['schedule_search'] = schedules(bases, rng)
    print('Bounded master-key schedule search complete', flush=True)
    report['authentication'] = mac_campaign(cases, rng)
    report['derivation'] = key_derivation(samples, rng)
    report['elapsed_seconds'] = time.perf_counter() - start
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=128)
    parser.add_argument('--bases', type=int, default=32)
    parser.add_argument('--cases', type=int, default=128)
    parser.add_argument('--output', type=Path, default=ROOT / 'research/results/construction-analysis-v1.json')
    args = parser.parse_args()
    report = run(args.samples, args.bases, args.cases)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps({name: report[name] for name in ('schedule_search', 'authentication', 'derivation')}, indent=2))
