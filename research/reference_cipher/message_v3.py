"""Independent research reference. Explicit nonces are ONLY for lab vectors."""
from engine_v3 import Engine

MAX_MESSAGE = 1_048_576
MAX_CONTEXT = 65_536


def domain(kind, role=0, part=0):
    return bytes([78,88,kind,3,role,part])+bytes(10)


class Message:
    def __init__(self, master):
        root = Engine(master)
        self.roles = [Engine(root.encrypt(domain(75,role,0))+root.encrypt(domain(75,role,1)))
                      for role in (1,2,3)]

    def crypt(self, nonce, data):
        out = bytearray()
        for index in range(0,len(data),16):
            stream = self.roles[0].encrypt(nonce+(index//16).to_bytes(4,'big'))
            out.extend(a ^ b for a,b in zip(data[index:index+16],stream))
        return bytes(out)

    def tag(self, header, aad, ciphertext):
        state = self.roles[1].encrypt(domain(77))
        payload = header+aad+ciphertext+b'\x80'
        payload += bytes((-len(payload)) % 16)
        for index in range(0,len(payload),16):
            state = self.roles[1].encrypt(bytes(a ^ b for a,b in zip(state,payload[index:index+16])))
        return self.roles[2].encrypt(bytes(a ^ b for a,b in zip(state,domain(70))))

    def seal_for_vector(self, nonce, plaintext, aad=b''):
        if len(nonce)!=12 or len(plaintext)>MAX_MESSAGE or len(aad)>MAX_CONTEXT:
            raise ValueError('invalid size')
        header = b'NXM3'+bytes([3,1,0,0])+nonce+len(aad).to_bytes(4,'big')+len(plaintext).to_bytes(4,'big')
        ciphertext = self.crypt(nonce,plaintext)
        return header+ciphertext+self.tag(header,aad,ciphertext)

    def open(self, record, aad=b''):
        if len(record)<44 or len(record)>44+MAX_MESSAGE or len(aad)>MAX_CONTEXT:
            raise ValueError('record rejected')
        header = record[:28]
        if header[:8]!=b'NXM3'+bytes([3,1,0,0]):
            raise ValueError('record rejected')
        context_len, size = int.from_bytes(header[20:24],'big'),int.from_bytes(header[24:28],'big')
        if context_len!=len(aad) or size>MAX_MESSAGE or len(record)!=44+size:
            raise ValueError('record rejected')
        cipher = record[28:-16]
        from secrets import compare_digest
        if not compare_digest(self.tag(header,aad,cipher),record[-16:]):
            raise ValueError('record rejected')
        return self.crypt(header[8:20],cipher)
