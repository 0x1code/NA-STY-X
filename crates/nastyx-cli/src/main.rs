use nastyx_core::{Nastyx, BLOCK_SIZE, KEY_SIZE};
use std::env;

const WARNING: &str = "WARNING: experimental research cipher; do not use to protect real data.";

fn parse_hex<const N: usize>(text: &str, label: &str) -> Result<[u8; N], String> {
    if text.len() != N * 2 || !text.is_ascii() {
        return Err(format!(
            "{label} must be exactly {} hexadecimal characters",
            N * 2
        ));
    }
    let mut output = [0_u8; N];
    for (i, byte) in output.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&text[i * 2..i * 2 + 2], 16)
            .map_err(|_| format!("{label} contains invalid hexadecimal"))?;
    }
    Ok(output)
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 2 {
        return Err(format!(
            "{WARNING}\nUsage: nastyx-demo <64-hex-char-key> <32-hex-char-block>"
        ));
    }
    let key = parse_hex::<KEY_SIZE>(&args[0], "key")?;
    let block = parse_hex::<BLOCK_SIZE>(&args[1], "block")?;
    let cipher = Nastyx::new(&key);
    let encrypted = cipher.encrypt_block(&block);
    let decrypted = cipher.decrypt_block(&encrypted);
    println!("{WARNING}");
    println!("ciphertext: {}", hex(&encrypted));
    println!("decrypted:  {}", hex(&decrypted));
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(2);
    }
}
