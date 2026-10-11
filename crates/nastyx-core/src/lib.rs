//! Experimental NA&STY-X cipher for reproducible research only.
//!
//! **Do not use this crate to protect real data.** The construction and key
//! schedule have not received independent cryptanalysis. This module provides
//! a fixed 128-bit block and 256-bit master-key permutation for experiments.

use std::sync::OnceLock;

/// Cipher revision. Version 0.2 is incompatible with the historical v0.1 S-box.
pub const ALGORITHM_VERSION: &str = "0.2";

/// Block size, in bytes.
pub const BLOCK_SIZE: usize = 16;
/// Master-key size, in bytes.
pub const KEY_SIZE: usize = 32;
/// Number of Feistel rounds in the v0.2 reference construction.
pub const ROUNDS: usize = 16;
/// Largest round count supported by the research variants.
pub const MAX_ROUNDS: usize = 24;

/// Explicit experimental variants. No variant has an established security bound.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(usize)]
pub enum RoundCount {
    R8 = 8,
    R12 = 12,
    R16 = 16,
    R20 = 20,
    R24 = 24,
}

impl RoundCount {
    /// Returns the number of Feistel rounds.
    pub const fn count(self) -> usize {
        self as usize
    }
}

const BYTE_PERMUTATION: [usize; 8] = [2, 5, 0, 7, 4, 1, 6, 3];
const GOLDEN_RATIO: u64 = 0x9E37_79B9_7F4A_7C15;

/// A keyed experimental block permutation. Not suitable for production.
#[derive(Clone)]
pub struct Nastyx {
    round_keys: [u64; MAX_ROUNDS],
    rounds: RoundCount,
}

impl Nastyx {
    /// Creates a cipher instance from exactly 32 key bytes.
    ///
    /// This API is experimental and makes no security guarantee.
    pub fn new(key: &[u8; KEY_SIZE]) -> Self {
        Self::with_rounds(key, RoundCount::R16)
    }

    /// Constructs an explicit research variant; the default remains 16 rounds.
    pub fn with_rounds(key: &[u8; KEY_SIZE], rounds: RoundCount) -> Self {
        Self {
            round_keys: expand_key(key),
            rounds,
        }
    }

    /// Returns the configured research round count.
    pub fn rounds(&self) -> RoundCount {
        self.rounds
    }

    /// Encrypts one 16-byte block. This is a research primitive, not an AEAD.
    pub fn encrypt_block(&self, block: &[u8; BLOCK_SIZE]) -> [u8; BLOCK_SIZE] {
        let mut left = u64::from_be_bytes(block[..8].try_into().expect("fixed slice"));
        let mut right = u64::from_be_bytes(block[8..].try_into().expect("fixed slice"));
        for &round_key in &self.round_keys[..self.rounds.count()] {
            let next = left ^ round_function(right, round_key);
            left = right;
            right = next;
        }
        join_halves(left, right)
    }

    /// Decrypts one 16-byte block using the same Feistel round keys in reverse.
    pub fn decrypt_block(&self, block: &[u8; BLOCK_SIZE]) -> [u8; BLOCK_SIZE] {
        let mut left = u64::from_be_bytes(block[..8].try_into().expect("fixed slice"));
        let mut right = u64::from_be_bytes(block[8..].try_into().expect("fixed slice"));
        for &round_key in self.round_keys[..self.rounds.count()].iter().rev() {
            let previous_right = left;
            let previous_left = right ^ round_function(left, round_key);
            left = previous_left;
            right = previous_right;
        }
        join_halves(left, right)
    }
}

fn join_halves(left: u64, right: u64) -> [u8; BLOCK_SIZE] {
    let mut output = [0_u8; BLOCK_SIZE];
    output[..8].copy_from_slice(&left.to_be_bytes());
    output[8..].copy_from_slice(&right.to_be_bytes());
    output
}

fn expand_key(key: &[u8; KEY_SIZE]) -> [u64; MAX_ROUNDS] {
    let mut state = [0_u64; 4];
    for (i, word) in state.iter_mut().enumerate() {
        let start = i * 8;
        *word = u64::from_be_bytes(key[start..start + 8].try_into().expect("fixed slice"));
    }
    let mut round_keys = [0_u64; MAX_ROUNDS];
    for (i, output) in round_keys.iter_mut().enumerate() {
        let constant = GOLDEN_RATIO.wrapping_mul((i as u64) + 1);
        let [s0, s1, s2, s3] = state;
        let round_key =
            s0.wrapping_add(s1.rotate_left(13)).wrapping_add(constant) ^ s2.rotate_left(29) ^ s3;
        *output = round_key;
        state = [s1, s2, s3, round_key.wrapping_add(s0.rotate_left(7))];
    }
    round_keys
}

fn round_function(input: u64, round_key: u64) -> u64 {
    let mixed = (input ^ round_key).to_le_bytes();
    let sbox = nastyx_sbox();
    let mut permuted = [0_u8; 8];
    for (i, source_index) in BYTE_PERMUTATION.iter().enumerate() {
        permuted[i] = sbox[mixed[*source_index] as usize];
    }
    let x = u64::from_le_bytes(permuted);
    x.wrapping_add(x.rotate_left(17)) ^ x.rotate_left(41) ^ round_key
}

fn nastyx_sbox() -> &'static [u8; 256] {
    static SBOX: OnceLock<[u8; 256]> = OnceLock::new();
    SBOX.get_or_init(|| {
        let mut state = 0x4E41_5859_u32.wrapping_add(18_u32.wrapping_mul(0x9E37_79B9));
        let mut rounds = [[0_u8; 16]; 12];
        for table in &mut rounds {
            for (index, value) in table.iter_mut().enumerate() {
                *value = index as u8;
            }
            for j in (1..16).rev() {
                state = state.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
                let index = ((state >> 16) as usize) % (j + 1);
                table.swap(j, index);
            }
        }
        let mut result = [0_u8; 256];
        for (input, output) in result.iter_mut().enumerate() {
            let (mut left, mut right) = ((input >> 4) as u8, (input & 15) as u8);
            for table in &rounds {
                (left, right) = (right, left ^ table[right as usize]);
            }
            *output = (left << 4) | right;
        }
        result
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn decode_hex<const N: usize>(text: &str) -> [u8; N] {
        let mut out = [0; N];
        for (i, byte) in out.iter_mut().enumerate() {
            *byte = u8::from_str_radix(&text[i * 2..i * 2 + 2], 16).unwrap();
        }
        out
    }

    #[test]
    fn nastyx_sbox_reference_points() {
        assert_eq!(nastyx_sbox()[0x00], 0xbe);
        assert_eq!(nastyx_sbox()[0x53], 0x15);
        assert_eq!(nastyx_sbox()[0xff], 0xbb);
    }

    #[test]
    fn custom_sbox_matches_entire_python_table() {
        let expected =
            decode_hex::<256>(include_str!("../../../tests/vectors/sbox-v0.2.hex").trim());
        assert_eq!(*nastyx_sbox(), expected);
        let mut seen = [false; 256];
        for value in nastyx_sbox() {
            assert!(!seen[*value as usize]);
            seen[*value as usize] = true;
        }
    }

    #[test]
    fn encrypts_reference_vector() {
        let key = decode_hex::<KEY_SIZE>(
            "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
        );
        let block = decode_hex::<BLOCK_SIZE>("00112233445566778899aabbccddeeff");
        let expected = decode_hex::<BLOCK_SIZE>("e1e45eb0d6d559f54f1c932d8ec53879");
        let cipher = Nastyx::new(&key);
        assert_eq!(cipher.encrypt_block(&block), expected);
        assert_eq!(cipher.decrypt_block(&expected), block);
    }

    #[test]
    fn round_trips_deterministic_sample_blocks() {
        let key = [0x5a; KEY_SIZE];
        let cipher = Nastyx::new(&key);
        for seed in 0_u8..=255 {
            let block = [seed; BLOCK_SIZE];
            assert_eq!(cipher.decrypt_block(&cipher.encrypt_block(&block)), block);
        }
    }
}
