"""BroadcastScheduler 单测：cron 定时播报（§9-9，asyncio 无线程）。

- 命中 cron 时刻触发一次播报（同日不重复）
- 未命中不触发
- enabled=False 不启动
- 调度循环可被取消（lifespan 关闭路径）
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

import pytest

from app.core.broadcast import BroadcastScheduler

NowFn = Callable[[], datetime]
SleepFn = Callable[[float], Awaitable[None]]


class FakeOrchestrator:
    """记录 process_text 调用的最小编排桩（契约：async generator，与真实 Orchestrator 一致）。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def process_text(self, session_id: str, text: str) -> Any:
        self.calls.append(text)
        if False:  # async generator 形态，契约对齐真实 Orchestrator.process_text
            yield


class FakeClock:
    """注入式时钟：拨动 now() 与 sleep()，测试不真实等待。"""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now = self._now + timedelta(seconds=seconds)

    async def sleep(self, seconds: float) -> None:
        self.advance(seconds)
        await asyncio.sleep(0)  # 让出事件循环：使 task.cancel() 在 await 点生效


@pytest.mark.asyncio
async def test_broadcasts_once_when_cron_matches() -> None:
    """cron 命中 → 播报一次；同日再 tick 不重复。"""
    orch = FakeOrchestrator()
    clock = FakeClock(datetime(2026, 8, 31, 9, 0, 0))
    scheduler = BroadcastScheduler(
        orch,
        cron="09:00",
        text="早上好，今天也要元气满满！",
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    await scheduler.tick()
    assert orch.calls == ["早上好，今天也要元气满满！"]

    clock.advance(30)  # 同一日再次 tick
    await scheduler.tick()
    assert orch.calls == ["早上好，今天也要元气满满！"]  # 未重复


@pytest.mark.asyncio
async def test_no_broadcast_when_cron_not_matched() -> None:
    orch = FakeOrchestrator()
    clock = FakeClock(datetime(2026, 8, 31, 10, 0, 0))
    scheduler = BroadcastScheduler(
        orch,
        cron="09:00",
        text="播报",
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    await scheduler.tick()
    assert orch.calls == []


@pytest.mark.asyncio
async def test_broadcasts_again_next_day() -> None:
    """跨日 cron 再次命中 → 重新播报（非同日去重）。"""
    orch = FakeOrchestrator()
    clock = FakeClock(datetime(2026, 8, 31, 9, 0, 0))
    scheduler = BroadcastScheduler(
        orch,
        cron="09:00",
        text="早安",
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    await scheduler.tick()
    clock.advance(24 * 3600)  # 次日 09:00
    await scheduler.tick()
    assert orch.calls == ["早安", "早安"]


@pytest.mark.asyncio
async def test_no_broadcast_when_disabled() -> None:
    orch = FakeOrchestrator()
    clock = FakeClock(datetime(2026, 8, 31, 9, 0, 0))
    scheduler = BroadcastScheduler(
        orch,
        cron="09:00",
        text="播报",
        enabled=False,
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    await scheduler.tick()
    assert orch.calls == []


@pytest.mark.asyncio
async def test_run_loop_broadcasts_and_cancels() -> None:
    """run() 循环推进至命中后播报；cancel 在 await 点生效（lifespan 收尾）。"""
    orch = FakeOrchestrator()
    clock = FakeClock(datetime(2026, 8, 31, 8, 59, 30))
    scheduler = BroadcastScheduler(
        orch,
        cron="09:00",
        text="准点播报",
        tick_interval=30.0,
        now_fn=clock.now,
        sleep_fn=clock.sleep,
    )

    task = asyncio.create_task(scheduler.run())
    # 让事件循环跑若干拍（每 tick 推进 30s），直到命中 09:00 播报
    for _ in range(200):
        if orch.calls:
            break
        await asyncio.sleep(0)
    assert orch.calls == ["准点播报"]

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
