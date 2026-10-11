# NA&STY-X

**Current research revision:** 0.3.0-alpha
**Status:** experimental cryptography research

NA&STY-X is a research project exploring a reversible hybrid construction that combines a Feistel network, byte substitution and permutation, and ARX operations. This first iteration contains a block-cipher experiment and small reproducible research tools.

> **Security warning:** The cipher in `nastyx-core` is newly designed, unaudited, and unsuitable for protecting real data. The legacy primitive has no message mode or authentication. The v0.3 message construction adds an experimental mode, tag and nonce registry; neither version has independent security analysis or a side-channel guarantee. Do not use it for passwords, files, network traffic, or any other secrets. The current direction is an original cipher and protocol. An experimental message mode and tag exist; secure key establishment and session protection are not implemented; see [`docs/PROTOCOL_DESIGN.md`](docs/PROTOCOL_DESIGN.md).

## Current v0.3 implementation

- `nastyx-engine`: original 128-bit block / 256-bit key construction, default 24 rounds, improved own S-box and nonlinear key schedule.
- `nastyx-message`: arbitrary-length research message encryption, external context binding, a 128-bit integrity tag and persistent nonce reservation.
- 185 v0.3 block vectors and 10 message vectors checked by independent Rust and Python implementations.
- Full-width sample probes, exact component analysis, exhaustive 16-bit toy-model experiments and a local serial benchmark.

**This is experimental software, not approved for protecting real secrets.** The cipher, derived keys and tag lack independent cryptanalysis. Nonce registries require correct local storage and must not be deleted or rolled back. Replay protection, session key exchange, forward secrecy, guaranteed key erasure and constant-time implementation are absent.

Specifications: [cipher v0.3](docs/CRYPTO_SPEC_V0_3.md), [message format v0.3](docs/MESSAGE_SPEC_V0_3.md), [iteration report](docs/ITERATION_V0_3.md).

## Run

```powershell
cargo test --workspace --locked
cargo run -p nastyx-message --example research_roundtrip
py -3 -m unittest discover -s tests -v
py -3 research/generate_v3_vectors.py --check
py -3 research/full_width_v3.py
py -3 research/reduced_model_v3.py --output research/results/reduced-model-v3.json
```

The demonstration uses a public test key and fixed message, prints an explicit warning, and keeps nonce markers under `.tools/nastyx-message-demo`. Never use its key for real data. Production-shaped Rust entry points are `Sender::initialize` for a fresh key, `Sender::open` for an existing registry, `Sender::seal`, and `Receiver::open`; the construction itself is not production-approved.

On this Windows workspace the tested toolchain is `stable-x86_64-pc-windows-gnu`: select it with `cargo +stable-x86_64-pc-windows-gnu ...`. Linux/macOS normally use their stable host toolchain. CI is configured for Linux, Windows, macOS and Rust 1.74; configuration is not confirmation of successful remote runs.

## Research reproducibility

Python 3.10+ runs the references; published optimization experiments used Python 3.12.10. All research inputs and vector keys are public, deterministic test data. Their PRNGs must not generate secrets. Reports retain scopes, sample sizes, seeds and source hashes. Toy-model estimates do not bound the full cipher; sample correlations and diffusion are not security proofs.

```powershell
py -3 research/optimize_sbox.py --output research/results/sbox-optimized-v1.json
py -3 research/optimize_linear.py
cargo run --release -p nastyx-engine --example bench
```

See [benchmark scope](docs/BENCHMARKS.md) for raw measurements and limitations.

## Historical versions

`nastyx-core` and the original `nastyx-demo` CLI remain revision v0.2. Their reference, fixtures and specifications are preserved unchanged. v0.1 exists as historical specifications and results. Current v0.3 records never silently fall back to these versions. The workspace therefore intentionally contains legacy v0.2 packages and new v0.3 packages.

## Layout

```text
crates/nastyx-engine/       current v0.3 block research engine
crates/nastyx-message/      current v0.3 message research module
crates/nastyx-core/         historical v0.2 engine
crates/nastyx-cli/          historical single-block demonstration
research/reference_cipher/ independent Python references
tests/vectors/             public interoperability fixtures
research/results/          measurements and provenance
docs/                      exact specifications, risks and roadmap
```

Next: independent analysis of the construction, then the separately scoped session protocol described in [PROTOCOL_DESIGN.md](docs/PROTOCOL_DESIGN.md).
