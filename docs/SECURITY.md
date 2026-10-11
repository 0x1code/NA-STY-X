# Security status — v0.3 research revision

The original cipher, subkey derivation and message tag have no independent cryptanalysis or security bounds. Do not use this revision to protect real secrets. See `CRYPTO_SPEC_V0_3.md` and `MESSAGE_SPEC_V0_3.md`.

Message encryption and tag verification are implemented; this does not establish confidentiality or forgery resistance. The receiver authenticates before decrypting. Nonces are reserved in one shared persistent registry per key; missing/corrupt metadata fail closed. Never reuse a key after losing or rolling back this state. Windows power-loss durability of directory metadata is not established. Local storage tampering/rollback, network filesystems and multiple registries for the same key are outside the nonce guarantee.

Table access depends on secrets, compiler-level constant time is unverified, and key memory is not guaranteed to be erased. No key exchange, replay protection, forward secrecy or full session protocol is implemented. Public examples use test keys, not real secrets. Functional tests and improved statistical metrics do not replace a cryptographic review.

## Historical v0.2 status

# Security status

NA&STY-X v0.2.0-alpha is experimental research software. **Do not use the cipher or CLI to protect real secrets.** It has not had independent cryptanalysis, implementation audit, formal verification, or side-channel review.

The research cipher is a raw block permutation. It does not authenticate data and does not define a mode, nonce, padding, or message encoding. Repeated encryption of blocks directly would expose patterns. The Rust S-box is a data-dependent table lookup and is not constant-time. The simple key schedule is an unreviewed design choice.

The current test suite checks the full independently generated custom S-box, 185 shared vectors across five round counts, input validation in Python, round-trip reversibility, exact S-box metrics, and the statistical tools against small examples. These checks catch some implementation errors; they do not establish cryptographic security. The laboratory reports descriptive avalanche, SAC and bit-pair correlation estimates. Its published 32-sample results must not be treated as proof of randomness or resistance to attack. In particular, extreme correlations in this small sample do not establish an attack or independent bits.

Research variants share prefixes of the same round-key schedule and have no domain separation. No round count is approved for protecting data. Differential/linear attacks on the full network, related-key attacks, weak-key analysis beyond a small public family, and implementation side channels remain open work.

The current scope is an original protocol; message authentication, message encryption mode and authenticated key establishment remain unimplemented. The replacement S-box has weaker measured differential/linear properties than the historical AES S-box. Independent cryptanalysis and implementation review are required before any claim of protecting real data. Report security issues privately to the project maintainers until a disclosure process is established.
