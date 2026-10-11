//! Experimental NA&STY-X cipher for reproducible research only.
//!
//! **Do not use this crate to protect real data.** The construction and key
//! schedule have not received independent cryptanalysis. This module provides
//! a fixed 128-bit block and 256-bit master-key permutation for experiments.

use std::sync::OnceLock;

/// Block size, in bytes.
pub const BLOCK_SIZE: usize = 16;
/// Master-key size, in bytes.
pub const KEY_SIZE: usize = 32;
/// Number of Feistel rounds in the v0.1 reference construction.
pub const ROUNDS: usize = 16;

const BYTE_PERMUTATION: [usize; 8] = [2, 5, 0, 7, 4, 1, 6, 3];
const GOLDEN_RATIO: u64 = 0x9E37_79B9_7F4A_7C15;

/// A keyed experimental block permutation. Not suitable for production.
#[derive(Clone)]
pub struct Nastyx {
    round_keys: [u64; ROUNDS],
}

impl Nastyx {
    /// Creates a cipher instance from exactly 32 key bytes.
    ///
    /// This API is experimental and makes no security guarantee.
    pub fn new(key: &[u8; KEY_SIZE]) -> Self {
        Self { round_keys: expand_key(key) }
    }

    /// Encrypts one 16-byte block. This is a research primitive, not an AEAD.
    pub fn encrypt_block(&self, block: &[u8; BLOCK_SIZE]) -> [u8; BLOCK_SIZE] {
        let mut left = u64::from_be_bytes(block[..8].try_into().expect("fixed slice"));
        let mut right = u64::from_be_bytes(block[8..].try_into().expect("fixed slice"));
        for &round_key in &self.round_keys {
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
        for &round_key in self.round_keys.iter().rev() {
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

fn expand_key(key: &[u8; KEY_SIZE]) -> [u64; ROUNDS] {
    let mut state = [0_u64; 4];
    for (i, word) in state.iter_mut().enumerate() {
        let start = i * 8;
        *word = u64::from_be_bytes(key[start..start + 8].try_into().expect("fixed slice"));
    }
    let mut round_keys = [0_u64; ROUNDS];
    for (i, output) in round_keys.iter_mut().enumerate() {
        let constant = GOLDEN_RATIO.wrapping_mul((i as u64) + 1);
        let [s0, s1, s2, s3] = state;
        let round_key = s0
            .wrapping_add(s1.rotate_left(13))
            .wrapping_add(constant)
            ^ s2.rotate_left(29)
            ^ s3;
        *output = round_key;
        state = [s1, s2, s3, round_key.wrapping_add(s0.rotate_left(7))];
    }
    round_keys
}

fn round_function(input: u64, round_key: u64) -> u64 {
    let mixed = (input ^ round_key).to_le_bytes();
    let sbox = aes_sbox();
    let mut permuted = [0_u8; 8];
    for (i, source_index) in BYTE_PERMUTATION.iter().enumerate() {
        permuted[i] = sbox[mixed[*source_index] as usize];
    }
    let x = u64::from_le_bytes(permuted);
    x.wrapping_add(x.rotate_left(17)) ^ x.rotate_left(41) ^ round_key
}

fn aes_sbox() -> &'static [u8; 256] {
    static SBOX: OnceLock<[u8; 256]> = OnceLock::new();
    SBOX.get_or_init(|| {
        let mut table = [0_u8; 256];
        for (i, value) in table.iter_mut().enumerate() {
            let x = i as u8;
            let inverse = if x == 0 { 0 } else { gf_pow(x, 254) };
            *value = inverse
                ^ inverse.rotate_left(1)
                ^ inverse.rotate_left(2)
                ^ inverse.rotate_left(3)
                ^ inverse.rotate_left(4)
                ^ 0x63;
        }
        table
    })
}

fn gf_pow(mut base: u8, mut exponent: u16) -> u8 {
    let mut result = 1_u8;
    while exponent > 0 {
        if exponent & 1 != 0 {
            result = gf_mul(result, base);
        }
        base = gf_mul(base, base);
        exponent >>= 1;
    }
    result
}

fn gf_mul(mut a: u8, mut b: u8) -> u8 {
    let mut result = 0_u8;
    for _ in 0..8 {
        if b & 1 != 0 {
            result ^= a;
        }
        let high = a & 0x80;
        a <<= 1;
        if high != 0 {
            a ^= 0x1b;
        }
        b >>= 1;
    }
    result
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
    fn aes_sbox_reference_points() {
        assert_eq!(aes_sbox()[0x00], 0x63);
        assert_eq!(aes_sbox()[0x53], 0xed);
        assert_eq!(aes_sbox()[0xff], 0x16);
    }

    #[test]
    fn encrypts_reference_vector() {
        let key = decode_hex::<KEY_SIZE>("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f");
        let block = decode_hex::<BLOCK_SIZE>("00112233445566778899aabbccddeeff");
        let expected = decode_hex::<BLOCK_SIZE>("f7d36b9993d7af9ae115d2c7458b6118");
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
