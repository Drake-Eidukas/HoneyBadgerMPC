from honeybadgermpc.field import GF, GFElement
from honeybadgermpc.mixins import DoubleSharing
from honeybadgermpc.elliptic_curve import Subgroup
from honeybadgermpc.mpc import Mpc
import asyncio

Field = GF.get(Subgroup.BLS12_381)


class Jubjub(object):
    """
    JubJub is a twisted Edwards curve of the form -x^2 + y^2 = 1 + dx^2y^2
    """

    def __init__(self, a: GFElement = Field(-1), d: GFElement = -(Field(10240)/Field(10241))):
        # Workaround so that we can simply define field to define these in
        # terms of a given field
        self.a = a
        self.d = d

        self.disc = self.a * self.d * (self.a - self.d) * (self.a - self.d) * \
            (self.a - self.d) * (self.a - self.d)

        if not self.is_smooth():
            raise Exception(f"The curve {self} is not smooth!")

        # TODO: document this term and j
        a_d_term = self.a * self.a + 14 * self.a * self.d + self.d * self.d
        self.j = 16 * a_d_term * a_d_term * a_d_term / self.disc

    def __str__(self) -> str:
        return '%sx^2 + y^2 = 1 + %sx^2y^2' % (self.a, self.d)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        return (self.a, self.d) == (other.a, other.d)

    def is_smooth(self) -> bool:
        return self.disc != 0

    async def contains_shared_point(self, context: Mpc, p: 'SharedPoint') -> bool:
        """
        Checks whether or not the given shares for x and y correspond to a
        point that sits on this curve
        """
        assert isinstance(p, SharedPoint)

        x_sq = await(p.xs * p.xs)
        y_sq = await(p.ys * p.ys)

        # ax^2 + y^2
        lhs = await(context.Share(self.a) * x_sq) + y_sq

        # 1 + dx^2y^2
        rhs = context.Share(1) + await(context.Share(self.d) * await(x_sq * y_sq))

        return await lhs.open() == await rhs.open()

    def contains_point(self, p: 'Point') -> bool:
        """
        Checks whether or not the given x and y coordinates sit on the curve
        """
        return self.a * p.x * p.x + p.y * p.y == 1 + self.d * p.x * p.x * p.y * p.y


class Point(object):
    """
    Represents a point with optimized operations over Edwards curves
    This is the 'local' version of this class, that doesn't deal with shares
    """

    def __init__(self, x: int, y: int, curve: Jubjub = Jubjub()):
        if not isinstance(curve, Jubjub):
            raise Exception(
                f"Could not create Point-- given curve not of type Jubjub ({type(curve)})")

        self.curve = curve  # the curve containing this point
        self.x = x
        self.y = y

        if not self.curve.contains_point(self):
            raise Exception(
                f"Could not create Point({self})-- not on the given curve {curve}!")

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
        elif n == 0:
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

    def __eq__(self, other: object) -> bool:
        if type(other) is Ideal:
            return False

        return (self.x, self.y) == (other.x, other.y)

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __getitem__(self, index: int) -> int:
        return [self.x, self.y][index]

    def double(self) -> 'Point':
        return self + self


class SharedPoint(object):
    """
    Represents a point with optimized operatons over Edward's curves.
    This is the 'shared' version of this class, which does deal with shares
    """

    def __init__(self, context: Mpc, xs, ys, curve: Jubjub = Jubjub()):
        if not isinstance(curve, Jubjub):
            raise Exception(
                f"Could not create Point-- given curve not of type Jubjub ({type(curve)})")

        self.context = context
        self.curve = curve
        self.xs = xs
        self.ys = ys

    async def __init(self):
        if not await(self.curve.contains_shared_point(self.context, self)):
            raise Exception(
                f"Could not initialize Point {self}-- does not sit on given curve {self.curve}")

    @staticmethod
    async def create(context: Mpc, xs, ys, curve=Jubjub()):
        point = SharedPoint(context, xs, ys, curve)
        await(point.__init())
        return point

    @staticmethod
    async def from_point(context: Mpc, p: Point) -> 'SharedPoint':
        if not isinstance(p, Point):
            raise Exception(f"Could not create shared point-- p ({p}) is not a Point!")

        return await(SharedPoint.create(context, context.Share(p.x), context.Share(p.y)))

    def __str__(self) -> str:
        return f"({self.xs}, {self.ys})"

    def __repr__(self) -> str:
        return str(self)

    async def neg(self):
        return await SharedPoint.create(self.context, await (-1 * self.xs), self.ys, self.curve)

    async def add(self, other: 'SharedPoint') -> 'SharedPoint':
        if self.curve != other.curve:
            raise Exception("Can't add points on different curves!")
        elif self.context != other.context:
            raise Exception("Can't add points from different contexts!")
        elif isinstance(other, Ideal):
            return self
        elif not isinstance(other, SharedPoint):
            raise Exception(
                f"Could not add other point-- not an instance of SharedPoint")

        x1, y1, x2, y2 = self.xs, self.ys, other.xs, other.ys

        one = self.context.Share(1)
        y_prod = await(y1 * y2)
        x_prod = await(x1 * x2)
        d_prod = await(await(self.context.Share(self.curve.d) * x_prod) * y_prod)

        # TODO: mpc division
        x3 = (await(x1 * y2) + await(y1 * x2)) / (one + d_prod)
        y3 = (y_prod + x_prod) / (one - d_prod)

        return await(SharedPoint.create(self.context, x3, y3, self.curve))

    async def sub(self, other: 'SharedPoint') -> 'SharedPoint':
        return self.add(await(other.mul(-1)))

    async def mul(self, n: int) -> 'SharedPoint':
        if not isinstance(n, int):
            raise Exception("Can't scale a SharedPoint by something which isn't an int!")

        if n < 0:
            return await(await(self.mul(-1)).mul(-n))
        elif n == 0:
            # TODO: consider returning some SharedIdeal class
            return Ideal(self.curve)

        Q = self
        R = self if n & 1 == 1 else Ideal(self.curve)

        i = 2
        while i <= n:
            Q = await(Q.double())

            if n & i == i:
                R = await(R.add(Q))

            i = i << 1

        return R

    async def double(self) -> 'SharedPoint':
        return await(self.add(self))


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

    def __eq__(self, other: object) -> bool:
        return type(other) is Ideal


if __name__ == '__main__':
    """
    main method for quick testing
    """
    n, t = 9, 2
    curve = Jubjub()

    p_actual = Point(0, 1)
    x_secret, y_secret = p_actual.x, p_actual.y

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
