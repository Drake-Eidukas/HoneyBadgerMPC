import asyncio
import logging

from honeybadgermpc.mpc import TaskProgramRunner
from honeybadgermpc.preprocessing import PreProcessedElements, PreProcessingConstants, wait_for_preprocessing, preprocessing_done

from .jubjub import Point, Field, Jubjub

# Diffie-Hellman Key-Exchange
# Link: https://en.wikipedia.org/wiki/Diffie%E2%80%93Hellman_key_exchange#Operation_with_more_than_two_parties
# We'll be implementing the divide-and-conquer approach to n-party key exchange.
# Quick example for the case where n=2^3:
# A, B, C, and D each perform an exponentiation, giving g^abcd, which is sent to E, F, G, and H, and vice versa.
# A, B each perform an exponentiation, giving g^efghab, which is sent to C, D
# A performs exponentiation, giving g^efghcda, which is sent to B
# A performs one final exponentiation, giving g^efghcdba
# If the following pattern is applied throughout, each member performs i+1 exponentiations (given n = 2^i)
#
# At first, we'll just be implementing the circular method for simplicity.


async def async_exchanging_in_processes(peers, n, t, k, run_id, node_id):
    logging.info('peers: ' + str(peers))
    logging.info('Peer information:')
    for peer in peers:
        logging.info(f"Peer {peer}: {peers[peer]}")
    logging.info('n: ' + str(n))
    logging.info('t: ' + str(t))
    logging.info('k: ' + str(k))
    logging.info('run_id: ' + str(run_id))
    logging.info('node_id: ' + str(node_id))

    task_runner = TaskProgramRunner(n, t)

    return True


async def generate_shared_key(context):
    if context.myid == 0:
        logging.info(f"context: {str(context)}")
        logging.info(f"context.sid: {context.sid}")
        logging.info(f"context.myid: {context.myid}")


def _preprocess(config):
    if config.skip_preprocessing:
        logging.info('skipping preprocessing')
    else:
        logging.info('preprocessing')


def _cleanup_preprocessing():
    logging.info('cleaning up prior preprocessing')


def _create_asyncio_loop():
    """Creates asyncio event loop for use in MPC application
    """

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()

    def handle_async_exception(loop, ctx):
        logging.info('handle_async_exception:')
        if 'exception' in ctx:
            logging.info(f"exc: {repr(ctx['exception'])}")
        else:
            logging.info(f'ctx: {ctx}')
        logging.info(f"msg: {ctx['message']}")

    loop.set_exception_handler(handle_async_exception)
    loop.set_debug(True)

    return loop


if __name__ == "__main__":
    from honeybadgermpc.config import HbmpcConfig

    # initial config values
    run_id = HbmpcConfig.extras['run_id']
    k = int(HbmpcConfig.extras['k'])

    # setting up asyncio
    loop = _create_asyncio_loop()

    # Clean up preprocessing from last run
    _cleanup_preprocessing()

    try:
        # Preprocess elements for computation
        _preprocess(HbmpcConfig)

        program_runner = TaskProgramRunner(
            HbmpcConfig.N, HbmpcConfig.t, {'g': Point(0, 1)})
        program_runner.add(generate_shared_key)
        loop.run_until_complete(program_runner.join())

        # loop.run_until_complete(
        #     async_exchanging_in_processes(
        #         HbmpcConfig.peers,
        #         HbmpcConfig.N,
        #         HbmpcConfig.t,
        #         k,
        #         run_id,
        #         HbmpcConfig.my_id
        #     )
        # )
    finally:
        loop.close()
