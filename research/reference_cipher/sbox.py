"""NA&STY-X S-box v0.2: public deterministic construction, not a cipher RNG."""

DESIGN_SEED = 0x4E415859
DESIGN_ROUNDS = 12
SELECTED_CANDIDATE = 18  # Frozen after the public screening experiment.


def make_sbox(candidate: int) -> tuple[int, ...]:
    if type(candidate) is not int or not 0 <= candidate < 256:
        raise ValueError('candidate must be an integer in 0..255')
    state = (DESIGN_SEED + candidate * 0x9E3779B9) & 0xFFFFFFFF
    rounds = []
    for _ in range(DESIGN_ROUNDS):
        table = list(range(16))
        for j in range(15, 0, -1):
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            index = (state >> 16) % (j + 1)
            table[j], table[index] = table[index], table[j]
        rounds.append(table)
    result = []
    for value in range(256):
        left, right = value >> 4, value & 15
        for table in rounds:
            left, right = right, left ^ table[right]
        result.append((left << 4) | right)
    return tuple(result)


NASTYX_SBOX = make_sbox(SELECTED_CANDIDATE)
