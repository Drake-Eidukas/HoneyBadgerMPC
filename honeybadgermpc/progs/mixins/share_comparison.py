from honeybadgermpc.progs.mixins.base import MixinBase, AsyncMixin
from honeybadgermpc.progs.mixins.constants import MixinConstants
from honeybadgermpc.utils import static_type_check
from honeybadgermpc.preprocessing import PreProcessedElements
from honeybadgermpc.elliptic_curve import GF, Subgroup
from gmpy2 import num_digits

from asyncio import gather


class Equality(AsyncMixin):
    from honeybadgermpc.mpc import Mpc, GFElement

    name = MixinConstants.ShareEquality

    @staticmethod
    @static_type_check(GFElement)
    def legendre_mod_p(a):
        """Return the legendre symbol ``legendre(a, p)`` where *p* is the
        order of the field of *a*.
        """
        assert a.modulus % 2 == 1

        b = a ** ((a.modulus - 1)//2)
        if b == 1:
            return 1
        elif b == a.modulus-1:
            return -1
        return 0

    @staticmethod
    @static_type_check(Mpc, 'context.Share')
    async def _gen_test_bit(context, diff):
        # # b \in {0, 1}
        b = MixinBase.pp_elements.get_bit(context)

        # # _b \in {5, 1}, for p = 1 mod 8, s.t. (5/p) = -1
        # # so _b = -4 * b + 5
        _b = (-4 * b) + context.Share(5)

        _r = MixinBase.pp_elements.get_rand(context)
        _rp = MixinBase.pp_elements.get_rand(context)

        # c = a * r + b * rp * rp
        # If b_i == 1, c_i is guaranteed to be a square modulo p if a is zero
        # and with probability 1/2 otherwise (except if rp == 0).
        # If b_i == -1 it will be non-square.
        c = await ((diff * _r) + (_b * _rp * _rp)).open()

        return c, _b

    @staticmethod
    @static_type_check(Mpc, 'context.Share')
    async def gen_test_bit(context, diff):
        cj, bj = await Equality._gen_test_bit(context, diff)
        while cj == 0:
            cj, bj = await Equality._gen_test_bit(context, diff)

        legendre = Equality.legendre_mod_p(cj)
        if legendre == 0:
            return Equality.gen_test_bit(context, diff)

        return (legendre / context.field(2)) * (bj + context.Share(legendre))

    @staticmethod
    @static_type_check(Mpc, 'context.Share', 'context.Share', int)
    async def _prog(context, p_share, q_share, security_parameter=32):
        diff = p_share - q_share

        x = await gather(*[Equality.gen_test_bit(context, diff)
                           for _ in range(security_parameter)])

        # Take the product (this is here the same as the "and") of all
        # the x'es
        while len(x) > 1:
            # Repeatedly split the shares in half and element-wise multiply the halves
            # until there's only one left.
            # TODO: Use a future version of this computation
            x_first, x_left = context.ShareArray(x[::2]), context.ShareArray(x[1::2])
            x = (await (x_first * x_left))._shares

        # Returns share, this will be equal to 0 only if the shares are equal
        return x[0]


class LessThan(AsyncMixin):
    """ Given two shares, a_share and b_share with corresponding values a and b,
    compute a < b and output the result as a share.

    args:
        context (Mpc): MPC context
        a_share (context.Share) Share representing a in a < b
        b_share (context.Share) Share representing b in a < b

    output:
        A share representing 1 if a < b, otherwise 0

    Source:
    MULTIPARTY COMPARISON - An Improved Multiparty Protocol for
    Comparison of Secret-shared Values by Tord Ingolf Reistad(2007)
    """
    from honeybadgermpc.mpc import Mpc
    from honeybadgermpc.field import GF

    name = MixinConstants.ShareLessThan

    @staticmethod
    @static_type_check(Mpc, 'context.Share', 'context.Share')
    async def _prog(context, a_share, b_share):
        pp_elements = PreProcessedElements()
        modulus = Subgroup.BLS12_381
        field = GF(modulus)
        bit_length = num_digits(modulus, 2)

        # assert 2 * a_share + 1 < modulus, "[a] < (p-1)/2 must hold"
        # assert 2 * b_share + 1 < modulus, "[b] < (p-1)/2 must hold"

        # ############# PART 1 ###############
        # First Transformation
        r_bits = [pp_elements.get_bit(context) for _ in range(bit_length)]
        r_bigb = field(0)
        for i, b in enumerate(r_bits):
            r_bigb = r_bigb + (2**i) * b

        z = a_share - b_share

        twoz0_open = int(await(2*z).open()) % 2
        a_open = int(await a_share.open())
        b_open = int(await b_share.open())
        assert (a_open < b_open) == (twoz0_open)

        c = await(2 * z + r_bigb).open()
        c_bits = [field(int(x)) for x in list('{0:0255b}'.format(c.value))]
        c_bits.reverse()
        r_0 = r_bits[0]
        c0 = c_bits[0]

        r_bigb_open = await r_bigb.open()
        r_0_open = int(r_bigb_open) % 2
        r_0_open2 = await r_0.open()
        assert r_0_open == r_0_open2
        rbgtc = int(r_bigb_open) > int(c)
        assert twoz0_open == (c0 ^ r_0_open ^ rbgtc)

        # ############# PART 2 ###############
        # Compute bigx
        bigx = field(0)
        for i in range(bit_length-1):
            cr = field(0)
            for j in range(i+1, bit_length):
                c_xor_r = r_bits[j] + c_bits[j] - field(2)*c_bits[j]*r_bits[j]
                cr = cr + c_xor_r
            cr_open = await cr.open()
            pp = pow(2, int(cr_open))
            bigx = bigx + (field(1) - c_bits[i]) * pp * r_bits[i]
        bigx = bigx + (field(1) - c_bits[bit_length-1]) * r_bits[bit_length-1]    # ???

        # ############# PART 3 ###############
        # Extracting LSB
        # TODO
        # assert bigx.v.value < sqrt(4 * modulus)

        s_bits = [pp_elements.get_bit(context) for _ in range(bit_length)]

        s_0 = s_bits[0]
        s1 = s_bits[-1]        # [s_{bit_length-1}]
        s2 = s_bits[-2]        # [s_{bit_length-2}]
        s1s2 = await(s1*s2)

        s_bigb = field(0)
        for i, b in enumerate(s_bits):
            s_bigb = s_bigb + (2**i) * b

        # Compute d_hat for check
        # d_hat = s_hat + x
        s_hat_bits = s_bits[:-2]
        assert len(s_hat_bits) == len(s_bits) - 2
        s_hat_bigb = field(0)
        for i, b in enumerate(s_hat_bits):
            s_hat_bigb = s_hat_bigb + (2**i) * b

        d_hat = s_hat_bigb + bigx
        d_hat_open = await d_hat.open()
        import math
        # Condition from paper
        assert int(d_hat_open) < 2**(bit_length-2) + math.sqrt(4 * modulus)

        d_hat_0_open = int(d_hat_open) % 2

        bigd = s_bigb + bigx
        d = await bigd.open()
        d0 = int(d) & 1

        # TODO
        # assert d > sqrt(4 * modulus)

        # d0 ^ (d < 2**{bit_length-1})
        dxor1 = d0 ^ (d.value < 2**(bit_length-1))
        # d0 ^ (d < 2**{bit_length-1})
        dxor2 = d0 ^ (d.value < 2**(bit_length-2))
        # d0 ^ (d < (2**{bit_length-2} + 2**{bit_length-1}))
        dxor12 = d0 ^ (d.value < (2**(bit_length-1) + 2**(bit_length-2)))

        d_0 = d0 * (field(1) + s1s2 - s1 - s2) \
            + dxor2 * (s2 - s1s2) \
            + dxor1 * (s1 - s1s2) \
            + dxor12 * s1s2

        # Check alternate way of computing d_hat_0
        d_0_open = await d_0.open()
        assert d_0_open == d_hat_0_open

        # [x0] = [s0] ^ [d0], equal to [r]B > c
        x_0 = s_0 + d_0 - 2 * (await(s_0 * d_0))

        # Check alternate way of computing x0
        bigx_open = await bigx.open()
        bigx_0_open = int(bigx_open) % 2
        x_0_open = await x_0.open()
        assert x_0_open == bigx_0_open
        assert int(int(r_bigb_open) > int(c)) == int(x_0_open)

        r_0_open = await r_0.open()
        c0_xor_r0 = c0 + r_0 - 2*c0*r_0
        final_val = c0_xor_r0 + x_0 - 2 * (await(c0_xor_r0 * x_0))
        return final_val
