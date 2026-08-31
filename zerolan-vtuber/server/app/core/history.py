"""会话历史：内存 + SQLite（aiosqlite）落盘，仅存聊天记录。

P0-1 优化：批量写（延迟 commit）+ recent() TTL 30s 内存缓存，减少事件循环阻塞。
"""

import time
from pathlib import Path

import aiosqlite

_BATCH = 10  # 每 N 条批量 commit 一次
_TTL = 30.0  # recent() 内存缓存秒数


class History:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._pending: list[tuple[str, str, str]] = []
        self._cache: dict[str, tuple[float, list[dict[str, str]]]] = {}

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " session_id TEXT NOT NULL,"
            " role TEXT NOT NULL,"
            " content TEXT NOT NULL,"
            " created_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ")"
        )
        await self._conn.commit()

    async def _flush(self) -> None:
        """批量落盘待写消息（commit 归并，非每条一事务）。"""
        if not self._pending:
            return
        assert self._conn is not None
        await self._conn.executemany(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            self._pending,
        )
        await self._conn.commit()
        self._pending.clear()

    async def add(self, session_id: str, role: str, content: str) -> None:
        self._pending.append((session_id, role, content))
        self._cache.pop(session_id, None)  # 写入即失效缓存
        if len(self._pending) >= _BATCH:
            await self._flush()

    async def recent(self, session_id: str, limit: int = 20) -> list[dict[str, str]]:
        await self._flush()  # 先落盘保证可见
        cached = self._cache.get(session_id)
        now = time.monotonic()
        if cached is not None and now - cached[0] < _TTL:
            return cached[1][:limit]
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        result = [{"role": r[0], "content": r[1]} for r in rows][::-1]
        self._cache[session_id] = (now, result)
        return result

    async def clear(self, session_id: str | None = None) -> None:
        assert self._conn is not None
        if session_id is None:
            self._pending.clear()
            await self._conn.execute("DELETE FROM messages")
            self._cache.clear()
        else:
            self._pending = [p for p in self._pending if p[0] != session_id]
            await self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            self._cache.pop(session_id, None)
        await self._conn.commit()

    async def close(self) -> None:
        await self._flush()
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
