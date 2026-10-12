//! Experimental paired-device E2EE sessions over NA&STY-X v0.3.
//! Requires a random one-time pairing secret delivered outside the relay.
//! No public-key agreement, automatic compromise recovery, durable key storage,
//! guaranteed erasure, side-channel protection, or independently proven security.
use nastyx_message::{authentication_code, tags_equal, OneTimeSealer, Receiver};
use zeroize::{Zeroize, Zeroizing};
type Secret = Zeroizing<[u8; 32]>;
use std::collections::BTreeMap;

pub const MAX_PLAINTEXT: usize = 65_536;
pub const MAX_SKIP: usize = 64;
pub const MAX_MESSAGES: u64 = 1_048_576;
const HEADER: usize = 68;

#[derive(Debug, PartialEq, Eq)]
pub enum Error {
    Rejected,
    Size,
    Limit,
    Closed,
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Rejected => "session record rejected",
            Self::Size => "session size limit exceeded",
            Self::Limit => "session limit reached; establish a new session",
            Self::Closed => "session closed",
        })
    }
}
impl std::error::Error for Error {}

fn code(key: &[u8; 32], label: u8, context: &[u8]) -> [u8; 16] {
    let mut input = b"NXS1".to_vec();
    input.push(label);
    input.extend_from_slice(context);
    authentication_code(key, &input).expect("bounded internal context")
}

fn expand(key: &[u8; 32], label: u8, context: &[u8]) -> Secret {
    let mut input = vec![0];
    input.extend_from_slice(context);
    let a = Zeroizing::new(code(key, label, &input));
    input[0] = 1;
    let b = Zeroizing::new(code(key, label, &input));
    let mut out = Zeroizing::new([0; 32]);
    out[..16].copy_from_slice(&*a);
    out[16..].copy_from_slice(&*b);
    out
}

fn handshake(kind: u8, body: &[u8], key: &[u8; 32]) -> Vec<u8> {
    let mut packet = b"NXH1".to_vec();
    packet.push(kind);
    packet.extend_from_slice(body);
    let proof = code(key, kind, &packet);
    packet.extend_from_slice(&proof);
    packet
}
fn verify_handshake(packet: &[u8], kind: u8, size: usize, key: &[u8; 32]) -> bool {
    packet.len() == size
        && packet[..5] == [b'N', b'X', b'H', b'1', kind]
        && tags_equal(
            &code(key, kind, &packet[..size - 16]),
            packet[size - 16..]
                .try_into()
                .expect("validated tag length"),
        )
}

/// One-time pairing data. Both IDs and the secret must be verified out of band.
/// Obtain secret/challenges/session IDs from the OS CSPRNG, never a password.
/// Creating another Pairing with the same secret defeats the one-time contract.
pub struct Pairing {
    secret: Secret,
    initiator: [u8; 16],
    responder: [u8; 16],
}
impl Pairing {
    pub fn new(secret: [u8; 32], initiator: [u8; 16], responder: [u8; 16]) -> Result<Self, Error> {
        let secret = Zeroizing::new(secret);
        if initiator == responder || *secret == [0; 32] {
            return Err(Error::Rejected);
        }
        Ok(Self {
            secret,
            initiator,
            responder,
        })
    }
    pub fn initiate(self, session_id: [u8; 16], challenge: [u8; 16]) -> (Initiator, Vec<u8>) {
        let mut body = Vec::with_capacity(64);
        body.extend_from_slice(&self.initiator);
        body.extend_from_slice(&self.responder);
        body.extend_from_slice(&session_id);
        body.extend_from_slice(&challenge);
        let packet = handshake(1, &body, &self.secret);
        (
            Initiator {
                pairing: self,
                body,
            },
            packet,
        )
    }
    pub fn respond(self, offer: &[u8], challenge: [u8; 16]) -> Result<(Responder, Vec<u8>), Error> {
        if !verify_handshake(offer, 1, 85, &self.secret)
            || offer[5..21] != self.initiator
            || offer[21..37] != self.responder
        {
            return Err(Error::Rejected);
        }
        let mut transcript = offer[5..69].to_vec();
        transcript.extend_from_slice(&challenge);
        let packet = handshake(2, &transcript, &self.secret);
        let root = expand(&self.secret, 10, &transcript);
        Ok((Responder { root, transcript }, packet))
    }
}

impl Drop for Pairing {
    fn drop(&mut self) {
        self.secret.zeroize(); // Owned storage only; historical copies/registers are not covered.
    }
}
pub struct Initiator {
    pairing: Pairing,
    body: Vec<u8>,
}
impl Initiator {
    /// Consumes the pending handshake, including on errors.
    pub fn complete(self, reply: &[u8]) -> Result<(UnverifiedSession, Vec<u8>), Error> {
        if !verify_handshake(reply, 2, 101, &self.pairing.secret) || reply[5..69] != self.body {
            return Err(Error::Rejected);
        }
        let transcript = &reply[5..85];
        let mut root = expand(&self.pairing.secret, 10, transcript);
        let confirm = handshake(3, transcript, &root);
        let session = UnverifiedSession::new(&root, transcript, 0);
        root.zeroize();
        Ok((session, confirm))
    }
}
pub struct Responder {
    root: Secret,
    transcript: Vec<u8>,
}
impl Responder {
    pub fn complete(self, confirm: &[u8]) -> Result<UnverifiedSession, Error> {
        if !verify_handshake(confirm, 3, 101, &self.root) || confirm[5..85] != self.transcript {
            return Err(Error::Rejected);
        }
        Ok(UnverifiedSession::new(&self.root, &self.transcript, 1))
    }
}
impl Drop for Responder {
    fn drop(&mut self) {
        self.root.zeroize();
    }
}

/// Cannot send or receive until the user compares the full peer verification code.
pub struct UnverifiedSession {
    verification: [u8; 16],
    session: Session,
}
impl UnverifiedSession {
    fn new(root: &[u8; 32], transcript: &[u8], direction: u8) -> Self {
        let a: [u8; 16] = transcript[..16].try_into().expect("fixed transcript");
        let b: [u8; 16] = transcript[16..32].try_into().expect("fixed transcript");
        Self {
            verification: code(root, 11, transcript),
            session: Session {
                id: transcript[32..48].try_into().expect("fixed transcript"),
                local: if direction == 0 { a } else { b },
                peer: if direction == 0 { b } else { a },
                direction,
                sending: expand(root, 20 + direction, transcript),
                receiving: expand(root, 21 - direction, transcript),
                sent: 0,
                received: 0,
                skipped: BTreeMap::new(),
                closed: false,
            },
        }
    }
    pub fn verification_code(&self) -> [u8; 16] {
        self.verification
    }
    /// The supplied code must come from the peer via a trusted separate channel,
    /// not from the relay or this object's own code automatically.
    pub fn verify_peer(self, externally_compared_code: &[u8; 16]) -> Result<Session, Error> {
        if !tags_equal(&self.verification, externally_compared_code) {
            return Err(Error::Rejected);
        }
        Ok(self.session)
    }
}

/// In-memory paired-device session. Intentionally not Clone or serializable.
/// Restart requires fresh pairing. Never snapshot, fork, or duplicate live state.
pub struct Session {
    id: [u8; 16],
    local: [u8; 16],
    peer: [u8; 16],
    direction: u8,
    sending: Secret,
    receiving: Secret,
    sent: u64,
    received: u64,
    skipped: BTreeMap<u64, Secret>,
    closed: bool,
}
fn step(chain: &[u8; 32], direction: u8, sequence: u64) -> (Secret, Secret) {
    let mut context = vec![direction];
    context.extend_from_slice(&sequence.to_be_bytes());
    (expand(chain, 30, &context), expand(chain, 31, &context))
}
impl Session {
    pub fn session_id(&self) -> [u8; 16] {
        self.id
    }
    pub fn seal(&mut self, plaintext: &[u8]) -> Result<Vec<u8>, Error> {
        if self.closed {
            return Err(Error::Closed);
        }
        if plaintext.len() > MAX_PLAINTEXT {
            return Err(Error::Size);
        }
        if self.sent >= MAX_MESSAGES {
            return Err(Error::Limit);
        }
        let mut header = b"NXS1".to_vec();
        header.extend_from_slice(&[self.direction, 0, 0, 0]);
        header.extend_from_slice(&self.id);
        header.extend_from_slice(&self.local);
        header.extend_from_slice(&self.peer);
        header.extend_from_slice(&self.sent.to_be_bytes());
        header.extend_from_slice(&((plaintext.len() + 44) as u32).to_be_bytes());
        let (mut key, next) = step(&self.sending, self.direction, self.sent);
        let result = OneTimeSealer::new(&key).seal(plaintext, &header);
        key.zeroize();
        let record = result.map_err(|_| Error::Size)?;
        self.sending = next;
        self.sent += 1; // Commit before returning any ciphertext to the application.
        header.extend_from_slice(&record);
        Ok(header)
    }
    pub fn open(&mut self, packet: &[u8]) -> Result<Vec<u8>, Error> {
        if self.closed {
            return Err(Error::Closed);
        }
        if packet.len() < HEADER + 44
            || packet.len() > HEADER + 44 + MAX_PLAINTEXT
            || packet[..4] != *b"NXS1"
            || packet[4] != 1 - self.direction
            || packet[5..8] != [0; 3]
            || packet[8..24] != self.id
            || packet[24..40] != self.peer
            || packet[40..56] != self.local
        {
            return Err(Error::Rejected);
        }
        let sequence = u64::from_be_bytes(packet[56..64].try_into().expect("fixed header"));
        let size = u32::from_be_bytes(packet[64..68].try_into().expect("fixed header")) as usize;
        if size > MAX_PLAINTEXT + 44 || size + HEADER != packet.len() || sequence >= MAX_MESSAGES {
            return Err(Error::Rejected);
        }
        // Session records use a single fresh key and the canonical zero nonce.
        if packet[HEADER + 8..HEADER + 20] != [0; 12] {
            return Err(Error::Rejected);
        }
        if sequence < self.received {
            let key = self.skipped.get(&sequence).ok_or(Error::Rejected)?;
            let result = Receiver::new(key)
                .open(&packet[HEADER..], &packet[..HEADER])
                .map_err(|_| Error::Rejected)?;
            // Clear the occupied map slot before removal can move its value.
            if let Some(key) = self.skipped.get_mut(&sequence) {
                key.zeroize();
            }
            self.skipped.remove(&sequence);
            return Ok(result);
        }
        let gap = sequence - self.received;
        if gap > MAX_SKIP as u64 || self.skipped.len() + gap as usize > MAX_SKIP {
            return Err(Error::Rejected);
        }
        // Derive on temporary state. No replay/chain mutation before authenticating.
        let mut chain = Zeroizing::new(*self.receiving);
        let mut pending = BTreeMap::new();
        for index in self.received..sequence {
            let (key, next) = step(&chain, 1 - self.direction, index);
            pending.insert(index, key);
            chain = next;
        }
        let (mut key, next) = step(&chain, 1 - self.direction, sequence);
        let result = Receiver::new(&key)
            .open(&packet[HEADER..], &packet[..HEADER])
            .map_err(|_| Error::Rejected);
        key.zeroize();
        chain.zeroize();
        match result {
            Ok(plaintext) => {
                self.skipped.append(&mut pending);
                self.receiving = next;
                self.received = sequence + 1;
                Ok(plaintext)
            }
            Err(error) => {
                for key in pending.values_mut() {
                    key.zeroize();
                }
                Err(error)
            }
        }
    }
    /// Explicitly discard keys of lost messages; they can never be received later.
    pub fn discard_skipped(&mut self) {
        for key in self.skipped.values_mut() {
            key.zeroize();
        }
        self.skipped.clear();
    }
    pub fn close(&mut self) {
        self.closed = true;
        self.sending.zeroize();
        self.receiving.zeroize();
        self.discard_skipped();
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        self.close();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn pair(seed: u8) -> (Session, Session) {
        let a = Pairing::new([7; 32], [1; 16], [2; 16]).unwrap();
        let b = Pairing::new([7; 32], [1; 16], [2; 16]).unwrap();
        let (a, offer) = a.initiate([seed; 16], [4; 16]);
        let (b, reply) = b.respond(&offer, [5; 16]).unwrap();
        let (a, confirm) = a.complete(&reply).unwrap();
        let b = b.complete(&confirm).unwrap();
        let ac = a.verification_code();
        let bc = b.verification_code();
        assert_eq!(ac, bc);
        (a.verify_peer(&bc).unwrap(), b.verify_peer(&ac).unwrap())
    }
    #[test]
    fn handshake_rejects_wrong_secret_ids_reflection_and_verification() {
        let make = |secret, a, b| Pairing::new(secret, a, b).unwrap();
        let (a, offer) = make([7; 32], [1; 16], [2; 16]).initiate([3; 16], [4; 16]);
        assert!(make([8; 32], [1; 16], [2; 16])
            .respond(&offer, [5; 16])
            .is_err());
        assert!(make([7; 32], [2; 16], [1; 16])
            .respond(&offer, [5; 16])
            .is_err());
        let (b, reply) = make([7; 32], [1; 16], [2; 16])
            .respond(&offer, [5; 16])
            .unwrap();
        let (ua, confirm) = a.complete(&reply).unwrap();
        assert!(ua.verify_peer(&[0; 16]).is_err());
        assert!(b.complete(&reply).is_err());
        assert_eq!(confirm.len(), 101);
        assert!(Pairing::new([0; 32], [1; 16], [2; 16]).is_err());
        assert!(Pairing::new([1; 32], [1; 16], [1; 16]).is_err());
    }
    #[test]
    fn handshake_mutations_are_authenticated() {
        let make = || Pairing::new([7; 32], [1; 16], [2; 16]).unwrap();
        let (_, offer) = make().initiate([3; 16], [4; 16]);
        for index in 0..offer.len() {
            for bit in 0..8 {
                let mut changed = offer.clone();
                changed[index] ^= 1 << bit;
                assert!(make().respond(&changed, [5; 16]).is_err());
            }
        }
        let (_, reply) = make().respond(&offer, [5; 16]).unwrap();
        for index in 0..reply.len() {
            let (a, _) = make().initiate([3; 16], [4; 16]);
            let mut changed = reply.clone();
            changed[index] ^= 1;
            assert!(a.complete(&changed).is_err());
        }
        let (a, _) = make().initiate([3; 16], [4; 16]);
        let (_, confirm) = a.complete(&reply).unwrap();
        for index in 0..confirm.len() {
            let (b, _) = make().respond(&offer, [5; 16]).unwrap();
            let mut changed = confirm.clone();
            changed[index] ^= 1;
            assert!(b.complete(&changed).is_err());
        }
    }
    #[test]
    fn reordered_messages_replays_and_bidirectional_keys() {
        let (mut a, mut b) = pair(3);
        let p0 = a.seal(b"zero").unwrap();
        let p1 = a.seal(b"one").unwrap();
        let p2 = a.seal(b"two").unwrap();
        assert_eq!(b.open(&p2).unwrap(), b"two");
        assert_eq!(b.open(&p0).unwrap(), b"zero");
        assert!(b.open(&p0).is_err());
        assert_eq!(b.open(&p1).unwrap(), b"one");
        assert!(b.skipped.is_empty());
        let reply = b.seal(b"zero").unwrap();
        assert_ne!(&reply[HEADER..], &p0[HEADER..]);
        assert_eq!(a.open(&reply).unwrap(), b"zero");
        assert!(a.open(&p0).is_err()); // reflection
    }
    #[test]
    fn modified_records_do_not_advance_or_consume_skipped_keys() {
        let (mut a, mut b) = pair(3);
        let p0 = a.seal(b"zero").unwrap();
        let p1 = a.seal(b"one").unwrap();
        let before = *b.receiving;
        for index in 0..p1.len() {
            let mut changed = p1.clone();
            changed[index] ^= 1;
            assert!(b.open(&changed).is_err());
            assert_eq!(*b.receiving, before);
            assert_eq!(b.received, 0);
            assert!(b.skipped.is_empty());
        }
        assert_eq!(b.open(&p1).unwrap(), b"one");
        let mut changed = p0.clone();
        *changed.last_mut().unwrap() ^= 1;
        assert!(b.open(&changed).is_err());
        assert!(b.skipped.contains_key(&0));
        assert_eq!(b.open(&p0).unwrap(), b"zero");
    }
    #[test]
    fn malformed_lengths_unknown_suites_and_large_gaps() {
        let (mut a, mut b) = pair(3);
        let packet = a.seal(b"test").unwrap();
        for end in 0..packet.len() {
            assert!(b.open(&packet[..end]).is_err());
        }
        let mut tail = packet.clone();
        tail.push(0);
        assert!(b.open(&tail).is_err());
        let mut huge_length = packet.clone();
        huge_length[64..68].copy_from_slice(&u32::MAX.to_be_bytes());
        assert!(b.open(&huge_length).is_err());
        let mut future = packet.clone();
        future[56..64].copy_from_slice(&u64::MAX.to_be_bytes());
        assert!(b.open(&future).is_err());
        future[56..64].copy_from_slice(&65_u64.to_be_bytes());
        assert!(b.open(&future).is_err());
        assert_eq!(b.open(&packet).unwrap(), b"test");
    }
    #[test]
    fn skip_limit_discard_and_session_exhaustion() {
        let (mut a, mut b) = pair(3);
        let packets: Vec<_> = (0..67).map(|_| a.seal(b"").unwrap()).collect();
        assert!(b.open(&packets[65]).is_err());
        assert!(b.open(&packets[64]).is_ok());
        assert_eq!(b.skipped.len(), MAX_SKIP);
        assert!(b.open(&packets[66]).is_err()); // total skipped keys would be 65
        b.discard_skipped();
        assert!(b.open(&packets[0]).is_err());
        assert!(b.open(&packets[66]).is_ok());
        a.sent = MAX_MESSAGES;
        assert_eq!(a.seal(b"").unwrap_err(), Error::Limit);
    }
    #[test]
    fn fresh_pairing_revocation_restart_and_device_separation() {
        let (mut a, mut b) = pair(3);
        let old = a.seal(b"old").unwrap();
        let (mut fresh_a, mut fresh_b) = pair(9);
        assert!(fresh_b.open(&old).is_err());
        assert_ne!(*a.sending, *fresh_a.sending);
        b.close();
        assert_eq!(b.open(&old).unwrap_err(), Error::Closed);
        a.close();
        assert_eq!(a.seal(b"old").unwrap_err(), Error::Closed);
        let new = fresh_a.seal(b"new").unwrap();
        assert_eq!(fresh_b.open(&new).unwrap(), b"new");
        // A second device must use another pairing and its own IDs.
        let p = Pairing::new([9; 32], [1; 16], [8; 16]).unwrap();
        let (p, offer) = p.initiate([3; 16], [4; 16]);
        let (q, reply) = Pairing::new([9; 32], [1; 16], [8; 16])
            .unwrap()
            .respond(&offer, [5; 16])
            .unwrap();
        let (p, confirm) = p.complete(&reply).unwrap();
        let q = q.complete(&confirm).unwrap();
        let pc = p.verification_code();
        let qc = q.verification_code();
        let mut c = q.verify_peer(&pc).unwrap();
        let mut d = p.verify_peer(&qc).unwrap();
        assert!(c.open(&old).is_err());
        assert!(c.open(&new).is_err());
        assert_eq!(c.open(&d.seal(b"device").unwrap()).unwrap(), b"device");
    }
    #[test]
    fn current_state_cannot_directly_decrypt_old_packet() {
        let (mut a, mut b) = pair(3);
        let initial_chain = *a.sending;
        let old = a.seal(b"old").unwrap();
        b.open(&old).unwrap();
        assert_ne!(*a.sending, initial_chain);
        assert_ne!(*b.receiving, initial_chain);
        let (current_message_key, _) = step(&a.sending, 0, 1);
        assert!(Receiver::new(&current_message_key)
            .open(&old[HEADER..], &old[..HEADER])
            .is_err());
        assert!(b.skipped.is_empty());
        // This checks deletion from logical state, NOT one-wayness or physical erasure.
    }
    #[test]
    fn size_limit_and_closed_state() {
        let (mut a, mut b) = pair(3);
        assert_eq!(
            a.seal(&vec![0; MAX_PLAINTEXT + 1]).unwrap_err(),
            Error::Size
        );
        assert_eq!(a.sent, 0);
        let bytes = vec![19; MAX_PLAINTEXT];
        assert_eq!(b.open(&a.seal(&bytes).unwrap()).unwrap(), bytes);
        b.close();
        assert_eq!(*b.receiving, [0; 32]);
        assert_eq!(*b.sending, [0; 32]);
    }
    #[test]
    fn bounded_parser_fuzz_never_panics_or_mutates_state() {
        let (mut a, mut b) = pair(3);
        let valid = a.seal(b"parser fuzz").unwrap();
        let before = *b.receiving;
        let mut public_seed = 20261012_u64;
        for index in 0..10_000 {
            let mut packet = if index % 2 == 0 {
                valid.clone()
            } else {
                vec![0; index % 300]
            };
            for byte in &mut packet {
                public_seed = public_seed
                    .wrapping_mul(6364136223846793005)
                    .wrapping_add(1);
                if index % 2 == 1 {
                    *byte = (public_seed >> 32) as u8;
                }
            }
            if index % 2 == 0 {
                let offset = (public_seed as usize) % packet.len();
                packet[offset] ^= 1 << (index % 8);
            }
            assert!(b.open(&packet).is_err());
            assert_eq!(*b.receiving, before);
            assert_eq!(b.received, 0);
            assert!(b.skipped.is_empty());
        }
        assert_eq!(b.open(&valid).unwrap(), b"parser fuzz");
    }
}
