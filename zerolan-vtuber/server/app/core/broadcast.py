"""定时播报调度器（§9-9）：asyncio 循环按 cron（HH:MM）触发播报。

- 无线程：仅 asyncio sleep + tick 检查（§3 红线）。
- 触发时调用 orchestrator.process_text("broadcast", text)，输出事件经
  output_callback 广播到全部 WS 连接（复用现有 play_speech/字幕链路）。
- 同日不重复：记录最近触发日期，跨日允许再次命中。
- run() 可被 cancel（lifespan 关闭路径 await asyncio.CancelledError）。
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

from loguru import logger

from app.core.orchestrator import Orchestrator

_TICK_INTERVAL = 30.0  # 秒：cron 粒度到分钟，30s 轮询足够


class BroadcastScheduler:
    def __init__(
        self,
        orchestrator: Orchestrator,
        *,
        cron: str | None,
        text: str,
        enabled: bool = True,
        tick_interval: float = _TICK_INTERVAL,
        now_fn: Callable[[], datetime] = datetime.now,
        sleep_fn: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._orchestrator = orchestrator
        self._cron = cron
        self._text = text
        self._enabled = enabled
        self._tick_interval = tick_interval
        self._now_fn = now_fn
        self._sleep_fn = sleep_fn
        self._last_date: str | None = None

    async def tick(self) -> None:
        """单次检查：命中 cron 且非同日已播 → 触发一次播报。"""
        if not self._enabled or not self._cron:
            return
        now = self._now_fn()
        if now.strftime("%H:%M") != self._cron:
            return
        today = now.strftime("%Y-%m-%d")
        if today == self._last_date:
            return  # 同日已播，去重
        self._last_date = today
        logger.info("broadcast triggered at {}", now.isoformat(timespec="seconds"))
        async for _evt in self._orchestrator.process_text("broadcast", self._text):
            pass  # 输出事件经 output_callback 广播（WSHub 已注册）

    async def run(self) -> None:
        """调度主循环：tick + sleep 循环，支持 cancel（lifespan 关闭）。"""
        try:
            while True:
                await self.tick()
                await self._sleep_fn(self._tick_interval)
        except asyncio.CancelledError:
            logger.info("broadcast scheduler cancelled")
            raise
