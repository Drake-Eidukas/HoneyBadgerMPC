import asyncio
from pytest import mark
from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.mixins import MixinOpName, DoubleSharing, BeaverTriple
from progs.jubjub import point_shares_on_curve, Jubjub, Point, Ideal
import logging


def test_basic_point_functionality():
    p1 = Point(0, 1)
    curve = p1.curve
    ideal = Ideal(curve)

    assert p1.curve.testPoint(p1.x, p1.y)
    assert 2 * p1 == p1
    assert p1.double() == 2 * p1

    p2 = Point(5, 6846412461894745224441235558443359243034138132682534265960483512729196124138)
    assert p2 + ideal == p2
    assert p1 + p2 == p2
    assert p2.double() == p2 * 2
    assert p2 - p2 == p1

    p3 = Point(10, 9069365299349881324022309154395348339753339814197599672892180073931980134853)
    assert p2 + p3 == Point(31969263762581634541702420136595781625976564652055998641927499388080005620826,
                            31851650165997003853447983973612951129977622378317524209017259746316028027479)
    assert p2 != p3

    assert p3[0] == 10


@mark.asyncio
async def test_point_on_curve(test_preprocessing):
    n, t = 4, 1
    test_preprocessing.generate("rands", n, t)
    test_preprocessing.generate("triples", n, t)
    test_preprocessing.generate("double_shares", n, t)

    async def _prog(context):
        curve = Jubjub(field=context.field)

        xs = context.Share(0)
        ys = context.Share(1)

        assert await point_shares_on_curve(context, curve, xs, ys)

    program_runner = TaskProgramRunner(
        n, t, {MixinOpName.MultiplyShare: BeaverTriple.multiply_shares})
    program_runner.add(_prog)
    await program_runner.join()
