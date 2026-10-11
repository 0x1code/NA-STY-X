//! Experimental original NA&STY-X message construction. NOT production crypto.
//! Tags and subkeys depend on unreviewed v0.3 cipher/PRF assumptions.
//! No key exchange, replay protection, side-channel guarantee or rollback defense.
use nastyx_engine::Nastyx;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

/// Maximum plaintext size accepted by this research interface.
pub const MAX_MESSAGE: usize = 1_048_576;
/// Maximum size of external authenticated context.
pub const MAX_CONTEXT: usize = 65_536;
const HEADER: usize = 28;
const TAG: usize = 16;
const MAX_RECORDS: u64 = 1_048_576;

/// Public errors never contain keys or plaintext.
#[derive(Debug)]
pub enum Error {
    /// Malformed, modified, wrong-key or wrong-context record.
    Rejected,
    /// Application size exceeds the research limits.
    TooLarge,
    /// Persistent nonce storage failed; no ciphertext is returned.
    Storage(io::Error),
    /// This key's persistent counter has reached its operational limit.
    Exhausted,
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Rejected => f.write_str("record rejected"),
            Self::TooLarge => f.write_str("size limit exceeded"),
            Self::Storage(_) => f.write_str("nonce storage failed"),
            Self::Exhausted => f.write_str("key record limit reached"),
        }
    }
}
impl std::error::Error for Error {}

fn domain(kind: u8, role: u8, part: u8) -> [u8; 16] {
    let mut block = [0; 16];
    block[..6].copy_from_slice(&[b'N', b'X', kind, 3, role, part]);
    block
}

struct Keys {
    encryption: Nastyx,
    authentication: Nastyx,
    finalization: Nastyx,
    identity: [u8; 16],
}
impl Keys {
    fn new(master: &[u8; 32]) -> Self {
        let root = Nastyx::new(master);
        let derive = |role| {
            let mut key = [0; 32];
            key[..16].copy_from_slice(&root.encrypt_block(&domain(b'K', role, 0)));
            key[16..].copy_from_slice(&root.encrypt_block(&domain(b'K', role, 1)));
            Nastyx::new(&key)
        };
        Self {
            encryption: derive(1),
            authentication: derive(2),
            finalization: derive(3),
            identity: root.encrypt_block(&domain(b'I', 0, 0)),
        }
    }
}

fn xor(a: [u8; 16], b: &[u8; 16]) -> [u8; 16] {
    std::array::from_fn(|i| a[i] ^ b[i])
}

fn crypt(keys: &Keys, nonce: &[u8], input: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(input.len());
    for (index, chunk) in input.chunks(16).enumerate() {
        let mut counter = [0; 16];
        counter[..12].copy_from_slice(nonce);
        counter[12..].copy_from_slice(&(index as u32).to_be_bytes());
        let stream = keys.encryption.encrypt_block(&counter);
        out.extend(chunk.iter().zip(stream).map(|(a, b)| a ^ b));
    }
    out
}

fn tag(keys: &Keys, header: &[u8], context: &[u8], ciphertext: &[u8]) -> [u8; 16] {
    let mut state = keys.authentication.encrypt_block(&domain(b'M', 0, 0));
    let mut block = [0; 16];
    let mut used = 0;
    for &value in header.iter().chain(context).chain(ciphertext) {
        block[used] = value;
        used += 1;
        if used == 16 {
            state = keys.authentication.encrypt_block(&xor(state, &block));
            block = [0; 16];
            used = 0;
        }
    }
    block[used] = 0x80;
    state = keys.authentication.encrypt_block(&xor(state, &block));
    keys.finalization
        .encrypt_block(&xor(state, &domain(b'F', 0, 0)))
}

fn seal(keys: &Keys, nonce: &[u8; 12], plaintext: &[u8], context: &[u8]) -> Vec<u8> {
    let mut header = [0; HEADER];
    header[..4].copy_from_slice(b"NXM3");
    header[4] = 3;
    header[5] = 1;
    header[8..20].copy_from_slice(nonce);
    header[20..24].copy_from_slice(&(context.len() as u32).to_be_bytes());
    header[24..28].copy_from_slice(&(plaintext.len() as u32).to_be_bytes());
    let ciphertext = crypt(keys, nonce, plaintext);
    let authentication = tag(keys, &header, context, &ciphertext);
    let mut out = Vec::with_capacity(HEADER + ciphertext.len() + TAG);
    out.extend_from_slice(&header);
    out.extend_from_slice(&ciphertext);
    out.extend_from_slice(&authentication);
    out
}

/// Sender backed by one shared persistent registry per master key.
/// Never delete/roll back this registry or use another registry for the same key.
/// Atomic create-new markers protect normal restarts/concurrent senders;
/// filesystem rollback and loss of directory metadata on power failure are outside this guarantee.
pub struct Sender {
    keys: Keys,
    directory: PathBuf,
    next: u64,
}
impl Sender {
    /// Explicitly initializes a registry for a fresh, never-used master key.
    /// Never initialize the same key again after losing or deleting its state.
    pub fn initialize(master: &[u8; 32], registry: impl AsRef<Path>) -> Result<Self, Error> {
        let keys = Keys::new(master);
        let identity: String = keys.identity.iter().map(|b| format!("{b:02x}")).collect();
        let directory = registry.as_ref().join(identity);
        fs::create_dir_all(registry.as_ref()).map_err(Error::Storage)?;
        fs::create_dir(&directory).map_err(Error::Storage)?;
        let mut metadata = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(directory.join("registry.version"))
            .map_err(Error::Storage)?;
        metadata
            .write_all(b"NXM3-registry-v1")
            .map_err(Error::Storage)?;
        metadata.sync_all().map_err(Error::Storage)?;
        #[cfg(unix)]
        {
            fs::File::open(&directory)
                .and_then(|dir| dir.sync_all())
                .map_err(Error::Storage)?;
            fs::File::open(registry.as_ref())
                .and_then(|dir| dir.sync_all())
                .map_err(Error::Storage)?;
        }
        Ok(Self {
            keys,
            directory,
            next: 0,
        })
    }

    /// Reopens an existing registry. Missing/corrupt state is an error, never an automatic reset.
    /// Keys must be uniformly random, not passwords.
    pub fn open(master: &[u8; 32], registry: impl AsRef<Path>) -> Result<Self, Error> {
        let keys = Keys::new(master);
        let identity: String = keys.identity.iter().map(|b| format!("{b:02x}")).collect();
        let directory = registry.as_ref().join(identity);
        let metadata = fs::read(directory.join("registry.version")).map_err(Error::Storage)?;
        if metadata != b"NXM3-registry-v1" {
            return Err(Error::Storage(io::Error::new(
                io::ErrorKind::InvalidData,
                "invalid registry metadata",
            )));
        }
        Ok(Self {
            keys,
            directory,
            next: 0,
        })
    }

    fn reserve(&mut self) -> Result<[u8; 12], Error> {
        while self.next < MAX_RECORDS {
            let sequence = self.next;
            self.next += 1;
            let path = self.directory.join(format!("{sequence:016x}.used"));
            match OpenOptions::new().create_new(true).write(true).open(path) {
                Ok(mut file) => {
                    // Reserve before encryption. Failed writes still burn this marker.
                    file.write_all(b"NXM3").map_err(Error::Storage)?;
                    file.sync_all().map_err(Error::Storage)?;
                    #[cfg(unix)]
                    fs::File::open(&self.directory)
                        .and_then(|dir| dir.sync_all())
                        .map_err(Error::Storage)?;
                    let mut nonce = [0; 12];
                    nonce[4..].copy_from_slice(&sequence.to_be_bytes());
                    return Ok(nonce);
                }
                Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(error) => return Err(Error::Storage(error)),
            }
        }
        Err(Error::Exhausted)
    }

    /// Encrypts an arbitrary-length message and binds external context into its tag.
    /// An empty message also consumes a nonce. No plaintext or key is written to disk.
    pub fn seal(&mut self, plaintext: &[u8], context: &[u8]) -> Result<Vec<u8>, Error> {
        if plaintext.len() > MAX_MESSAGE || context.len() > MAX_CONTEXT {
            return Err(Error::TooLarge);
        }
        let nonce = self.reserve()?;
        Ok(seal(&self.keys, &nonce, plaintext, context))
    }
}

/// Receiver validates a complete tag before decrypting. Replay protection is a later protocol layer.
pub struct Receiver {
    keys: Keys,
}
impl Receiver {
    /// Constructs a receiver for the same master key as its sender.
    pub fn new(master: &[u8; 32]) -> Self {
        Self {
            keys: Keys::new(master),
        }
    }

    /// Returns plaintext only after successful integrity verification.
    pub fn open(&self, record: &[u8], context: &[u8]) -> Result<Vec<u8>, Error> {
        if record.len() < HEADER + TAG
            || record.len() > HEADER + MAX_MESSAGE + TAG
            || context.len() > MAX_CONTEXT
        {
            return Err(Error::Rejected);
        }
        let header = &record[..HEADER];
        if &header[..4] != b"NXM3" || header[4] != 3 || header[5] != 1 || header[6..8] != [0, 0] {
            return Err(Error::Rejected);
        }
        let aad_len = u32::from_be_bytes(header[20..24].try_into().expect("fixed slice")) as usize;
        let size = u32::from_be_bytes(header[24..28].try_into().expect("fixed slice")) as usize;
        if aad_len != context.len() || size > MAX_MESSAGE || record.len() != HEADER + size + TAG {
            return Err(Error::Rejected);
        }
        let ciphertext = &record[HEADER..HEADER + size];
        let expected = tag(&self.keys, header, context, ciphertext);
        let mut difference = 0_u8;
        for (a, b) in expected.iter().zip(&record[HEADER + size..]) {
            difference |= a ^ b;
        }
        if difference != 0 {
            return Err(Error::Rejected);
        }
        Ok(crypt(&self.keys, &header[8..20], ciphertext))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn hex(text: &str) -> Vec<u8> {
        text.as_bytes()
            .chunks(2)
            .map(|chunk| u8::from_str_radix(std::str::from_utf8(chunk).unwrap(), 16).unwrap())
            .collect()
    }
    fn directory() -> PathBuf {
        std::env::temp_dir().join(format!(
            "nastyx-research-tests-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ))
    }
    #[test]
    fn independent_python_message_vectors() {
        let fixture = include_str!("../../../tests/vectors/v0.3-messages.tsv");
        let mut cases = 0;
        for line in fixture.lines().filter(|line| !line.starts_with('#')) {
            let fields: Vec<_> = line.split('\t').collect();
            let master: [u8; 32] = hex(fields[0]).try_into().unwrap();
            let nonce: [u8; 12] = hex(fields[1]).try_into().unwrap();
            let plaintext = hex(fields[2]);
            let aad = hex(fields[3]);
            let expected = hex(fields[4]);
            assert_eq!(
                seal(&Keys::new(&master), &nonce, &plaintext, &aad),
                expected
            );
            assert_eq!(
                Receiver::new(&master).open(&expected, &aad).unwrap(),
                plaintext
            );
            cases += 1;
        }
        assert_eq!(cases, 10);
    }
    #[test]
    fn rejects_each_changed_byte_wrong_key_context_and_bad_lengths() {
        let master = [9; 32];
        let plaintext = [7; 33];
        let receiver = Receiver::new(&master);
        let record = seal(&Keys::new(&master), &[0; 12], &plaintext, b"context");
        for index in 0..record.len() {
            for bit in 0..8 {
                let mut modified = record.clone();
                modified[index] ^= 1 << bit;
                assert!(matches!(
                    receiver.open(&modified, b"context"),
                    Err(Error::Rejected)
                ));
            }
        }
        assert!(Receiver::new(&[8; 32]).open(&record, b"context").is_err());
        assert!(receiver.open(&record, b"different").is_err());
        assert!(receiver
            .open(&record[..record.len() - 1], b"context")
            .is_err());
        let mut extended = record.clone();
        extended.push(0);
        assert!(receiver.open(&extended, b"context").is_err());
        for size in 0..44 {
            assert!(receiver.open(&record[..size], b"context").is_err());
        }
    }
    #[test]
    fn nonce_survives_reopen_and_coexisting_handles() {
        let root = directory();
        let key = [5; 32];
        let mut first = Sender::initialize(&key, &root).unwrap();
        let mut second = Sender::open(&key, &root).unwrap();
        let a = first.seal(b"same", b"").unwrap();
        let b = second.seal(b"same", b"").unwrap();
        drop(first);
        let mut reopened = Sender::open(&key, &root).unwrap();
        let c = reopened.seal(b"same", b"").unwrap();
        assert_ne!(&a[8..20], &b[8..20]);
        assert_ne!(&b[8..20], &c[8..20]);
        assert_ne!(&a[8..20], &c[8..20]);
        for record in [a, b, c] {
            assert_eq!(Receiver::new(&key).open(&record, b"").unwrap(), b"same");
        }
    }
    #[test]
    fn bounds_exhaustion_and_storage_failure() {
        let mut sender = Sender::initialize(&[1; 32], directory()).unwrap();
        assert!(matches!(
            sender.seal(&vec![0; MAX_MESSAGE + 1], b""),
            Err(Error::TooLarge)
        ));
        assert!(matches!(
            sender.seal(b"", &vec![0; MAX_CONTEXT + 1]),
            Err(Error::TooLarge)
        ));
        assert_eq!(sender.next, 0);
        sender.next = MAX_RECORDS;
        assert!(matches!(sender.seal(b"", b""), Err(Error::Exhausted)));
        let root = directory();
        fs::write(&root, b"not a directory").unwrap();
        assert!(matches!(
            Sender::open(&[1; 32], root),
            Err(Error::Storage(_))
        ));
    }
    #[test]
    fn subkeys_and_domains_differ() {
        let keys = Keys::new(&[0; 32]);
        let block = [0; 16];
        let a = keys.encryption.encrypt_block(&block);
        let b = keys.authentication.encrypt_block(&block);
        let c = keys.finalization.encrypt_block(&block);
        assert_ne!(a, b);
        assert_ne!(b, c);
        assert_ne!(a, c);
        assert_ne!(domain(b'K', 1, 0), domain(b'K', 1, 1));
    }

    #[test]
    fn concurrent_senders_and_abandoned_reservations_do_not_reuse_nonces() {
        let root = directory();
        let key = [42; 32];
        let sender = Sender::initialize(&key, &root).unwrap();
        fs::write(sender.directory.join("0000000000000000.used"), b"").unwrap();
        let mut threads = Vec::new();
        for _ in 0..4 {
            let root = root.clone();
            threads.push(std::thread::spawn(move || {
                let mut sender = Sender::open(&key, root).unwrap();
                (0..16)
                    .map(|_| sender.seal(b"test", b"parallel").unwrap()[8..20].to_vec())
                    .collect::<Vec<_>>()
            }));
        }
        let nonces: Vec<_> = threads
            .into_iter()
            .flat_map(|thread| thread.join().unwrap())
            .collect();
        let unique: std::collections::HashSet<_> = nonces.iter().collect();
        assert_eq!(unique.len(), 64);
        assert!(nonces.iter().all(|nonce| nonce[4..] != [0; 8]));
    }

    #[test]
    fn maximum_message_and_context_round_trip() {
        let mut sender = Sender::initialize(&[23; 32], directory()).unwrap();
        let plaintext = vec![17; MAX_MESSAGE];
        let context = vec![19; MAX_CONTEXT];
        let record = sender.seal(&plaintext, &context).unwrap();
        assert_eq!(
            Receiver::new(&[23; 32]).open(&record, &context).unwrap(),
            plaintext
        );
    }

    #[test]
    fn missing_or_corrupt_registry_is_not_silently_reset() {
        let root = directory();
        let key = [55; 32];
        assert!(matches!(Sender::open(&key, &root), Err(Error::Storage(_))));
        let sender = Sender::initialize(&key, &root).unwrap();
        assert!(matches!(
            Sender::initialize(&key, &root),
            Err(Error::Storage(_))
        ));
        fs::write(sender.directory.join("registry.version"), b"damaged").unwrap();
        assert!(matches!(Sender::open(&key, &root), Err(Error::Storage(_))));
    }
}
