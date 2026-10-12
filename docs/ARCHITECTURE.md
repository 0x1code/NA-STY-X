# Architecture

## Phase 1

`nastyx-core` is dependency-free Rust code for the experimental block permutation. `nastyx-cli` is a narrow hex-in/hex-out demonstration with a warning on each run. `research/reference_cipher/reference.py` is the executable reference used for research and vector generation. The Python scripts are not imported by the Rust library.

The block primitive and future messaging layer have separate specifications and threat models. No approved secure messaging component is implemented. Protocol decisions must be made explicitly and receive analysis; a working block primitive alone does not provide a secure channel.

## Phase 2 laboratory

`Nastyx::with_rounds` selects one of five explicit research variants through `RoundCount`; `Nastyx::new` retains the 16-round default. The Python reference uses an explicit `rounds` argument. This is a raw block API; bindings and safe application-level encryption are not implemented.

`research/generate_vectors.py` produces public JSON and TSV fixtures. Rust integration tests consume TSV and check encryption and decryption independently. `research/lab.py` uses only the Python standard library to compute exact S-box tables and descriptive experiments. It records sample size, seed, bit order, runtime, platform, Python version and the normalized source hash. Raw measurements live in `research/results/`. A fixed seed makes public experiments repeatable; it must never be used for generating application secrets.

## Current protocol direction

The direction was revised on 2026-10-11 to develop an original cipher and protocol without integrating ready-made encryption algorithms. `nastyx-core` v0.2 uses its own public S-box generator. No new cryptographic dependencies were added. Earlier proposals to wrap established AEAD and key-exchange libraries are not the current implementation plan.

`PROTOCOL_DESIGN.md` and `SESSION_SPEC_V1.md` describe paired-device volatile sessions.
Public-key establishment and independent security evaluation remain absent. Historical
results are kept separate; a working prototype does not establish production security.

## Current v0.3 implementation

`nastyx-engine` implements the new cipher revision; `nastyx-message` builds on it. The active engine/message/session crates also use pinned `zeroize` solely for memory clearing. `nastyx-core` remains the historical v0.2 implementation. Their vectors and algorithms are kept separate. Python independently implements v0.3 block and message transformations.

The message API implements research encryption/integrity and a local nonce registry, not a complete session protocol. See `MESSAGE_SPEC_V0_3.md` for exact framing, key derivation, state assumptions and missing properties. Earlier statements about absent authentication refer to the historical primitive; the new tag is implemented but unreviewed.

## NXS1 / 0.4.0-alpha

`nastyx-session` builds on `nastyx-message`: one-time pairing, ID/transcript binding,
peer-code verification, directional chains, consumed message keys and bounded skipped keys.
No serialization/key export: fresh pairing after restart. OneTimeSealer uses fixed-nonce
NXM3 only for fresh message keys; long-term keys require Sender's persistent nonce registry.

Independent `session_v1.py` matches Rust fixtures. `demos/e2ee_chat.py` launches two clients
and an HTTP relay; trusted local pipes provision pairing and drive endpoints, while only
canonical packets traverse HTTP. This demonstrates separation, not malware isolation,
production key agreement or a deployed messenger.
