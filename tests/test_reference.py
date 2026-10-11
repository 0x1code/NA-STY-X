import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research" / "reference_cipher"))
from reference import AES_SBOX, decrypt_block, encrypt_block  # noqa: E402


class ReferenceCipherTests(unittest.TestCase):
    def test_aes_sbox_reference_points(self):
        self.assertEqual(AES_SBOX[0x00], 0x63)
        self.assertEqual(AES_SBOX[0x53], 0xED)
        self.assertEqual(AES_SBOX[0xFF], 0x16)

    def test_round_trip_deterministic_blocks(self):
        key = bytes([0x5A] * 32)
        for seed in range(256):
            block = bytes([seed] * 16)
            self.assertEqual(decrypt_block(key, encrypt_block(key, block)), block)

    def test_reference_vector(self):
        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
        block = bytes.fromhex("00112233445566778899aabbccddeeff")
        self.assertEqual(
            encrypt_block(key, block).hex(),
            "f7d36b9993d7af9ae115d2c7458b6118",
        )

    def test_rejects_wrong_lengths(self):
        with self.assertRaises(ValueError):
            encrypt_block(bytes(31), bytes(16))
        with self.assertRaises(ValueError):
            encrypt_block(bytes(32), bytes(15))


if __name__ == "__main__":
    unittest.main()
