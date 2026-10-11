//! Demonstration with a PUBLIC TEST KEY. Never use this key for real data.
use nastyx_message::{Error, Receiver, Sender};
fn main() -> Result<(), Error> {
    println!("WARNING: experimental construction and public test key; research only.");
    let public_test_key = [0x5a; 32];
    let root = ".tools/nastyx-message-demo";
    let mut sender = match Sender::initialize(&public_test_key, root) {
        Ok(sender) => sender,
        Err(Error::Storage(error)) if error.kind() == std::io::ErrorKind::AlreadyExists => {
            Sender::open(&public_test_key, root)?
        }
        Err(error) => return Err(error),
    };
    let plaintext = b"NA&STY-X research message";
    let record = sender.seal(plaintext, b"demo/v3")?;
    let recovered = Receiver::new(&public_test_key).open(&record, b"demo/v3")?;
    assert_eq!(recovered, plaintext);
    println!("roundtrip=ok record_bytes={}", record.len());
    Ok(())
}
