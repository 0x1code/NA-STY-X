# Threat model (Phase 1)

Current code is cipher revision v0.2 with a custom substitution table. Historical v0.1 measurements do not describe the current table. The original protocol's design assumptions and missing mechanisms are recorded in `PROTOCOL_DESIGN.md`; no secure channel is implemented.

The cipher is a mathematical research target, not an application security boundary. Researchers can test fixed-key block behavior and implementation correctness. The implementation does not claim to resist a computationally capable attacker.

In scope for future investigation: chosen-plaintext and chosen-ciphertext distinguishers, differential and linear trails, key-schedule relations, implementation inconsistencies, and basic statistical artifacts.

Out of scope for the current code: secure storage or transport, authentication, replay prevention, malicious peers, key exchange, nonce management, traffic analysis, fault injection, memory disclosure, secure key erasure, and constant-time execution. S-box table accesses are data-dependent. The demo prints no key material, but caller-provided keys remain in ordinary process memory.

No claim of protocol security follows from the reversible block implementation or the avalanche experiment. Secure messaging must be designed and reviewed as a separate system.
