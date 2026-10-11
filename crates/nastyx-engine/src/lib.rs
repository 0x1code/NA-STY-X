//! Experimental NA&STY-X cipher for reproducible research only.
//!
//! **Do not use this crate to protect real data.** The construction and key
//! schedule have not received independent cryptanalysis. This module provides
//! a fixed 128-bit block and 256-bit master-key permutation for experiments.

mod substitution;
use substitution::SBOX;

/// Cipher revision. Version 0.2 is incompatible with the historical previous cipher revisions.
pub const ALGORITHM_VERSION: &str = "0.3";

/// Block size, in bytes.
pub const BLOCK_SIZE: usize = 16;
/// Master-key size, in bytes.
pub const KEY_SIZE: usize = 32;
/// Number of Feistel rounds in the v0.3 reference construction.
pub const ROUNDS: usize = 24;
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
        Self::with_rounds(key, RoundCount::R24)
    }

    /// Constructs an explicit research variant; the default is 24 rounds.
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
        let round_key = round_function(
            round_function(s0 ^ s1.rotate_left(13), s2 ^ constant) ^ s3,
            constant,
        );
        *output = round_key;
        state = [
            s1 ^ s0.rotate_left(7),
            s2.wrapping_add(round_key.rotate_left(11)),
            s3 ^ s1.rotate_left(29),
            round_key.wrapping_add(s0),
        ];
    }
    round_keys
}

fn round_function(input: u64, round_key: u64) -> u64 {
    let mixed = (input ^ round_key).to_le_bytes();
    let sbox = &SBOX;
    let mut permuted = [0_u8; 8];
    for (i, source_index) in BYTE_PERMUTATION.iter().enumerate() {
        permuted[i] = sbox[mixed[*source_index] as usize];
    }
    let x = u64::from_le_bytes(permuted);
    let y = x.wrapping_add(x.rotate_left(17)) ^ x.rotate_left(41);
    let y = y.wrapping_add(y.rotate_left(31)) ^ y.rotate_left(23);
    y.wrapping_add(y.rotate_left(11)) ^ y.rotate_left(37) ^ round_key
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn every_master_key_bit_affects_schedule() {
        let key = [0_u8; 32];
        let baseline = expand_key(&key);
        for bit in 0..256 {
            let mut changed = key;
            changed[bit / 8] ^= 1 << (bit % 8);
            assert_ne!(baseline, expand_key(&changed));
        }
    }
    #[test]
    fn substitution_is_bijective() {
        let mut seen = [false; 256];
        for value in SBOX {
            assert!(!seen[value as usize]);
            seen[value as usize] = true;
        }
        let fixture = include_str!("../../../tests/vectors/sbox-v0.3.hex").trim();
        for (i, value) in SBOX.iter().enumerate() {
            assert_eq!(
                *value,
                u8::from_str_radix(&fixture[i * 2..i * 2 + 2], 16).unwrap()
            );
        }
    }
}
