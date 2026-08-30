import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Union

from loguru import logger


class AsyncRunnable(ABC):

    def __init__(self):
        self._activate: bool = False
        self.id: str = str(uuid.uuid4())

    @abstractmethod
    def name(self):
        return self.id

    @abstractmethod
    async def start(self):
        self._activate = True
        add_runnable(self)

    def activate_check(self):
        if not self._activate:
            raise RuntimeError("This runnable object is not activated. Call `start()` first.")

    @abstractmethod
    async def stop(self):
        self._activate = False


class ThreadRunnable(ABC):

    def __init__(self):
        self._activate: bool = False
        self.id: str = str(uuid.uuid4())

    @abstractmethod
    def name(self):
        return self.id

    @abstractmethod
    def start(self):
        self._activate = True
        add_runnable(self)

    def activate_check(self):
        if not self._activate:
            raise RuntimeError("This runnable object is not activated. Call `start()` first.")

    @abstractmethod
    def stop(self):
        self._activate = False


# 所有的可运行组件都应该在调用 `start` 方法的时候被注册在这里
# All runnable components should be registered here when the `start` method is called
_all: Dict[str, Union[AsyncRunnable, ThreadRunnable]] = {}
_ids: List[str] = []


def add_runnable(run: AsyncRunnable | ThreadRunnable):
    _all[run.id] = run
    _ids.append(run.id)
    logger.debug(f"Runnable {run.name()}: {run.id}")


async def stop_all_runnable():
    """
    强制停止所有可运行组件的运行
    Force stop the operation of all runnable components
    """
    global _all, _ids
    ids = list(_ids)
    ids.reverse()

    for run_id in ids:
        run = _all.pop(run_id, None)
        if run is None:
            logger.warning(f"Runnable does not exist: {run_id}")
            continue
        try:
            await run.stop()
        except Exception as e:
            logger.error(f"Failed to stop runnable {run.name()}({run_id}): {e}")
        logger.debug(f"Runnable {run.name()}({run_id}): killed.")
    _ids.clear()
