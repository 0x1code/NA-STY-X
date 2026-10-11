# Architecture

## Phase 1

`nastyx-core` is dependency-free Rust code for the experimental block permutation. `nastyx-cli` is a narrow hex-in/hex-out demonstration with a warning on each run. `research/reference_cipher/reference.py` is the executable reference used for research and vector generation. The Python scripts are not imported by the Rust library.

The block primitive and future messaging layer have separate specifications and threat models. No secure messaging component is implemented. Protocol decisions must be made explicitly and receive analysis; a working block primitive alone does not provide a secure channel.

## Phase 2 laboratory

`Nastyx::with_rounds` selects one of five explicit research variants through `RoundCount`; `Nastyx::new` retains the 16-round default. The Python reference uses an explicit `rounds` argument. This is a raw block API; bindings and safe application-level encryption are not implemented.

`research/generate_vectors.py` produces public JSON and TSV fixtures. Rust integration tests consume TSV and check encryption and decryption independently. `research/lab.py` uses only the Python standard library to compute exact S-box tables and descriptive experiments. It records sample size, seed, bit order, runtime, platform, Python version and the normalized source hash. Raw measurements live in `research/results/`. A fixed seed makes public experiments repeatable; it must never be used for generating application secrets.

## Current protocol direction

The direction was revised on 2026-10-11 to develop an original cipher and protocol without integrating ready-made encryption algorithms. `nastyx-core` v0.2 uses its own public S-box generator. No new cryptographic dependencies were added. Earlier proposals to wrap established AEAD and key-exchange libraries are not the current implementation plan.

The protocol design is documented in `PROTOCOL_DESIGN.md`. It is a draft with explicit gaps, including authentication, message mode and key establishment. It must not be presented as a secure messaging implementation. Historical v0.1 results are kept separately from active v0.2 vectors and measurements.
