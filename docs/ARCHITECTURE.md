# Architecture

## Phase 1

`nastyx-core` is dependency-free Rust code for the experimental block permutation. `nastyx-cli` is a narrow hex-in/hex-out demonstration with a warning on each run. `research/reference_cipher/reference.py` is the executable reference used for research and vector generation. The Python scripts are not imported by the Rust library.

The cipher and future secure messaging work have separate namespaces, crates, specifications, and threat models. The experimental cipher is not a default or fallback for any secure protocol component.

## Proposed Secure separation

Future crates may include `nastyx-secure` for wrappers around reviewed primitives, and `nastyx-protocol` for message framing and session state. Candidate primitives include X25519, HKDF-SHA-256, and an established AEAD such as ChaCha20-Poly1305, selected from maintained RustCrypto ecosystem crates after reviewing current APIs and platform support. No dependency or protocol choice is implied by Phase 1. A ratchet and post-quantum hybrid are future design work, not implemented behavior.

Before a protocol prototype, specify identity binding, authenticated key establishment, key separation, nonce ownership, replay policy, serialization, session recovery, and failure handling. Prefer adopting an existing reviewed protocol implementation when practical instead of assembling a new protocol from primitive APIs.
