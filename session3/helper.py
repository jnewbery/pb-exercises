from binascii import hexlify, unhexlify
from unittest import TestCase, skip

import hashlib


BASE58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def hash160(s):
    return hashlib.new('ripemd160', hashlib.sha256(s).digest()).digest()


def double_sha256(s):
    return hashlib.sha256(hashlib.sha256(s).digest()).digest()


def encode_base58(s):
    # determine how many 0 bytes (b'\x00') s starts with
    count = 0
    for c in s:
        if c == 0:
            count += 1
        else:
            break
    prefix = b'1' * count
    # convert from binary to hex, then hex to integer
    num = int(hexlify(s), 16)
    result = bytearray()
    while num > 0:
        num, mod = divmod(num, 58)
        result.insert(0, BASE58_ALPHABET[mod])

    return prefix + bytes(result)


def encode_base58_checksum(s):
    return encode_base58(s + double_sha256(s)[:4]).decode('ascii')


def decode_base58(s):
    num = 0
    for c in s.encode('ascii'):
        num *= 58
        num += BASE58_ALPHABET.index(c)
    # disregard the prefix and checksum
    return num.to_bytes(25, byteorder='big')[1:-4]


def flip_endian(h):
    '''flip_endian takes a hex string and flips the endianness
    Returns a hexadecimal string
    '''
    raise NotImplementedError


def little_endian_to_int(b):
    '''little_endian_to_int takes byte sequence as a little-endian number.
    Returns an integer'''
    raise NotImplementedError


def int_to_little_endian(n, length):
    '''endian_to_little_endian takes an integer and returns the little-endian
    byte sequence of length'''
    raise NotImplementedError


class HelperTest(TestCase):

    def test_base58(self):
        addr = 'mnrVtF8DWjMu839VW3rBfgYaAfKk8983Xf'
        h160 = hexlify(decode_base58(addr))
        want = b'507b27411ccf7f16f10297de6cef3f291623eddf'
        self.assertEqual(h160, want)
        got = encode_base58_checksum(b'\x6f' + unhexlify(h160))
        self.assertEqual(got, addr)

    @skip('unimplemented')
    def test_flip_endian(self):
        h = '03ee4f7a4e68f802303bc659f8f817964b4b74fe046facc3ae1be4679d622c45'
        w = '452c629d67e41baec3ac6f04fe744b4b9617f8f859c63b3002f8684e7a4fee03'
        self.assertEqual(flip_endian(h), w)
        h = '813f79011acb80925dfe69b3def355fe914bd1d96a3f5f71bf8303c6a989c7d1'
        w = 'd1c789a9c60383bf715f3f6ad9d14b91fe55f3deb369fe5d9280cb1a01793f81'
        self.assertEqual(flip_endian(h), w)

    @skip('unimplemented')
    def test_little_endian_to_int(self):
        h = unhexlify('99c3980000000000')
        want = 10011545
        self.assertEqual(little_endian_to_int(h), want)
        h = unhexlify('a135ef0100000000')
        want = 32454049
        self.assertEqual(little_endian_to_int(h), want)

    @skip('unimplemented')
    def test_int_to_little_endian(self):
        n = 1
        want = b'\x01\x00\x00\x00'
        self.assertEqual(int_to_little_endian(n, 4), want)
        n = 10011545
        want = b'\x99\xc3\x98\x00\x00\x00\x00\x00'
        self.assertEqual(int_to_little_endian(n, 8), want)
