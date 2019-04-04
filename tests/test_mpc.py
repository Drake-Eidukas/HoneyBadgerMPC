from pytest import mark
from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.mixins import MixinOpName, Inverter, BeaverTriple


@mark.asyncio
async def test_open_shares(test_preprocessing):

    n, t = 3, 1
    number_of_secrets = 100
    test_preprocessing.generate("zeros", n, t)

    async def _prog(context):
        secrets = []
        for _ in range(number_of_secrets):
            s = await test_preprocessing.elements.get_zero(context).open()
            assert s == 0
            secrets.append(s)
        print('[%d] Finished' % (context.myid,))
        return secrets

    program_runner = TaskProgramRunner(n, t)
    program_runner.add(_prog)
    results = await program_runner.join()
    assert len(results) == n
    assert all(len(secrets) == number_of_secrets for secrets in results)
    assert all(secret == 0 for secrets in results for secret in secrets)


@mark.asyncio
async def test_share_inversion(test_preprocessing):
    n, t = 3, 1
    test_preprocessing.generate("triples", n, t)
    test_preprocessing.generate("rands", n, t)

    async def _prog(context):
        r1 = test_preprocessing.elements.get_rand(context)
        assert await(await(r1 * await(~r1))).open() == 1

    program_runner = TaskProgramRunner(n, t, {
        MixinOpName.MultiplyShare: BeaverTriple.multiply_shares,
        MixinOpName.InvertShare: Inverter.invert_share
    })
    program_runner.add(_prog)
    await (program_runner.join())


@mark.asyncio
async def test_share_array_inversion(test_preprocessing):
    n, t = 3, 1
    test_preprocessing.generate("triples", n, t)
    test_preprocessing.generate("rands", n, t)

    async def _prog(context):
        shares = context.ShareArray(
            [test_preprocessing.elements.get_rand(context) for _ in range(20)])
        inverted_shares = await(~shares)
        product = await(inverted_shares * shares)

        for e in await(product).open():
            assert e == 1

    program_runner = TaskProgramRunner(n, t, {
        MixinOpName.MultiplyShareArray: BeaverTriple.multiply_share_arrays,
        MixinOpName.InvertShareArray: Inverter.invert_share_array
    })
    program_runner.add(_prog)
    await (program_runner.join())


@mark.asyncio
async def test_share_division(test_preprocessing):
    n, t = 3, 1
    test_preprocessing.generate("triples", n, t)
    test_preprocessing.generate("rands", n, t)

    async def _prog(context):
        r1 = test_preprocessing.elements.get_rand(context)
        assert await(await(r1 / r1)).open() == 1

    program_runner = TaskProgramRunner(n, t, {
        MixinOpName.MultiplyShare: BeaverTriple.multiply_shares,
        MixinOpName.InvertShare: Inverter.invert_share
    })
    program_runner.add(_prog)
    await (program_runner.join())


@mark.asyncio
async def test_share_array_division(test_preprocessing):
    n, t = 3, 1
    test_preprocessing.generate("triples", n, t)
    test_preprocessing.generate("rands", n, t)

    async def _prog(context):
        shares = context.ShareArray(
            [test_preprocessing.elements.get_rand(context) for _ in range(20)])

        result = await(shares / shares)
        for e in await(result).open():
            assert e == 1

    program_runner = TaskProgramRunner(n, t, {
        MixinOpName.MultiplyShareArray: BeaverTriple.multiply_share_arrays,
        MixinOpName.InvertShareArray: Inverter.invert_share_array
    })
    program_runner.add(_prog)
    await (program_runner.join())
