"""
Cooperative thread termination using an event flag.
Modify from:
    http://www.s1nh.org/post/python-different-ways-to-kill-a-thread/
"""
import threading
import weakref
from typing import List

from loguru import logger


class ThreadKilledError(RuntimeError):
    def __init__(self, *args):
        super().__init__(*args)


class KillableThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, *, daemon=None):
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self._stop_event = threading.Event()
        add_thread(self)

    @property
    def is_killed(self) -> bool:
        return self._stop_event.is_set()

    def request_stop(self):
        """Request the thread to stop cooperatively."""
        self._stop_event.set()

    def should_stop(self) -> bool:
        """Check if the thread has been asked to stop. Call this in your thread loop."""
        return self._stop_event.is_set()

    def join(self, timeout=None):
        if self._stop_event.is_set():
            return
        super().join(timeout)


_all: weakref.WeakSet[KillableThread] = weakref.WeakSet()


def add_thread(t: KillableThread):
    if not isinstance(t, KillableThread):
        raise TypeError(f"Expected KillableThread, got {type(t)}")
    _all.add(t)


def remove_thread(t: KillableThread):
    _all.discard(t)


def kill_all_threads():
    # Snapshot to avoid mutation during iteration
    threads = list(_all)
    for thread in threads:
        try:
            thread.request_stop()
            thread.join(timeout=5)
            logger.debug(f"Thread {thread.name}: stopped")
        except Exception:
            logger.error(f"Failed to stop thread: {thread.name}")
    logger.debug("All threads stopped.")
