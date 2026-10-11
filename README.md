# NA&STY-X

**Version:** 0.1.0-alpha  
**Status:** experimental cryptography research

NA&STY-X is a research project exploring a reversible hybrid construction that combines a Feistel network, byte substitution and permutation, and ARX operations. This first iteration contains a block-cipher experiment and small reproducible research tools.

> **Security warning:** The cipher in `nastyx-core` is newly designed, unaudited, and unsuitable for protecting real data. It has no secure mode of operation, authentication, nonce handling, side-channel review, or security proof. Do not use it for passwords, files, network traffic, or any other secrets. The future `nastyx-secure` work will use established cryptographic libraries and remain separate from this cipher.

## Phase 1 contents

- Rust workspace with `nastyx-core` and the warning-labeled `nastyx-demo` CLI.
- Python reference implementation and deterministic avalanche probe.
- A 128-bit block / 256-bit key, 16-round Feistel construction described in [`docs/CRYPTO_SPEC_V0_1.md`](docs/CRYPTO_SPEC_V0_1.md).
- A cross-language test vector in [`tests/vectors/v0.1.json`](tests/vectors/v0.1.json).
- Threat model, architecture, security notes, and roadmap under `docs/`.

## Phase 2 laboratory

- Explicit research variants with 8, 12, 16, 20 and 24 rounds; the original default and vector are unchanged.
- 185 shared vectors checked independently by Rust and Python.
- Exact S-box differential and Walsh tables, component nonlinearity, block/key avalanche, SAC counts, conditional bit-pair correlations, and round dependency measurements.
- Public raw results and methodology in [`docs/CRYPTOANALYSIS.md`](docs/CRYPTOANALYSIS.md). These measurements are not security proofs.

## Run the Python checks

Python 3.10 or newer is required. The test suite uses only the standard library:

```powershell
py -3 -m unittest discover -s tests -v
py -3 research/avalanche.py --samples 4 --seed 20261011
py -3 research/generate_vectors.py --check
py -3 research/lab.py --samples 32 --seed 20261011 --output research/results/phase2-smoke.json
```

## Run the Rust checks and demo

Install a stable Rust toolchain with Cargo, then run:

```powershell
cargo test --workspace --locked
cargo run -p nastyx-cli -- 000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f 00112233445566778899aabbccddeeff
```

The demo accepts only a 32-byte key and one 16-byte block, both as hex. It prints a warning every time. This is a primitive demonstration, not a file-encryption utility.

On Windows, install the build prerequisites for your Rust target. This iteration was checked with `stable-x86_64-pc-windows-gnu`; select it explicitly with `cargo +stable-x86_64-pc-windows-gnu test --workspace --locked` when multiple toolchains are installed. CI is configured for Linux, Windows, macOS and Rust 1.74; local checks do not establish their remote status.

## Reproducibility

The vector test fixes the key, input block, round count, and expected output. The avalanche script uses Python's deterministic `random.Random` seeded from the command line. Its output is descriptive only; sample size, runtime, hardware, Python version, and seed should accompany any reported results. No performance comparison is claimed in this phase.

## Layout

```text
crates/nastyx-core/       Rust experimental primitive
crates/nastyx-cli/        warning-labeled single-block demo
research/reference_cipher/ Python reference
research/avalanche.py     small diffusion probe
research/lab.py           S-box and diffusion research
research/generate_vectors.py shared fixture generator
research/results/         public measurements and metadata
tests/                    Python checks and shared vectors
docs/                     specification, risks, architecture, roadmap
```

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the proposed Cryptoanalysis and Secure Protocol phases.
