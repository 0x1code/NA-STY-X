use nastyx_core::{Nastyx, RoundCount};

fn hex<const N: usize>(text: &str) -> [u8; N] {
    assert_eq!(text.len(), N * 2);
    let mut output = [0; N];
    for (i, byte) in output.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&text[i * 2..i * 2 + 2], 16).unwrap();
    }
    output
}

#[test]
fn all_shared_python_vectors_match_rust() {
    let fixtures = include_str!("../../../tests/vectors/research-rounds.tsv");
    let mut checked = 0;
    for line in fixtures.lines().filter(|line| !line.starts_with('#')) {
        let fields: Vec<_> = line.split('\t').collect();
        assert_eq!(fields.len(), 4);
        let rounds = match fields[0] {
            "8" => RoundCount::R8,
            "12" => RoundCount::R12,
            "16" => RoundCount::R16,
            "20" => RoundCount::R20,
            "24" => RoundCount::R24,
            _ => panic!("invalid fixture round count"),
        };
        let key = hex::<32>(fields[1]);
        let block = hex::<16>(fields[2]);
        let expected = hex::<16>(fields[3]);
        let cipher = Nastyx::with_rounds(&key, rounds);
        assert_eq!(cipher.rounds(), rounds);
        assert_eq!(cipher.encrypt_block(&block), expected, "vector {}", checked);
        assert_eq!(cipher.decrypt_block(&expected), block, "vector {}", checked);
        checked += 1;
    }
    assert_eq!(checked, 185);
}
