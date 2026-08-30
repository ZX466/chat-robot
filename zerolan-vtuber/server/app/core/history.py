"""会话历史：内存 + SQLite（aiosqlite）落盘，仅存聊天记录。

骨架为最小可运行实现；数据层由 opencode 深化并评审。
"""

from pathlib import Path

import aiosqlite


class History:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

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

    async def add(self, session_id: str, role: str, content: str) -> None:
        assert self._conn is not None
        await self._conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        await self._conn.commit()

    async def recent(self, session_id: str, limit: int = 20) -> list[dict[str, str]]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ?"
            " ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows][::-1]

    async def clear(self, session_id: str | None = None) -> None:
        assert self._conn is not None
        if session_id is None:
            await self._conn.execute("DELETE FROM messages")
        else:
            await self._conn.execute(
                "DELETE FROM messages WHERE session_id = ?", (session_id,)
            )
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
