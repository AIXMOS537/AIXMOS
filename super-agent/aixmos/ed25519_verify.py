"""
ed25519_verify.py -- Ed25519 signature VERIFICATION in pure Python (RFC 8032, section 6 reference algorithm).

Used by licence.py when the 'cryptography' package is not installed (the bundled Windows runtime ships without it).
Verification only: this module cannot sign, so it can never mint a licence. Slow (tens of milliseconds) but a
licence is checked once and cached.

  verify(public_key_32_bytes, message_bytes, signature_64_bytes) -> bool
"""
import hashlib

p = 2 ** 255 - 19
q = 2 ** 252 + 27742317777372353535851937790883648493

def _inv(x):
    return pow(x, p - 2, p)

d = -121665 * _inv(121666) % p
_SQRT_M1 = pow(2, (p - 1) // 4, p)

def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % p
    C = 2 * P[3] * Q[3] * d % p
    D = 2 * P[2] * Q[2] % p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % p, G * H % p, F * G % p, E * H % p)

def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q

def _equal(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % p == 0

def _recover_x(y, sign):
    if y >= p:
        return None
    x2 = (y * y - 1) * _inv(d * y * y + 1) % p
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (p + 3) // 8, p)
    if (x * x - x2) % p != 0:
        x = x * _SQRT_M1 % p
    if (x * x - x2) % p != 0:
        return None
    if (x & 1) != sign:
        x = p - x
    return x

_GY = 4 * _inv(5) % p
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % p)

def _decompress(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % p)

def verify(public, msg, signature):
    if not isinstance(public, (bytes, bytearray)) or len(public) != 32 or len(signature) != 64:
        return False
    A = _decompress(bytes(public))
    if A is None:
        return False
    Rs = bytes(signature[:32])
    R = _decompress(Rs)
    if R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= q:
        return False
    h = int.from_bytes(hashlib.sha512(Rs + bytes(public) + bytes(msg)).digest(), "little") % q
    return _equal(_mul(s, _G), _add(R, _mul(h, A)))
