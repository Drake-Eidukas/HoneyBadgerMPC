from abc import abstractmethod, ABC
import asyncio
from honeybadgermpc.mpc import Mpc
from honeybadgermpc.router import SimpleRouter


class ProgramRunner(ABC):
    @abstractmethod
    def add(self, program, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def join(self):
        raise NotImplementedError

    @abstractmethod
    def run(self):
        raise NotImplementedError


class TaskProgramRunner(ProgramRunner):
    """ Runner to set up and run MPC programs
    """

    def __init__(self, n, t, config={}):
        # Number of players for MPC programs
        self.N = n

        # Fault tolerance.
        self.t = t

        self.config = config
        self.loop = asyncio.get_event_loop()

        # Monotonically increasing counter for assigning IDs to programs
        self._pid = 0

        # Handles send and recv
        self._router = SimpleRouter(self.N)

        # Tasks to run in MPC
        self._tasks = []

    def add(self, program, **kwargs):
        """ Adds a given MPC program to be run by the task runner.

        args: 
            program (coroutine): Task to be run in MPC
            kwargs (dict): Key-word arguments to pass to the MPC program
        """
        for i in range(self.N):
            context = Mpc(
                'sid',
                self.N,
                self.t,
                i,
                self._pid,
                self._router,
                program,
                self.config,
                **kwargs,
            )
            self._tasks.append(self.loop.create_task(context._run()))
        self._pid += 1

    async def join(self):
        """ Non-blocking operation to run the tasks until they're complete
        """

        return await asyncio.gather(*self._tasks)

    def run(self):
        """ Blocking operation to run the tasks until they're complete
        """

        return self.loop.run_until_complete(self.join())
