# Security status

NA&STY-X v0.1.0-alpha is experimental research software. **Do not use the cipher or CLI to protect real secrets.** It has not had independent cryptanalysis, implementation audit, formal verification, or side-channel review.

The research cipher is a raw block permutation. It does not authenticate data and does not define a mode, nonce, padding, or message encoding. Repeated encryption of blocks directly would expose patterns. The Rust S-box is a data-dependent table lookup and is not constant-time. The simple key schedule is an unreviewed design choice.

The current test suite checks known AES S-box points, a reproducible block vector, input lengths in Python, and round-trip reversibility over a deterministic sample. These checks catch some implementation errors; they do not test cryptographic security. The avalanche script reports a small descriptive sample and must not be treated as proof of randomness or resistance to attack.

Future secure communication code must use maintained implementations of established cryptographic primitives, specify authenticated key establishment and key management, and receive independent review before any production claim. Report security issues privately to the project maintainers until a disclosure process is established.
