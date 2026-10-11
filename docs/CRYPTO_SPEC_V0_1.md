# NA&STY-X Research Cipher v0.1 (draft specification)

**Status:** research draft; not a standard and not approved for security use. All integer arithmetic is explicitly modulo `2^64` where stated.

## Parameters and encoding

- Block: 128 bits, encoded as 16 bytes.
- Master key: 256 bits, encoded as 32 bytes.
- Rounds: 16.
- Explicit research variants: 8, 12, 20 and 24 rounds, using the same key-expansion recurrence truncated or continued to the requested round count. They are separate labelled experiments; 16 remains the default and its original vector is unchanged.
- Split: `L0` is the first 8 block bytes and `R0` the final 8; both decode as unsigned big-endian 64-bit integers.
- Output: final `L16 || R16`, each encoded big-endian.
- Round key: one 64-bit word per round.
- This is a block permutation only. There is no padding, mode, authentication, nonce, or message format.

## S-box and byte permutation

The byte S-box is the AES S-box, generated from inversion in `GF(2^8)` with irreducible polynomial `x^8 + x^4 + x^3 + x + 1` (`0x11b`) and the AES affine map. For byte `a`, let `a^-1` be its multiplicative inverse, with `0^-1 = 0`. Then:

`S(a) = a^-1 XOR ROTL8(a^-1,1) XOR ROTL8(a^-1,2) XOR ROTL8(a^-1,3) XOR ROTL8(a^-1,4) XOR 0x63`.

The v0.1 byte permutation is `P = [2,5,0,7,4,1,6,3]`: output byte `j` is the S-box of input byte `P[j]`. It is a permutation of indices 0 through 7. The AES S-box is a standard component; its use here does not make the full construction equivalent to, or as secure as, AES.

## Key expansion

Parse key bytes into big-endian words `s0,s1,s2,s3`. Let `G = 0x9E3779B97F4A7C15`. For `i` from 0 through 15, compute:

```text
c  = G * (i + 1) mod 2^64
ki = (s0 + ROTL64(s1,13) + c mod 2^64)
     XOR ROTL64(s2,29) XOR s3
(s0,s1,s2,s3) = (s1,s2,s3, ki + ROTL64(old_s0,7) mod 2^64)
```

`ki` is the round key for round `i`. This transparent ad hoc schedule is not a cryptographic KDF and has not been analyzed for related-key, equivalent-key, or weak-key properties.

## Round function

For 64-bit input `x` and round key `k`:

1. Compute `q = x XOR k` and encode `q` as 8 little-endian bytes `q[0..7]`.
2. Set `b[j] = S(q[P[j]])` for `j = 0..7`.
3. Decode `b` as little-endian word `z`.
4. Return `F(x,k) = (z + ROTL64(z,17) mod 2^64) XOR ROTL64(z,41) XOR k`.

This combines key addition by XOR, nonlinear byte substitution, byte permutation, modular addition, and rotations/XOR. No claim is made that these choices provide adequate confusion or diffusion.

## Encryption and decryption

For each round `i=0..15`:

```text
Li+1 = Ri
Ri+1 = Li XOR F(Ri, ki)
```

For decryption, process `i=15..0`:

```text
Li = Ri+1 XOR F(Li+1, ki)
Ri = Li+1
```

Each round is invertible for every function `F`: from `(L',R')=(R,L XOR F(R,k))`, recover `R=L'`, then `L=R' XOR F(L',k)`. Thus the full network is a permutation for a fixed key. This proves reversibility only; it says nothing about secrecy or attack resistance.

## Known limits and open questions

- 16 rounds is an initial experimental choice; no reduced-round or full-round security bound is known.
- The custom key schedule has no security analysis.
- The byte permutation and ARX mixing need differential, linear, and bit-dependency analysis.
- Runtime S-box lookup is data-dependent and may leak through cache timing. The implementation is not constant-time.
- A 128-bit block has birthday-bound limitations if used repeatedly; this code does not define a safe usage limit or mode.
- No authenticated encryption, nonce discipline, key erasure, fault resistance, formal verification, or independent review is provided.
- The vector demonstrates implementation agreement only when reproduced independently; it is not evidence of security.

## Fixed vector

```text
rounds      = 16
key         = 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
plaintext   = 00112233445566778899aabbccddeeff
ciphertext  = f7d36b9993d7af9ae115d2c7458b6118
```

The JSON vector file is [`../tests/vectors/v0.1.json`](../tests/vectors/v0.1.json).

## Research variants

For a selected round count `r` in `{8,12,16,20,24}`, replace `16` by `r` in the iteration limits and output `Lr || Rr`. The key schedule computes `ki` for `i=0..r-1`, using exactly the recurrence above. Keys for a smaller variant are a prefix of the larger variant's schedule; variants are not domain-separated cryptosystems and must not be used concurrently as secure services.

Rust selects the variant explicitly with `Nastyx::with_rounds(key, RoundCount::R24)`; Python uses `encrypt_block(key, block, rounds=24)`. Unsupported counts are unrepresentable in the Rust enum and rejected in Python. Shared JSON/TSV fixtures contain 185 cases across all five supported counts.

The S-box definition follows [NIST FIPS 197](https://csrc.nist.gov/pubs/fips/197/final). This reference documents a component, not the security of NA&STY-X.
