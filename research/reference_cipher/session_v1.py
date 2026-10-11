"""Independent NXS1 reference, experimental; not approved for real secrets.

Pairing secrets MUST come from a trusted separate channel. All state is volatile.
This Python reference has no guaranteed secret erasure or timing guarantees.
"""
from secrets import compare_digest
from message_v3 import Message, domain, MAX_CONTEXT

MAX_PLAINTEXT = 65536
MAX_SKIP = 64
MAX_MESSAGES = 1048576
HEADER = 68


def authenticate(key, data):
    if len(data) > MAX_CONTEXT:
        raise ValueError('size limit')
    header = domain(72) + len(data).to_bytes(4, 'big')
    return Message(key).tag(header, data, b'')


def code(key, label, context):
    return authenticate(key, b'NXS1' + bytes([label]) + context)


def expand(key, label, context):
    return b''.join(code(key, label, bytes([part]) + context) for part in (0, 1))


def handshake(kind, body, key):
    unsigned = b'NXH1' + bytes([kind]) + body
    return unsigned + code(key, kind, unsigned)


def check_handshake(packet, kind, size, key):
    if (len(packet) != size or packet[:5] != b'NXH1' + bytes([kind])
            or not compare_digest(packet[-16:], code(key, kind, packet[:-16]))):
        raise ValueError('handshake rejected')


class Pairing:
    def __init__(self, secret, initiator, responder):
        if (len(secret) != 32 or secret == bytes(32) or len(initiator) != 16
                or len(responder) != 16 or initiator == responder):
            raise ValueError('invalid pairing')
        self.secret, self.a, self.b = secret, initiator, responder

    def consume(self):
        if self.secret is None:
            raise ValueError('pairing consumed')
        secret, self.secret = self.secret, None
        return secret

    def initiate(self, sid, challenge):
        if len(sid) != 16 or len(challenge) != 16:
            raise ValueError('invalid challenge')
        secret = self.consume()
        body = self.a + self.b + sid + challenge
        return Initiator(secret, body), handshake(1, body, secret)

    def respond(self, offer, challenge):
        secret = self.consume()
        if len(challenge) != 16:
            raise ValueError('invalid challenge')
        check_handshake(offer, 1, 85, secret)
        if offer[5:37] != self.a + self.b:
            raise ValueError('peer rejected')
        transcript = offer[5:69] + challenge
        return Responder(expand(secret, 10, transcript), transcript), handshake(2, transcript, secret)


class Initiator:
    def __init__(self, secret, body):
        self.secret, self.body = secret, body

    def complete(self, reply):
        secret, self.secret = self.secret, None
        if secret is None:
            raise ValueError('handshake consumed')
        check_handshake(reply, 2, 101, secret)
        if reply[5:69] != self.body:
            raise ValueError('transcript rejected')
        transcript = reply[5:85]
        root = expand(secret, 10, transcript)
        return UnverifiedSession(root, transcript, 0), handshake(3, transcript, root)


class Responder:
    def __init__(self, root, transcript):
        self.root, self.transcript = root, transcript

    def complete(self, confirm):
        root, self.root = self.root, None
        if root is None:
            raise ValueError('handshake consumed')
        check_handshake(confirm, 3, 101, root)
        if confirm[5:85] != self.transcript:
            raise ValueError('transcript rejected')
        return UnverifiedSession(root, self.transcript, 1)


class UnverifiedSession:
    def __init__(self, root, transcript, direction):
        self.verification = code(root, 11, transcript)
        self.session = Session(root, transcript, direction)

    def verify_peer(self, external_code):
        session, self.session = self.session, None
        if session is None or not compare_digest(self.verification, external_code):
            if session is not None:
                session.close()
            raise ValueError('peer verification failed')
        return session


def step(chain, direction, sequence):
    context = bytes([direction]) + sequence.to_bytes(8, 'big')
    return expand(chain, 30, context), expand(chain, 31, context)


class Session:
    def __init__(self, root, transcript, direction):
        self.sid = transcript[32:48]
        self.local = transcript[16 * direction:16 * direction + 16]
        self.peer = transcript[16 * (1 - direction):16 * (1 - direction) + 16]
        self.direction = direction
        self.sending = expand(root, 20 + direction, transcript)
        self.receiving = expand(root, 21 - direction, transcript)
        self.sent = self.received = 0
        self.skipped = {}
        self.closed = False

    def seal(self, plaintext):
        if self.closed:
            raise ValueError('session closed')
        if len(plaintext) > MAX_PLAINTEXT or self.sent >= MAX_MESSAGES:
            raise ValueError('session limit')
        header = (b'NXS1' + bytes([self.direction, 0, 0, 0]) + self.sid
                  + self.local + self.peer + self.sent.to_bytes(8, 'big')
                  + (len(plaintext) + 44).to_bytes(4, 'big'))
        key, next_chain = step(self.sending, self.direction, self.sent)
        packet = header + Message(key).seal_for_vector(bytes(12), plaintext, header)
        self.sending, self.sent = next_chain, self.sent + 1
        return packet

    def open(self, packet):
        if self.closed:
            raise ValueError('session closed')
        if (len(packet) < HEADER + 44 or len(packet) > HEADER + 44 + MAX_PLAINTEXT
                or packet[:8] != b'NXS1' + bytes([1 - self.direction, 0, 0, 0])
                or packet[8:56] != self.sid + self.peer + self.local
                or int.from_bytes(packet[64:68], 'big') != len(packet) - HEADER
                or packet[HEADER + 8:HEADER + 20] != bytes(12)):
            raise ValueError('record rejected')
        sequence = int.from_bytes(packet[56:64], 'big')
        if sequence >= MAX_MESSAGES:
            raise ValueError('record rejected')
        if sequence < self.received:
            if sequence not in self.skipped:
                raise ValueError('record rejected')
            plaintext = Message(self.skipped[sequence]).open(packet[HEADER:], packet[:HEADER])
            del self.skipped[sequence]
            return plaintext
        gap = sequence - self.received
        if gap > MAX_SKIP or len(self.skipped) + gap > MAX_SKIP:
            raise ValueError('record rejected')
        chain, pending = self.receiving, {}
        for index in range(self.received, sequence):
            pending[index], chain = step(chain, 1 - self.direction, index)
        key, next_chain = step(chain, 1 - self.direction, sequence)
        plaintext = Message(key).open(packet[HEADER:], packet[:HEADER])
        self.skipped.update(pending)
        self.receiving, self.received = next_chain, sequence + 1
        return plaintext

    def discard_skipped(self):
        self.skipped.clear()

    def close(self):
        self.closed = True
        self.sending = self.receiving = None
        self.skipped.clear()
