"""NA&STY-X v0.3 research engine; no security guarantee."""
MASK = (1 << 64)-1
SBOX = (190, 229, 15, 88, 39, 251, 206, 56, 202, 154, 67, 13, 231, 38, 118, 137, 84, 73, 163, 175, 130, 207, 249, 106, 42, 217, 111, 55, 186, 164, 242, 213, 157, 160, 147, 30, 44, 250, 218, 96, 254, 243, 132, 14, 210, 225, 185, 77, 72, 33, 48, 27, 50, 69, 155, 7, 187, 52, 97, 141, 93, 212, 18, 159, 95, 148, 180, 24, 94, 227, 80, 66, 178, 208, 209, 98, 253, 133, 149, 22, 128, 222, 181, 21, 165, 58, 145, 54, 138, 112, 123, 4, 9, 168, 8, 82, 219, 45, 247, 211, 215, 193, 53, 92, 177, 26, 140, 183, 29, 179, 120, 203, 102, 201, 0, 184, 105, 40, 244, 136, 79, 226, 63, 172, 192, 200, 37, 108, 70, 1, 237, 150, 239, 103, 245, 167, 114, 6, 189, 91, 61, 151, 223, 31, 115, 221, 5, 161, 117, 74, 246, 122, 11, 252, 188, 162, 113, 125, 195, 135, 19, 119, 28, 153, 116, 3, 234, 240, 236, 198, 25, 23, 233, 197, 124, 17, 224, 2, 57, 86, 90, 12, 46, 32, 121, 199, 76, 62, 34, 36, 65, 176, 68, 146, 49, 83, 170, 85, 230, 104, 173, 139, 126, 171, 235, 10, 51, 110, 131, 216, 16, 127, 35, 99, 43, 75, 194, 47, 59, 248, 60, 214, 220, 255, 134, 228, 205, 87, 169, 182, 81, 166, 158, 20, 204, 143, 238, 152, 142, 174, 196, 64, 101, 109, 41, 89, 241, 156, 232, 78, 100, 107, 144, 129, 191, 71)


def rot(x, n):
    return ((x << n) | (x >> (64-n))) & MASK


def round_function(x, k):
    b = (x ^ k).to_bytes(8, 'little')
    z = int.from_bytes(bytes(SBOX[b[i]] for i in (2,5,0,7,4,1,6,3)), 'little')
    y = ((z + rot(z,17)) & MASK) ^ rot(z,41)
    y = ((y + rot(y,31)) & MASK) ^ rot(y,23)
    return ((y + rot(y,11)) & MASK) ^ rot(y,37) ^ k


class Engine:
    def __init__(self, key, rounds=24):
        if len(key) != 32 or type(rounds) is not int or rounds not in (8,12,16,20,24):
            raise ValueError('32-byte key and supported round count required')
        state = [int.from_bytes(key[i:i+8],'big') for i in range(0,32,8)]
        self.keys = []
        for i in range(rounds):
            a,b,c,d = state
            constant = (0x9E3779B97F4A7C15*(i+1)) & MASK
            k = round_function(round_function(a ^ rot(b,13), c ^ constant) ^ d, constant)
            self.keys.append(k)
            state = [b ^ rot(a,7), (c + rot(k,11)) & MASK, d ^ rot(b,29), (k+a) & MASK]

    def encrypt(self, block):
        if len(block) != 16:
            raise ValueError('16-byte block required')
        l,r = int.from_bytes(block[:8],'big'),int.from_bytes(block[8:],'big')
        for k in self.keys:
            l,r = r,l ^ round_function(r,k)
        return l.to_bytes(8,'big')+r.to_bytes(8,'big')

    def decrypt(self, block):
        if len(block) != 16:
            raise ValueError('16-byte block required')
        l,r = int.from_bytes(block[:8],'big'),int.from_bytes(block[8:],'big')
        for k in reversed(self.keys):
            l,r = r ^ round_function(l,k),l
        return l.to_bytes(8,'big')+r.to_bytes(8,'big')
