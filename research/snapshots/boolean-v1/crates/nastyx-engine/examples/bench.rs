//! Small serial research benchmark; no security or comparative claim.
use nastyx_engine::Nastyx;
use std::hint::black_box;
use std::time::Instant;
fn main() {
    let key = [0x5a; 32]; // Public benchmark input, never an application key.
    let cipher = Nastyx::new(&key);
    println!("cipher_state_bytes={}", std::mem::size_of::<Nastyx>());
    for repetition in 0..3 {
        let started = Instant::now();
        for _ in 0..1000 {
            black_box(Nastyx::new(black_box(&key)));
        }
        let setup = started.elapsed().as_secs_f64();
        let mut block = [0; 16];
        let started = Instant::now();
        for _ in 0..100000 {
            block = cipher.encrypt_block(black_box(&block));
        }
        black_box(block);
        let encryption = started.elapsed().as_secs_f64();
        let started = Instant::now();
        for _ in 0..100000 {
            block = cipher.decrypt_block(black_box(&block));
        }
        black_box(block);
        let decryption = started.elapsed().as_secs_f64();
        println!("repetition={repetition} setups=1000 setup_seconds={setup:.6} blocks=100000 encrypt_seconds={encryption:.6} decrypt_seconds={decryption:.6}");
    }
}
