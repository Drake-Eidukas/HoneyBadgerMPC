from pytest import mark
from random import randint
import asyncio
from honeybadgermpc.field import GF
from honeybadgermpc.comparison import less_than
from honeybadgermpc.mpc import Subgroup
from honeybadgermpc.progs.mixins.share_arithmetic import (
    BeaverMultiply, BeaverMultiplyArrays, InvertShare, InvertShareArray, DivideShares,
    DivideShareArrays, Equality)

STANDARD_ARITHMETIC_MIXINS = [
    BeaverMultiply(),
    BeaverMultiplyArrays(),
    InvertShare(),
    InvertShareArray(),
    DivideShares(),
    DivideShareArrays(),
    Equality()
]

PREPROCESSING = ['rands', 'triples', 'zeros', 'cubes', 'bits']
n, t = 4, 1
k = 10000

FIELD = GF(Subgroup.BLS12_381)

NUM_COMPARISONS = 3


@mark.asyncio
async def test_comparison(test_preprocessing, galois_field, test_runner):
    p = FIELD.modulus
    ranges = [0, p//2**128, p//2**64, p//2**32, p//2**16, p]
    constants = [[randint(ranges[i], ranges[i + 1]) for _ in range(NUM_COMPARISONS)]
                 for i in range(len(ranges) - 1)]

    async def _prog(context):
        for m in range(len(ranges)-1):
            a_shares = [test_preprocessing.elements.get_zero(context) + FIELD(constant)
                        for constant in constants[m]]
            b_shares = [a_shares[0] - FIELD(1), a_shares[1], a_shares[2] + FIELD(1)]
            expected = [False, False, True]

            comparisons = await asyncio.gather(*[less_than(context, a, b)
                                                 for (a, b) in zip(a_shares, b_shares)])
            results = await asyncio.gather(*[c.open() for c in comparisons])

            for (res, ex) in zip(results, expected):
                assert bool(res) == ex

    await test_runner(_prog, n, t, PREPROCESSING, k, STANDARD_ARITHMETIC_MIXINS)
