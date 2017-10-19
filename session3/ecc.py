from binascii import hexlify, unhexlify
from io import BytesIO
from random import randint
from unittest import TestCase, skip

from helper import encode_base58, encode_base58_checksum, hash160, double_sha256


class FieldElement:

    def __init__(self, num, prime):
        self.num = num
        self.prime = prime
        if self.num >= self.prime or self.num < 0:
            error = 'Num {} not in field range 0 to {}'.format(
                self.num, self.prime-1)
            raise RuntimeError(error)

    def __eq__(self, other):
        if other is None:
            return False
        return self.num == other.num and self.prime == other.prime

    def __ne__(self, other):
        if other is None:
            return True
        return self.num != other.num or self.prime != other.prime

    def __repr__(self):
        return 'FieldElement_{}({})'.format(self.prime, self.num)

    def __add__(self, other):
        num = (self.num + other.num) % self.prime
        return self.__class__(num=num, prime=self.prime)

    def __sub__(self, other):
        num = (self.num - other.num) % self.prime
        return self.__class__(num=num, prime=self.prime)

    def __mul__(self, other):
        num = (self.num * other.num) % self.prime
        return self.__class__(num=num, prime=self.prime)

    def __rmul__(self, coefficient):
        num = (self.num * coefficient) % self.prime
        return self.__class__(num=num, prime=self.prime)

    def __pow__(self, n):
        n = n % (self.prime - 1)
        num = pow(self.num, n, self.prime)
        return self.__class__(num=num, prime=self.prime)

    def __truediv__(self, other):
        other_inv = pow(other.num, self.prime - 2, self.prime)
        return self*self.__class__(num=other_inv, prime=self.prime)


class FieldElementTest(TestCase):

    def test_add(self):
        a = FieldElement(2, 31)
        b = FieldElement(15, 31)
        self.assertEqual(a+b, FieldElement(17, 31))
        a = FieldElement(17, 31)
        b = FieldElement(21, 31)
        self.assertEqual(a+b, FieldElement(7, 31))

    def test_sub(self):
        a = FieldElement(29, 31)
        b = FieldElement(4, 31)
        self.assertEqual(a-b, FieldElement(25, 31))
        a = FieldElement(15, 31)
        b = FieldElement(30, 31)
        self.assertEqual(a-b, FieldElement(16, 31))

    def test_mul(self):
        a = FieldElement(24, 31)
        b = FieldElement(19, 31)
        self.assertEqual(a*b, FieldElement(22, 31))

    def test_rmul(self):
        a = FieldElement(24, 31)
        b = 2
        self.assertEqual(b*a, a+a)

    def test_pow(self):
        a = FieldElement(17, 31)
        self.assertEqual(a**3, FieldElement(15, 31))
        a = FieldElement(5, 31)
        b = FieldElement(18, 31)
        self.assertEqual(a**5 * b, FieldElement(16, 31))

    def test_div(self):
        a = FieldElement(3, 31)
        b = FieldElement(24, 31)
        self.assertEqual(a/b, FieldElement(4, 31))
        a = FieldElement(17, 31)
        self.assertEqual(a**-3, FieldElement(29, 31))
        a = FieldElement(4, 31)
        b = FieldElement(11, 31)
        self.assertEqual(a**-4*b, FieldElement(13, 31))


class Point:

    def __init__(self, x, y, a, b):
        self.a = a
        self.b = b
        if x is None and y is None:
            # point at infinity
            self.x = None
            self.y = None
            return
        if y**2 != x**3 + self.a * x + self.b:
            raise RuntimeError('Not a point on the curve')
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y \
            and self.a == other.a and self.b == other.b

    def __ne__(self, other):
        return self.x != other.x or self.y != other.y \
            or self.a != other.a or self.b != other.b

    def __repr__(self):
        if self.x is None:
            return 'Point(infinity)'
        else:
            return 'Point({},{})'.format(self.x, self.y)

    def __add__(self, other):
        # identity
        if self.x is None:
            return other
        if other.x is None:
            return self
        if self.x == other.x:
            if self.y != other.y:
                # point at infinity
                return self.__class__(x=None, y=None, a=self.a, b=self.b)
            # we're adding a point to itself
            s = (3* self.x**2 + self.a) / (2* self.y)
            x = s**2 - 2*self.x
            y = s * (self.x - x) - self.y
            return self.__class__(x=x, y=y, a=self.a, b=self.b)
        else:
            s = (other.y - self.y) / (other.x - self.x)
            x = s**2 - self.x - other.x
            y = s * (self.x - x) - self.y
            return self.__class__(x=x, y=y, a=self.a, b=self.b)

    def __rmul__(self, coefficient):
        # naive way - see below for binary expansion method
        result = self.__class__(x=None, y=None, a=self.a, b=self.b)
        for i in range(coefficient):
            result += self
        return result


class PointTest(TestCase):

    def test_on_curve(self):
        with self.assertRaises(RuntimeError):
            Point(x=-2, y=4, a=5, b=7)
        # these should not raise an error
        Point(x=3, y=-7, a=5, b=7)
        Point(x=18, y=77, a=5, b=7)
        Point(x=None, y=None, a=5, b=7)

    def test_add0(self):
        a = Point(x=None, y=None, a=5, b=7)
        b = Point(x=2, y=5, a=5, b=7)
        c = Point(x=2, y=-5, a=5, b=7)
        self.assertEqual(a+b, b)
        self.assertEqual(b+a, b)
        self.assertEqual(b+c, a)

    def test_add1(self):
        a = Point(x=3, y=7, a=5, b=7)
        b = Point(x=-1, y=-1, a=5, b=7)
        self.assertEqual(a+b, Point(x=2, y=-5, a=5, b=7))

    def test_add2(self):
        a = Point(x=-1, y=1, a=5, b=7)
        self.assertEqual(a+a, Point(x=18, y=-77, a=5, b=7))


class ECCTest(TestCase):

    def test_on_curve(self):
        # tests the following points whether they are on the curve or not
        # on curve y^2=x^3-7 over F_223:
        # (200,119) (42,99) - not on curve
        # (192,105) (17,56) (1,193) - on curve
        # the ones that aren't should raise a RuntimeError
        a = FieldElement(num=0, prime=223)
        b = FieldElement(num=7, prime=223)
        with self.assertRaises(RuntimeError):
            x = FieldElement(num=200, prime=223)
            y = FieldElement(num=119, prime=223)
            Point(x=x, y=y, a=a, b=b)
        with self.assertRaises(RuntimeError):
            x = FieldElement(num=42, prime=223)
            y = FieldElement(num=99, prime=223)
            Point(x=x, y=y, a=a, b=b)
        # these should go through fine
        x = FieldElement(num=192, prime=223)
        y = FieldElement(num=105, prime=223)
        Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=17, prime=223)
        y = FieldElement(num=56, prime=223)
        Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=1, prime=223)
        y = FieldElement(num=193, prime=223)
        Point(x=x, y=y, a=a, b=b)

    def test_add1(self):
        # tests the following additions on curve y^2=x^3-7 over F_223:
        # (192,105) + (17,56) = (170, 142)
        # (47,71) + (117,141) = (60, 139)
        # (143,98) + (76,66) = (47, 71)
        a = FieldElement(num=0, prime=223)
        b = FieldElement(num=7, prime=223)
        x = FieldElement(num=192, prime=223)
        y = FieldElement(num=105, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=17, prime=223)
        y = FieldElement(num=56, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=170, prime=223)
        y = FieldElement(num=142, prime=223)
        p3 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(p1+p2, p3)
        x = FieldElement(num=47, prime=223)
        y = FieldElement(num=71, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=117, prime=223)
        y = FieldElement(num=141, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=60, prime=223)
        y = FieldElement(num=139, prime=223)
        p3 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(p1+p2, p3)
        x = FieldElement(num=143, prime=223)
        y = FieldElement(num=98, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=76, prime=223)
        y = FieldElement(num=66, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=47, prime=223)
        y = FieldElement(num=71, prime=223)
        p3 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(p1+p2, p3)

    def test_rmul(self):
        # tests the following scalar multiplications
        # 2*(192,105) = (49, 71)
        # 2*(143,98) = (64, 168)
        # 2*(47,71) = (36, 111)
        # 4*(47,71) = (194, 51)
        # 8*(47,71) = (116, 55)
        # 21*(47,71) = (None, None)
        a = FieldElement(num=0, prime=223)
        b = FieldElement(num=7, prime=223)
        x = FieldElement(num=192, prime=223)
        y = FieldElement(num=105, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=49, prime=223)
        y = FieldElement(num=71, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(2*p1, p2)
        x = FieldElement(num=143, prime=223)
        y = FieldElement(num=98, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=64, prime=223)
        y = FieldElement(num=168, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(2*p1, p2)
        x = FieldElement(num=47, prime=223)
        y = FieldElement(num=71, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        x = FieldElement(num=36, prime=223)
        y = FieldElement(num=111, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(2*p1, p2)
        x = FieldElement(num=194, prime=223)
        y = FieldElement(num=51, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(4*p1, p2)
        x = FieldElement(num=116, prime=223)
        y = FieldElement(num=55, prime=223)
        p2 = Point(x=x, y=y, a=a, b=b)
        self.assertEqual(8*p1, p2)
        p2 = Point(x=None, y=None, a=a, b=b)
        self.assertEqual(21*p1, p2)
        x = FieldElement(num=15, prime=223)
        y = FieldElement(num=86, prime=223)
        p1 = Point(x=x, y=y, a=a, b=b)
        p2 = Point(x=None, y=None, a=a, b=b)
        self.assertEqual(7*p1, p2)


A = 0
B = 7
P = 2**256 - 2**32 - 977
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


class S256Field(FieldElement):

    def __init__(self, num, prime=None):
        super().__init__(num=num, prime=P)

    def hex(self):
        return '{:x}'.format(self.num).zfill(64)

    def __repr__(self):
        return self.hex()


class S256Point(Point):
    bits = 256

    def __init__(self, x, y, a=None, b=None):
        a, b = S256Field(A), S256Field(B)
        if x is None:
            super().__init__(x=None, y=None, a=a, b=b)
        elif type(x) == int:
            super().__init__(x=S256Field(x), y=S256Field(y), a=a, b=b)
        else:
            super().__init__(x=x, y=y, a=a, b=b)

    def __repr__(self):
        if self.x is None:
            return 'Point(infinity)'
        else:
            return 'Point({},{})'.format(self.x, self.y)

    def __rmul__(self, coefficient):
        # current will undergo binary expansion
        current = self
        # result is what we return, starts at 0
        result = S256Point(None, None)
        # we double 256 times and add where there is a 1 in the binary
        # representation of coefficient
        for i in range(self.bits):
            if coefficient & 1:
                result += current
            current += current
            # we shift the coefficient to the right
            coefficient >>= 1
        return result

    def sec(self, compressed=True):
        if compressed:
            if self.y.num % 2 == 1:
                prefix = '03'
            else:
                prefix = '02'
            return '{}{}'.format(prefix, self.x.hex())
        else:
            return '04{}{}'.format(self.x.hex(), self.y.hex())

    def address(self, compressed=True, testnet=False):
        h160 = hash160(unhexlify(self.sec(compressed=compressed)))
        if testnet:
            prefix = b'\x6f'
        else:
            prefix = b'\x00'
        raw = prefix + h160
        raw = raw + double_sha256(raw)[:4]
        return encode_base58(raw).decode('ascii')

    def verify(self, z, sig):
        u = z * pow(sig.s, N-2, N) % N
        v = sig.r * pow(sig.s, N-2, N) % N
        return (u*G + v*self).x.num == sig.r


G = S256Point(
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


class S256Test(TestCase):

    def test_order(self):
        point = N*G
        self.assertIsNone(point.x)

    def test_pubpoint(self):
        # write a test that tests the public point for the following
        # coefficients: 7G, 1485G, 2**128G, (2**240+2**31)G
        point = 7*G
        expected = (
            0x5CBDF0646E5DB4EAA398F365F2EA7A0E3D419B7E0330E39CE92BDDEDCAC4F9BC,
            0x6AEBCA40BA255960A3178D6D861A54DBA813D0B813FDE7B5A5082628087264DA)
        self.assertEqual((point.x.num, point.y.num), expected)
        point = 1485*G
        expected = (
            0xC982196A7466FBBBB0E27A940B6AF926C1A74D5AD07128C82824A11B5398AFDA,
            0x7A91F9EAE64438AFB9CE6448A1C133DB2D8FB9254E4546B6F001637D50901F55)
        self.assertEqual((point.x.num, point.y.num), expected)
        point = 2**128*G
        expected = (
            0x8F68B9D2F63B5F339239C1AD981F162EE88C5678723EA3351B7B444C9EC4C0DA,
            0x662A9F2DBA063986DE1D90C2B6BE215DBBEA2CFE95510BFDF23CBF79501FFF82)
        self.assertEqual((point.x.num, point.y.num), expected)
        point = (2**240+2**31)*G
        expected = (
            0x9577FF57C8234558F293DF502CA4F09CBC65A6572C842B39B366F21717945116,
            0x10B49C67FA9365AD7B90DAB070BE339A1DAF9052373EC30FFAE4F72D5E66D053)
        self.assertEqual((point.x.num, point.y.num), expected)

    def test_sec(self):
        coefficient = 999**3
        uncompressed = '049d5ca49670cbe4c3bfa84c96a8c87df086c6ea6a24ba6b809c9de234496808d56fa15cc7f3d38cda98dee2419f415b7513dde1301f8643cd9245aea7f3f911f9'
        compressed = '039d5ca49670cbe4c3bfa84c96a8c87df086c6ea6a24ba6b809c9de234496808d5'
        point = coefficient*G
        self.assertEqual(point.sec(compressed=False), uncompressed)
        self.assertEqual(point.sec(compressed=True), compressed)
        coefficient = 123
        uncompressed = '04a598a8030da6d86c6bc7f2f5144ea549d28211ea58faa70ebf4c1e665c1fe9b5204b5d6f84822c307e4b4a7140737aec23fc63b65b35f86a10026dbd2d864e6b'
        compressed = '03a598a8030da6d86c6bc7f2f5144ea549d28211ea58faa70ebf4c1e665c1fe9b5'
        point = coefficient*G
        self.assertEqual(point.sec(compressed=False), uncompressed)
        self.assertEqual(point.sec(compressed=True), compressed)
        coefficient = 42424242
        uncompressed = '04aee2e7d843f7430097859e2bc603abcc3274ff8169c1a469fee0f20614066f8e21ec53f40efac47ac1c5211b2123527e0e9b57ede790c4da1e72c91fb7da54a3'
        compressed = '03aee2e7d843f7430097859e2bc603abcc3274ff8169c1a469fee0f20614066f8e'
        point = coefficient*G
        self.assertEqual(point.sec(compressed=False), uncompressed)
        self.assertEqual(point.sec(compressed=True), compressed)

    def test_address(self):
        secret = 888**3
        mainnet_address = '148dY81A9BmdpMhvYEVznrM45kWN32vSCN'
        testnet_address = 'mieaqB68xDCtbUBYFoUNcmZNwk74xcBfTP'
        point = secret*G
        self.assertEqual(
            point.address(compressed=True, testnet=False), mainnet_address)
        self.assertEqual(
            point.address(compressed=True, testnet=True), testnet_address)
        secret = 321
        mainnet_address = '1S6g2xBJSED7Qr9CYZib5f4PYVhHZiVfj'
        testnet_address = 'mfx3y63A7TfTtXKkv7Y6QzsPFY6QCBCXiP'
        point = secret*G
        self.assertEqual(
            point.address(compressed=False, testnet=False), mainnet_address)
        self.assertEqual(
            point.address(compressed=False, testnet=True), testnet_address)
        secret = 4242424242
        mainnet_address = '1226JSptcStqn4Yq9aAmNXdwdc2ixuH9nb'
        testnet_address = 'mgY3bVusRUL6ZB2Ss999CSrGVbdRwVpM8s'
        point = secret*G
        self.assertEqual(
            point.address(compressed=False, testnet=False), mainnet_address)
        self.assertEqual(
            point.address(compressed=False, testnet=True), testnet_address)

    def test_verify(self):
        point = S256Point(
            0x887387e452b8eacc4acfde10d9aaf7f6d9a0f975aabb10d006e4da568744d06c,
            0x61de6d95231cd89026e286df3b6ae4a894a3378e393e93a0f45b666329a0ae34)
        z = 0xec208baa0fc1c19f708a9ca96fdeff3ac3f230bb4a7ba4aede4942ad003c0f60
        sig = Signature(
            0xac8d1c87e51d0d441be8b3dd5b05c8795b48875dffe00b7ffcfac23010d3a395,
            0x68342ceff8935ededd102dd876ffd6ba72d6a427a3edb13d26eb0781cb423c4)
        self.assertTrue(point.verify(z, sig))
        z = 0x7c076ff316692a3d7eb3c3bb0f8b1488cf72e1afcd929e29307032997a838a3d
        sig = Signature(
            0xeff69ef2b1bd93a66ed5219add4fb51e11a840f404876325a1e8ffe0529a2c,
            0xc7207fee197d27c618aea621406f6bf5ef6fca38681d82b2f06fddbdce6feab6)
        self.assertTrue(point.verify(z, sig))


class Signature:

    def __init__(self, r, s):
        self.r = r
        self.s = s

    def __repr__(self):
        return 'Signature({:x},{:x})'.format(self.r, self.s)

    def der(self):
        rbin = self.r.to_bytes(32, byteorder='big')
        # if rbin has a high bit, add a 00
        if rbin[0] > 128:
            rbin = b'\x00' + rbin
        result = bytes([2, len(rbin)]) + rbin
        sbin = self.s.to_bytes(32, byteorder='big')
        # if sbin has a high bit, add a 00
        if sbin[0] > 128:
            sbin = b'\x00' + sbin
        result += bytes([2, len(sbin)]) + sbin
        return bytes([0x30, len(result)]) + result

    @classmethod
    def parse(cls, signature_bin):
        s = BytesIO(signature_bin)
        compound = s.read(1)[0]
        if compound != 0x30:
            raise RuntimeError("Bad Signature")
        length = s.read(1)[0]
        if length + 2 != len(signature_bin):
            raise RuntimeError("Bad Signature Length")
        marker = s.read(1)[0]
        if marker != 0x02:
            raise RuntimeError("Bad Signature")
        rlength = s.read(1)[0]
        r = int(hexlify(s.read(rlength)), 16)
        marker = s.read(1)[0]
        if marker != 0x02:
            raise RuntimeError("Bad Signature")
        slength = s.read(1)[0]
        s = int(hexlify(s.read(slength)), 16)
        if len(signature_bin) != 6 + rlength + slength:
            raise RuntimeError("Signature too long")
        return cls(r, s)


class SignatureTest(TestCase):

    def test_der(self):
        testcases = (
            (1, 2),
            (randint(0, 2**256), randint(0, 2**255)),
            (randint(0, 2**256), randint(0, 2**255)),
        )
        for r, s in testcases:
            sig = Signature(r, s)
            der = sig.der()
            sig2 = Signature.parse(der)
            self.assertEqual(sig2.r, r)
            self.assertEqual(sig2.s, s)


class PrivateKey:

    def __init__(self, secret):
        self.secret = secret
        self.point = secret*G

    def hex(self):
        return '{:x}'.format(self.secret).zfill(64)

    def sign(self, z):
        k = randint(0, 2**256)
        r = (k*G).x.num
        s = (z + r*self.secret) * pow(k, N-2, N) % N
        if s*2 > N:
            s = N - s
        return Signature(r, s)

    def wif(self, compressed=True, testnet=False):
        s = self.secret.to_bytes(32, 'big')
        prefix = b'\xef' if testnet else b'\x80'
        suffix = b'\x01' if compressed else b''
        s = prefix + s + suffix
        return encode_base58_checksum(s)

class PrivateKeyTest(TestCase):

    def test_sign(self):
        pk = PrivateKey(randint(0, 2**256))
        z = randint(0, 2**256)
        sig = pk.sign(z)
        self.assertTrue(pk.point.verify(z, sig))

    def test_wif(self):
        pk = PrivateKey(2**256-2**199)
        expected = 'L5oLkpV3aqBJ4BgssVAsax1iRa77G5CVYnv9adQ6Z87te7TyUdSC'
        self.assertEqual(pk.wif(compressed=True, testnet=False), expected)
        pk = PrivateKey(2**256-2**201)
        expected = '93XfLeifX7Jx7n7ELGMAf1SUR6f9kgQs8Xke8WStMwUtrDucMzn'
        self.assertEqual(pk.wif(compressed=False, testnet=True), expected)
        pk = PrivateKey(0x0dba685b4511dbd3d368e5c4358a1277de9486447af7b3604a69b8d9d8b7889d)
        expected = '5HvLFPDVgFZRK9cd4C5jcWki5Skz6fmKqi1GQJf5ZoMofid2Dty'
        self.assertEqual(pk.wif(compressed=False, testnet=False), expected)
        pk = PrivateKey(0x1cca23de92fd1862fb5b76e5f4f50eb082165e5191e116c18ed1a6b24be6a53f)
        expected = 'cNYfWuhDpbNM1JWc3c6JTrtrFVxU4AGhUKgw5f93NP2QaBqmxKkg'
        self.assertEqual(pk.wif(compressed=True, testnet=True), expected)
