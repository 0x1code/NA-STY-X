use nastyx_session::Pairing;

fn hex(text: &str) -> Vec<u8> {
    text.as_bytes()
        .chunks(2)
        .map(|chunk| u8::from_str_radix(std::str::from_utf8(chunk).unwrap(), 16).unwrap())
        .collect()
}
#[test]
fn independent_python_handshake_and_bidirectional_message_vectors() {
    let lines: Vec<_> = include_str!("../../../tests/vectors/session-v1.hex")
        .lines()
        .filter(|line| !line.starts_with('#'))
        .map(hex)
        .collect();
    let secret = lines[0].as_slice().try_into().unwrap();
    let a = lines[1].as_slice().try_into().unwrap();
    let b = lines[2].as_slice().try_into().unwrap();
    let (sa, offer) = Pairing::new(secret, a, b).unwrap().initiate(
        lines[3].as_slice().try_into().unwrap(),
        lines[4].as_slice().try_into().unwrap(),
    );
    assert_eq!(offer, lines[6]);
    let (sb, reply) = Pairing::new(secret, a, b)
        .unwrap()
        .respond(&offer, lines[5].as_slice().try_into().unwrap())
        .unwrap();
    assert_eq!(reply, lines[7]);
    let (sa, confirm) = sa.complete(&reply).unwrap();
    assert_eq!(confirm, lines[8]);
    let sb = sb.complete(&confirm).unwrap();
    assert_eq!(sa.verification_code().as_slice(), lines[9]);
    assert_eq!(sb.verification_code().as_slice(), lines[9]);
    let code = sa.verification_code();
    let mut sa = sa.verify_peer(&code).unwrap();
    let mut sb = sb.verify_peer(&code).unwrap();
    for (index, direction) in [0, 0, 1, 0].iter().enumerate() {
        let (sender, receiver) = if *direction == 0 {
            (&mut sa, &mut sb)
        } else {
            (&mut sb, &mut sa)
        };
        let plaintext = &lines[10 + index * 2];
        let packet = sender.seal(plaintext).unwrap();
        assert_eq!(packet, lines[11 + index * 2]);
        assert_eq!(receiver.open(&packet).unwrap(), *plaintext);
    }
}
