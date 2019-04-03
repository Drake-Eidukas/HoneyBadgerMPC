import asyncio
from pytest import mark, raises
from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.mixins import MixinOpName, DoubleSharing, BeaverTriple
from progs.jubjub import Jubjub, SharedPoint, Point, Ideal
import logging


def test_basic_point_functionality():
    p1 = Point(0, 1)
    curve = p1.curve
    ideal = Ideal(curve)

    assert curve.contains_point(p1)
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
async def test_contains_shared_point(test_preprocessing):
    n, t = 4, 1
    test_preprocessing.generate("rands", n, t)
    test_preprocessing.generate("triples", n, t)
    test_preprocessing.generate("double_shares", n, t)
    curve = Jubjub()

    async def _prog(context):
        p1 = await(SharedPoint.create(context, context.Share(0), context.Share(1)))
        assert await(curve.contains_shared_point(context, p1))

        with raises(Exception) as e_info:
            await(SharedPoint.create(context, context.Share(0), context.Share(2)))
        assert ('Could not initialize Point' in str(e_info.value))

    program_runner = TaskProgramRunner(
        n, t, {MixinOpName.MultiplyShare: BeaverTriple.multiply_shares})
    program_runner.add(_prog)
    await program_runner.join()
