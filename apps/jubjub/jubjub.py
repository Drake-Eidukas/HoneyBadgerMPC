from honeybadgermpc.field import GF

Field = GF(0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001)


class Jubjub(object):
    """
    JubJub is a twisted Edwards curve of the form -x^2 + y^2 = 1 + dx^2y^2
    """

    def __init__(self, a: Field = Field(-1), d: Field = -(Field(10240)/Field(10241))):
        self.a = a
        self.d = d

        self.disc = a * d * (a - d) * (a - d) * (a - d) * (a - d)

        # TODO: document this term and j
        a_d_term = a * a + 14 * a * d + d * d
        self.j = 16 * a_d_term * a_d_term * a_d_term / self.disc

        if not self.isSmooth():
            raise Exception("The curve %s is not smooth!" % self)

    def isSmooth(self) -> bool:
        return self.disc != 0

    def testPoint(self, x: int, y: int) -> bool:
        """
        Checks to make sure that the point sits on this curve
        """
        return self.a * x * x + y*y == 1 + self.d * x * x * y * y

    def __str__(self) -> str:
        return '%sx^2 + y^2 = 1 + %sx^2y^2' % (self.a, self.d)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        return (self.a, self.d) == (other.a, other.d)


class Point(object):
    """
    Represents a point with optimized operations over Edwards curves
    """

    def __init__(self, x, y, curve=Jubjub()):
        self.curve = curve  # the curve containing this point
        self.x = x
        self.y = y

        if not self.curve.testPoint(x, y):
            raise Exception("The point %s is not on the given curve %s!" % (self, curve))

    def __str__(self):
        return "(%r, %r)" % (self.x, self.y)

    def __repr__(self):
        return str(self)

    def __neg__(self):
        return Point(Field(-self.x), self.y, self.curve)

    def __add__(self, Q: 'Point') -> 'Point':
        if self.curve != Q.curve:
            raise Exception("Can't add points on different curves!")

        if isinstance(Q, Ideal):
            return self

        x1, y1, x2, y2 = self.x, self.y, Q.x, Q.y

        x3 = ((x1 * y2) + (y1 * x2)) / (1 + self.curve.d * x1 * x2 * y1 * y2)
        y3 = ((y1 * y2) + (x1 * x2)) / (1 - self.curve.d * x1 * x2 * y1 * y2)

        return Point(x3, y3)

    def __sub__(self, Q: 'Point') -> 'Point':
        return self + -Q

    def __mul__(self, n: int) -> 'Point':
        if not isinstance(n, int):
            raise Exception("Can't scale a point by something which isn't an int!")

        if n < 0:
            return -self * -n

        if n == 0:
            return Ideal(self.curve)

        Q = self
        R = self if n & 1 == 1 else Ideal(self.curve)

        i = 2
        while i <= n:
            Q += Q

            if n & i == i:
                R += Q

            i = i << 1

        return R

    def __rmul__(self, n: int):
        return self * n

    def __list__(self):
        return [self.x, self.y]

    def __eq__(self, other) -> bool:
        if type(other) is Ideal:
            return False

        return self.x, self.y == other.x, other.y

    def __ne__(self, other) -> bool:
        return not self == other

    def __getitem__(self, index: int) -> int:
        return [self.x, self.y][index]

    def double(self) -> 'Point':
        return self + self


class Ideal(Point):
    """
    Represents the point at infinity of the curve
    """

    def __init__(self, curve):
        self.curve = curve

    def __neg__(self):
        return self

    def __str__(self):
        return "Ideal"

    def __add__(self, Q: 'Point') -> 'Point':
        if self.curve != Q.curve:
            raise Exception("Can't add points on different curves!")

        return Q

    def __mul__(self, n: int) -> 'Point':
        if not isinstance(n, int):
            raise Exception("Can't scale a point by something which isn't an int!")
        else:
            return self

    def __eq__(self, other) -> bool:
        return type(other) is Ideal


def main():
    """ 
    main method for quick testing
    """

    p = Point(0, 1)
    print(p)
    ideal = Ideal(p.curve)
    print(ideal)

    print(p + ideal)
    print(2 * p + 3 * ideal)

    try:
        print(p * ideal)
    except:
        print('correctly prevented multiplying points')

    pass


if __name__ == '__main__':
    main()
