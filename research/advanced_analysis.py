"""Bounded full-width adversarial experiments; all keys are public lab fixtures.

Exact controls, sampled characteristics, and unsuccessful attack searches are
reported separately. No random-permutation security or 256-bit strength claim.
"""
import argparse
import hashlib
import itertools
import json
import platform
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/reference_cipher'))
from engine_v3 import Engine, MASK, rot, round_function
from message_v3 import Message, domain
from session_v1 import expand, step

SEED = 2026101207


def trace(block, keys):
    left, right = block >> 64, block & MASK
    states = []
    for key in keys:
        left, right = right, left ^ round_function(right, key)
        states.append((left << 64) | right)
    return states


def schedule_score(keys, other):
    delta = [a ^ b for a, b in zip(keys, other)]
    period = [delta[0], delta[1], delta[0] ^ delta[1]]
    return sum((d ^ period[i % 3]).bit_count() for i, d in enumerate(delta[2:], 2)), delta


def structured_deltas():
    for byte in (0x01, 0x80, 0xff, 0x55, 0xaa):
        yield 'repeated_byte', int.from_bytes(bytes([byte]) * 32, 'big')
    for word in range(4):
        for width in (2, 4, 8, 16, 32, 64):
            for offset in range(0, 65 - width, width):
                yield 'word_bit_runs', ((1 << width) - 1) << (word * 64 + offset)
    for bit in range(64):
        for words in (3, 5, 9, 6, 10, 12, 15):
            yield 'repeated_word_bits', sum(1 << (word * 64 + bit) for word in range(4) if words >> word & 1)


def related_masters(bases, random_pairs, hill_steps, rng, exhaustive_two_bits=True):
    masters = [bytes(32), bytes([255]) * 32, bytes(range(32))]
    masters += [rng.randbytes(32) for _ in range(max(0, bases - 3))]
    counts, equivalents, periodic = Counter(), 0, 0
    best = None
    first_round_controls = []

    def inspect(master, original, candidate, family):
        nonlocal equivalents, periodic, best
        altered = Engine(candidate).keys
        score, delta = schedule_score(original, altered)
        counts[family] += 1
        equivalents += not any(delta)
        periodic += score == 0 and any(delta)
        if best is None or score < best['mismatching_bits_rounds_3_to_24']:
            best = {'master': master.hex(), 'related_master': candidate.hex(), 'family': family,
                    'mismatching_bits_rounds_3_to_24': score,
                    'round_key_xor': [f'{d:016x}' for d in delta]}
        return score

    for master in masters[:bases]:
        number, original = int.from_bytes(master, 'big'), Engine(master).keys
        if exhaustive_two_bits:
            for a, b in itertools.combinations(range(256), 2):
                inspect(master, original, (number ^ (1 << a) ^ (1 << b)).to_bytes(32, 'big'), 'all_two_bit_xors')
        for family, delta in structured_deltas():
            inspect(master, original, (number ^ delta).to_bytes(32, 'big'), family)
        for index in range(random_pairs):
            weight = (3, 4, 8, 16, 32, 64, 128, 255)[index % 8]
            delta = sum(1 << bit for bit in rng.sample(range(256), weight))
            inspect(master, original, (number ^ delta).to_bytes(32, 'big'), f'random_weight_{weight}')
        # Algebraic family: freely select a',b',c' and compensate d' to preserve k0.
        a, b, c, d = [int.from_bytes(master[i:i + 8], 'big') for i in range(0, 32, 8)]
        constant = 0x9e3779b97f4a7c15
        before = round_function(a ^ rot(b, 13), c ^ constant)
        for _ in range(32):
            aa, bb, cc = (rng.getrandbits(64) for _ in range(3))
            dd = d ^ before ^ round_function(aa ^ rot(bb, 13), cc ^ constant)
            candidate = b''.join(x.to_bytes(8, 'big') for x in (aa, bb, cc, dd))
            altered = Engine(candidate).keys
            assert original[0] == altered[0]
            inspect(master, original, candidate, 'first_round_key_preserving')
            if _ == 0:
                first_round_controls.append({'master': master.hex(), 'related_master': candidate.hex(),
                                             'shared_round_1_key': f'{original[0]:016x}'})
        # Local optimization is not uniform sampling. Store its own family count.
        candidate = number ^ rng.getrandbits(256)
        score = inspect(master, original, candidate.to_bytes(32, 'big'), 'hill_climb')
        for _ in range(hill_steps):
            proposed = candidate ^ (1 << rng.randrange(256))
            if proposed == number:
                continue
            proposed_score = inspect(master, original, proposed.to_bytes(32, 'big'), 'hill_climb')
            if proposed_score <= score:
                candidate, score = proposed, proposed_score
    return {'base_masters': bases, 'pairs_by_family': dict(counts), 'pairs_total': sum(counts.values()),
            'equivalent_schedules': equivalents, 'nonzero_period_three_schedules': periodic,
            'closest_observed': best, 'first_round_preserving_controls': first_round_controls,
            'scope': 'Selected baselines; exhaustive weight-two deltas only when enabled; bounded structured/random/local search. No exclusion of other relations.'}


def differential_linear(samples, rng):
    key = rng.randbytes(32)
    keys = Engine(key).keys[:8]
    deltas = [1 << bit for bit in (0, 7, 31, 63, 64, 95, 127)]
    deltas += [MASK, MASK << 64, (1 << 128) - 1]
    differential = []
    for delta in deltas:
        # Each complete path is counted jointly. Never multiply dependent rounds.
        outputs = [Counter() for _ in keys]
        trails = [Counter() for _ in keys]
        first = None
        for _ in range(samples):
            plain = rng.getrandbits(128)
            a, b = trace(plain, keys), trace(plain ^ delta, keys)
            path = tuple(x ^ y for x, y in zip(a, b))
            for index, value in enumerate(path):
                outputs[index][value] += 1
                trails[index][path[:index + 1]] += 1
            if first is None:
                first = {'plaintext': f'{plain:032x}', 'xor_path': [f'{d:032x}' for d in path]}
        differential.append({'input_xor': f'{delta:032x}', 'samples': samples,
                             'rounds': [{'rounds': i + 1,
                                         'max_observed_full_output_count': max(outputs[i].values()),
                                         'max_observed_joint_trail_count': max(trails[i].values()),
                                         'most_frequent_output': f'{outputs[i].most_common(1)[0][0]:032x}'}
                                        for i in range(8)], 'witness': first})
    # Predetermined sparse/dense masks plus random masks; discovery/holdout split.
    masks = [(1 << bit, 1 << (bit + 64)) for bit in (0, 7, 31, 63)]
    masks += [(1 << rng.randrange(128), 1 << rng.randrange(128)) for _ in range(60)]
    masks += [(rng.getrandbits(128), rng.getrandbits(128)) for _ in range(64)]

    def correlations():
        accum = [[0] * len(masks) for _ in keys]
        for _ in range(samples):
            x = rng.getrandbits(128)
            states = trace(x, keys)
            for index, (a, b) in enumerate(masks):
                parity = (x & a).bit_count() & 1
                for r, y in enumerate(states):
                    accum[r][index] += 1 if parity == ((y & b).bit_count() & 1) else -1
        return accum

    discover, holdout = correlations(), correlations()
    linear = []
    for r in range(8):
        selected = max(range(len(masks)), key=lambda i: abs(discover[r][i]))
        a, b = masks[selected]
        linear.append({'rounds': r + 1, 'input_mask': f'{a:032x}', 'output_mask': f'{b:032x}',
                       'discovery_signed_sum': discover[r][selected],
                       'holdout_signed_sum': holdout[r][selected], 'denominator_each': samples})
    return {'master': key.hex(), 'width_bits': 128, 'differential': differential,
            'linear_masks_tested': len(masks), 'linear_selected': linear,
            'exact_controls': ['For one round: input difference (d,0) -> output (0,d) for every block/key.',
                               'For one round: parity(mask & input_R) = parity(mask & output_L).'],
            'scope': '1..8 rounds of the full-width v0.3 function, fixed master. Observed joint paths and holdout mask correlations, NOT optimal trails, exhaustive probabilities, p-values or 24-round bounds.'}


def derivation_and_mac(samples, dictionary_bits, rng):
    accepted, attempts, same_nonce_xor, replay = 0, 0, 0, 0
    relation_counts = Counter()
    for index in range(samples):
        key, context = rng.randbytes(32), rng.randbytes(80)
        roles = []
        root = Engine(key)
        for role in (1, 2, 3):
            roles.append(root.encrypt(domain(75, role, 0)) + root.encrypt(domain(75, role, 1)))
        for left, right in itertools.combinations(roles, 2):
            score, delta = schedule_score(Engine(left).keys, Engine(right).keys)
            relation_counts['pairs'] += 1
            relation_counts['equal_subkeys'] += left == right
            relation_counts['period_three_schedules'] += score == 0 and any(delta)
        mk, after = step(key, 0, index)
        relation_counts['message_equals_next'] += mk == after
        relation_counts['halves_equal'] += mk[:16] == mk[16:]
        for label in (10, 20, 21, 30, 31):
            a = expand(key, label, context)
            b = expand(key, label, context + b'\x00')
            relation_counts['context_extension_collisions'] += a == b
        message = Message(key)
        nonce, plain = rng.randbytes(12), rng.randbytes(32)
        record = message.seal_for_vector(nonce, plain, context)
        # Mutating every tag bit reaches the authenticator with a valid frame.
        for bit in range(128):
            forged = bytearray(record)
            forged[-16 + bit // 8] ^= 1 << (bit % 8)
            attempts += 1
            try:
                message.open(bytes(forged), context)
                accepted += 1
            except ValueError:
                pass
        # Positive misuse controls: message layer deliberately has no replay state.
        assert message.open(record, context) == message.open(record, context) == plain
        replay += 1
        another = rng.randbytes(32)
        reused = message.seal_for_vector(nonce, another, context)
        assert bytes(a ^ b for a, b in zip(record[28:-16], reused[28:-16])) == bytes(a ^ b for a, b in zip(plain, another))
        same_nonce_xor += 1
    # Exhaustive recovery in an explicitly weak toy keyspace, using full algorithms.
    # Revealing chain_{n+1} permits testing guesses at chain_n offline. This is not
    # an inversion of uniform 256-bit states; the bound here is only 2^bits.
    secret_number = rng.randrange(1 << dictionary_bits)
    weak_chain = secret_number.to_bytes(32, 'big')
    old_mk, exposed_next = step(weak_chain, 0, 0)
    old_packet = Message(old_mk).seal_for_vector(bytes(12), b'past message control', b'dictionary lab')
    found, checked = None, 0
    for candidate in range(1 << dictionary_bits):
        checked += 1
        _, next_chain = step(candidate.to_bytes(32, 'big'), 0, 0)
        if next_chain == exposed_next:
            found = candidate
            break
    assert found == secret_number
    recovered_mk, _ = step(found.to_bytes(32, 'big'), 0, 0)
    recovered = Message(recovered_mk).open(old_packet, b'dictionary lab')
    assert recovered == b'past message control'
    return {'cases': samples, 'tag_bit_forgery_attempts': attempts, 'accepted_forgeries': accepted,
            'relations': dict(relation_counts), 'positive_controls': {'message_layer_replay_accepted': replay,
            'same_key_nonce_plaintext_xor_leaked': same_nonce_xor,
            'past_key_dictionary': {'entropy_bits': dictionary_bits, 'guesses': checked,
                                    'public_weak_chain': weak_chain.hex(), 'recovered_past_plaintext': recovered.decode()}},
            'scope': 'Bounded key-role checks and valid-frame forgeries, plus expected misuse failures. No PRF proof, high-entropy past-key recovery, or MAC security bound.'}


def key_establishment(samples, rng):
    agreements, witness = 0, None
    for _ in range(samples):
        a, b, proposed = rng.randbytes(32), rng.randbytes(32), rng.randbytes(16)
        alice, bob = Engine(a), Engine(b)
        first = alice.encrypt(proposed)
        second = bob.encrypt(first)
        third = alice.decrypt(second)
        recovered = bob.decrypt(third)
        agreements += recovered == proposed
        if witness is None and recovered != proposed:
            witness = {'alice_lab_key': a.hex(), 'bob_lab_key': b.hex(), 'proposed': proposed.hex(),
                       'first': first.hex(), 'second': second.hex(), 'third': third.hex(), 'bob_result': recovered.hex()}
    # Sending fresh entropy inside an already compromised symmetric channel
    # does not restore secrecy from the observer of that channel.
    stolen = rng.randbytes(32)
    random_refresh = rng.randbytes(32)
    mk, _ = step(stolen, 0, 7)
    refresh_packet = Message(mk).seal_for_vector(bytes(12), random_refresh, b'NXP0-refresh-control')
    adversary_mk, _ = step(stolen, 0, 7)
    recovered_refresh = Message(adversary_mk).open(refresh_packet, b'NXP0-refresh-control')
    honest_root = expand(stolen, 40, random_refresh)
    adversary_root = expand(stolen, 40, recovered_refresh)
    assert honest_root == adversary_root
    return {'candidate': 'NXP0 lab only: three-pass E_a, E_b, D_a, D_b using the original cipher',
            'agreement_trials': samples, 'agreements': agreements, 'counterexample': witness,
            'decision': 'REJECTED: block encryptions do not generally commute; correctness fails before secrecy analysis.',
            'refresh_control': {'fresh_entropy_recovered_from_compromised_channel': recovered_refresh == random_refresh,
                                'new_root_predicted': adversary_root == honest_root},
            'deployment': 'No candidate added to NXS1. First contact without a shared secret and automatic PCS remain unsolved.'}


def run(bases=4, samples=2048, random_pairs=512, hill_steps=2048, cases=32, dictionary_bits=12, smoke=False):
    if min(bases, samples, cases) < 1 or not 1 <= dictionary_bits <= 16:
        raise ValueError('positive counts and 1..16 dictionary bits required')
    start, rng = time.perf_counter(), random.Random(SEED)
    paths = ['research/advanced_analysis.py', 'research/reference_cipher/engine_v3.py',
             'research/reference_cipher/message_v3.py', 'research/reference_cipher/session_v1.py']
    report = {'format': 'nastyx-advanced-analysis-v1', 'seed': SEED, 'python': platform.python_version(),
              'platform': platform.platform(), 'smoke': smoke,
              'parameters': {'bases': bases, 'samples': samples, 'random_pairs': random_pairs,
                             'hill_steps': hill_steps, 'cases': cases, 'dictionary_bits': dictionary_bits},
              'sources_sha256_utf8_lf': {p: hashlib.sha256((ROOT / p).read_text(encoding='utf8').encode()).hexdigest() for p in paths}}
    report['related_masters'] = related_masters(bases, random_pairs, hill_steps, rng, not smoke)
    print('Related-master search finished', flush=True)
    report['full_width_reduced_rounds'] = differential_linear(samples, rng)
    print('Full-width differential/linear probes finished', flush=True)
    report['mac_kdf'] = derivation_and_mac(cases, dictionary_bits, rng)
    report['key_establishment'] = key_establishment(cases, rng)
    report['elapsed_seconds'] = time.perf_counter() - start
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'research/results/advanced-analysis-v1.json')
    args = parser.parse_args()
    report = run(1, 16, 8, 8, 2, 4, True) if args.smoke else run()
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(f'Results: {args.output}; {report["elapsed_seconds"]:.2f}s', flush=True)
