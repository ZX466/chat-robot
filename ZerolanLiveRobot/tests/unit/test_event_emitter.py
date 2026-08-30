import pytest
from unittest.mock import MagicMock

from event.event_emitter import BaseTask, SyncFunc, AsyncCoro, Timer


@pytest.mark.unit
class TestTimer:
    def test_timer_start_stop(self):
        handler = MagicMock()
        timer = Timer(timeout=None, timeout_handler=handler)
        timer.start()
        timer.stop()
        assert timer.elapsed >= 0

    def test_timer_no_timeout_no_thread(self):
        handler = MagicMock()
        timer = Timer(timeout=None, timeout_handler=handler)
        assert not hasattr(timer, '_thread_timer') or timer._thread_timer is None


@pytest.mark.unit
class TestBaseTask:
    def test_task_has_uuid(self):
        def dummy():
            pass
        task = BaseTask(target=dummy)
        assert task.id is not None
        assert len(task.id) > 0

    def test_task_name_defaults_to_id(self):
        def dummy():
            pass
        task = BaseTask(target=dummy)
        assert task.name == task.id

    def test_task_custom_name(self):
        def dummy():
            pass
        task = BaseTask(target=dummy, name="my_task")
        assert task.name == "my_task"

    def test_task_none_target_raises(self):
        with pytest.raises(AssertionError):
            BaseTask(target=None)


@pytest.mark.unit
class TestSyncFunc:
    def test_sync_func_execute(self):
        mock_fn = MagicMock()
        task = SyncFunc(target=mock_fn, timeout=None)
        task.set_args("arg1")
        task.set_kwargs(key="value")
        task.execute()
        mock_fn.assert_called_once_with("arg1", key="value")

    def test_sync_func_catches_exception(self):
        def failing():
            raise ValueError("test error")
        task = SyncFunc(target=failing, timeout=None)
        task.set_args()
        with pytest.raises(ValueError, match="test error"):
            task.execute()
        assert isinstance(task.exception, ValueError)


@pytest.mark.unit
class TestAsyncCoro:
    @pytest.mark.asyncio
    async def test_async_coro_execute(self):
        mock_fn = MagicMock()
        task = AsyncCoro(target=mock_fn, timeout=None)
        task.set_args("arg1")
        task.set_kwargs(key="value")
        await task.execute()
        mock_fn.assert_called_once_with("arg1", key="value")

    @pytest.mark.asyncio
    async def test_async_coro_catches_exception(self):
        async def failing():
            raise ValueError("async error")
        task = AsyncCoro(target=failing, timeout=None)
        task.set_args()
        with pytest.raises(ValueError, match="async error"):
            await task.execute()
        assert isinstance(task.exception, ValueError)
