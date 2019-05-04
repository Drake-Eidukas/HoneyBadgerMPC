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


class TaskProgramRunner(ProgramRunner):
    def __init__(self, n, t, config={}):
        self.N, self.t, self.pid = n, t, 0
        self.config = config
        self.tasks = []
        self.loop = asyncio.get_event_loop()
        self.router = SimpleRouter(self.N)

    def add(self, program, **kwargs):
        for i in range(self.N):
            context = Mpc(
                'sid',
                self.N,
                self.t,
                i,
                self.pid,
                self.router.sends[i],
                self.router.recvs[i],
                program,
                self.config,
                **kwargs,
            )
            self.tasks.append(self.loop.create_task(context._run()))
        self.pid += 1

    async def join(self):
        return await asyncio.gather(*self.tasks)
