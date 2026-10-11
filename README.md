# NA&STY-X

**Current research revision:** 0.4.0-alpha (NXS1 sessions; v0.3 cipher/messages)
**Status:** experimental cryptography research

NA&STY-X is a research project exploring a reversible hybrid construction that combines a Feistel network, byte substitution and permutation, and ARX operations. This first iteration contains a block-cipher experiment and small reproducible research tools.

> **Security warning:** All cryptographic constructions are original, experimental and unaudited. Do not protect real secrets with this revision. NXS1 implements paired-device sessions with an out-of-band one-time secret, confirmation, separate message-key chains and replay rejection. It does not provide public-key agreement, automatic post-compromise recovery, guaranteed erasure or proven cryptographic security. See [session specification](docs/SESSION_SPEC_V1.md).

## First working E2EE prototype — NXS1

```powershell
py -3 demos/e2ee_chat.py --interactive
```

Three separate processes: Alice, Bob and a relay holding only packets. OS-random pairing
data travels through trusted local pipes, simulating a separate pairing channel. The local
controller is trusted and displays both endpoints; it is not the relay. Clients use the
independent Python reference; Rust `nastyx-session` matches all session fixtures byte for byte.

Commands: `alice your text`, `bob your text`, `replay`, `tamper`, `reorder`, `renew`, `restart`, `status`, `quit`.
The opening scenario checks messages in both directions, tampering, replay, out-of-order
delivery and fresh pairing. `renew` uses a new secret outside the old session. State is
volatile: restarting requires fresh pairing. Each additional device pair needs independent
pairing data and a separate session; no automatic device directory is implemented.

Rust API: `Pairing::initiate/respond`, pending `complete`,
`UnverifiedSession::verification_code/verify_peer`, `Session::seal/open/close`.
Peer codes must be compared over a trusted separate channel. Initial PSK/root leave logical
active state; one-wayness and physical erasure remain unproven.

Use for research/integration experiments with non-secret data.
[Specification](docs/SESSION_SPEC_V1.md), [demonstration](docs/E2EE_DEMO.md),
[independent review package](docs/REVIEW_REQUEST.md).

## Current v0.3 implementation

- `nastyx-engine`: original 128-bit block / 256-bit key construction, default 24 rounds, improved own S-box and nonlinear key schedule.
- `nastyx-message`: arbitrary-length research message encryption, external context binding, a 128-bit integrity tag and persistent nonce reservation.
- 185 v0.3 block vectors and 10 message vectors checked by independent Rust and Python implementations.
- Full-width sample probes, exact component analysis, exhaustive 16-bit toy-model experiments and a local serial benchmark.

**This is experimental software, not approved for protecting real secrets.** The cipher, derived keys and tag lack independent cryptanalysis. The standalone v0.3 receiver is stateless; NXS1 adds replay protection above it. Standalone Sender nonce registries must not be deleted or rolled back. NXS1 consumes fresh message keys and never restores live chains from disk.

Specifications: [cipher v0.3](docs/CRYPTO_SPEC_V0_3.md), [message format v0.3](docs/MESSAGE_SPEC_V0_3.md), [iteration report](docs/ITERATION_V0_3.md).

Current Rust substitution uses Boolean ANF of the same original S-box, removing
secret-indexed S-box loads from this source path. Outputs and wire formats are unchanged;
this implementation is slower and is not a constant-time certification. Exact round-key
symmetry, bounded master-key search and MAC/KDF probes are published in
[construction analysis](docs/CONSTRUCTION_ANALYSIS.md).

## Run

```powershell
cargo test --workspace --locked
cargo run -p nastyx-message --example research_roundtrip
py -3 -m unittest discover -s tests -v
py -3 research/generate_v3_vectors.py --check
py -3 research/generate_session_vectors.py --check
py -3 research/generate_sbox_circuit.py --check
py -3 research/construction_analysis.py
py -3 demos/e2ee_chat.py
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
crates/nastyx-session/      NXS1 paired-device session prototype
demos/e2ee_chat.py          local three-process interactive chat
crates/nastyx-core/         historical v0.2 engine
crates/nastyx-cli/          historical single-block demonstration
research/reference_cipher/ independent Python references
tests/vectors/             public interoperability fixtures
research/results/          measurements and provenance
docs/                      exact specifications, risks and roadmap
```

Next: independent cryptanalysis and implementation hardening. Key establishment without
an external trusted pairing channel remains separate research. See [review package](docs/REVIEW_REQUEST.md).
