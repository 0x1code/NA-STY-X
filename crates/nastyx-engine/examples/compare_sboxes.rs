//! Same-process public-input comparison with the preserved v1 Boolean evaluator.
//! Microbenchmark only: black_box is not a cryptographic security barrier.
#[path = "../src/boolean_substitution.rs"]
mod current;
#[path = "../../../research/snapshots/boolean-v1/crates/nastyx-engine/src/boolean_substitution.rs"]
mod previous;
use std::hint::black_box;
use std::time::Instant;

fn measure(function: fn(u64) -> u64) -> f64 {
    let mut value = black_box(0x123456789abcdef0_u64);
    let start = Instant::now();
    for _ in 0..1_000_000 {
        value = black_box(function(black_box(value)));
    }
    black_box(value);
    start.elapsed().as_secs_f64()
}

fn main() {
    for repetition in 0..6 {
        // Alternate order to reduce systematic warmup/order bias.
        let (previous_seconds, current_seconds) = if repetition % 2 == 0 {
            (
                measure(previous::substitute_word),
                measure(current::substitute_word),
            )
        } else {
            let current = measure(current::substitute_word);
            (measure(previous::substitute_word), current)
        };
        println!("repetition={repetition} calls=1000000 previous_seconds={previous_seconds:.6} current_seconds={current_seconds:.6}");
    }
}
