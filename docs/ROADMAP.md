# Roadmap

## Phase 1 — Foundation (implemented)

- Workspace, experimental Rust block cipher, Python reference, vector, basic reversibility checks, small avalanche probe, CLI demonstration, and security documentation.
- Rust compiled and tested locally on Windows GNU; Python and Rust agree on 185 shared vectors. See `ITERATION_2026_10_11.md` for the recorded checks.

## Phase 2 — Cryptoanalysis (started)

Implemented: labelled round variants, shared fixtures, exact S-box DDT/Walsh/nonlinearity, descriptive block/key avalanche and SAC/BIC estimates, per-round diffusion, and a small repeated-byte key-schedule probe. Methodology and raw results are published. Full-network attack analysis remains open.

1. Freeze the specification and add independent vector generation/cross-checking before interpreting measurements.
2. Add S-box metrics: differential distribution table, maximum differential probability, linear approximation table, and component nonlinearity.
3. Measure block and key avalanche, SAC, and bit-independence over stated sample sizes and fixed seeds; publish scripts and raw result metadata.
4. Build reduced-round experiments and exhaustive small-width models for differential/linear trail search, round dependencies, and key-schedule collisions or equivalence.
5. Add reproducible Rust benchmarks and compare AES-256/ChaCha20 only with documented libraries, modes/interfaces, hardware, versions, and methodology. Do not infer security from speed or statistical appearance.
6. Seek external cryptanalysis and record negative results without tuning metrics as a substitute for a security argument.

## Phase 3 — Secure protocol prototype

1. Write a separate threat model and compare adopting an existing reviewed E2EE protocol with a narrowly scoped prototype.
2. Select maintained libraries for authenticated key establishment, HKDF, and AEAD. Review dependency health, supported platforms, and current API guidance.
3. Specify canonical serialization, identities and key binding, per-direction keys, nonce uniqueness, replay handling, error behavior, and key update boundaries.
4. Implement only a small two-party prototype with test vectors and interoperability tests. Keep NA&STY-X Research out of every secure path.
5. Treat Double Ratchet, multi-device, groups/MLS, and hybrid post-quantum exchange as later separately reviewed milestones.
