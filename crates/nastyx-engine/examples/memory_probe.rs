//! Public-input code-generation probe. Clearing this object's storage does not
//! clear caller-owned keys, registers, earlier moves, swap, crash dumps or DMA.
use nastyx_engine::Nastyx;
use std::hint::black_box;

#[inline(never)]
fn destroy(cipher: &mut Option<Nastyx>) {
    // Drop in the occupied slot, without first moving the key into a by-value
    // parameter. A by-value probe may only show erasure of the moved-to copy.
    *cipher = None;
}

fn main() {
    let mut cipher = Some(Nastyx::new(&black_box([0x5a; 32])));
    black_box(
        cipher
            .as_ref()
            .unwrap()
            .encrypt_block(&black_box([0x33; 16])),
    );
    destroy(black_box(&mut cipher));
    assert!(cipher.is_none());
    black_box(&cipher);
}
