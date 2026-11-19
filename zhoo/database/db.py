"""اتصال قاعدة البيانات SQLite مع ترحيلات مرقمة وقفل للكتابة."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Iterable

import aiosqlite

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_MIGRATION_NAME = re.compile(r"^(\d+)_[\w-]+\.sql$")


def now() -> int:
    return int(time.time())


class Database:
    def __init__(self, path: Path | str):
        self.path = path
        self._conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("قاعدة البيانات غير متصلة")
        return self._conn

    async def connect(self) -> None:
        if isinstance(self.path, Path):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA busy_timeout = 5000")
        if str(self.path) != ":memory:":
            await self._conn.execute("PRAGMA journal_mode = WAL")
            await self._conn.execute("PRAGMA synchronous = NORMAL")
        await self._migrate()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _migrate(self) -> None:
        await self.conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            " version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL)"
        )
        await self.conn.commit()
        async with self.conn.execute("SELECT version FROM schema_version") as cur:
            applied = {row[0] for row in await cur.fetchall()}

        files = []
        for f in MIGRATIONS_DIR.iterdir():
            m = _MIGRATION_NAME.match(f.name)
            if m:
                files.append((int(m.group(1)), f))

        for version, file in sorted(files):
            if version in applied:
                continue
            sql = file.read_text(encoding="utf-8")
            script = (
                "BEGIN;\n" + sql +
                f"\nINSERT INTO schema_version (version, applied_at) VALUES ({version}, {now()});\nCOMMIT;"
            )
            try:
                await self.conn.executescript(script)
            except Exception:
                await self.conn.rollback()
                log.exception("فشل تطبيق الترحيل %s", file.name)
                raise
            log.info("تم تطبيق الترحيل %s", file.name)

    # ---- قراءة ----
    async def fetchone(self, sql: str, params: Iterable[Any] = ()) -> aiosqlite.Row | None:
        async with self.conn.execute(sql, tuple(params)) as cur:
            return await cur.fetchone()

    async def fetchall(self, sql: str, params: Iterable[Any] = ()) -> list[aiosqlite.Row]:
        async with self.conn.execute(sql, tuple(params)) as cur:
            return list(await cur.fetchall())

    async def fetchval(self, sql: str, params: Iterable[Any] = (), default: Any = None) -> Any:
        row = await self.fetchone(sql, params)
        return row[0] if row is not None else default

    # ---- كتابة (ذرية ومتسلسلة) ----
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._write_lock:
            try:
                yield self.conn
                await self.conn.commit()
            except Exception:
                await self.conn.rollback()
                raise

    async def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        async with self.transaction() as conn:
            cur = await conn.execute(sql, tuple(params))
            return cur.rowcount

    async def executemany(self, sql: str, rows: Iterable[Iterable[Any]]) -> None:
        async with self.transaction() as conn:
            await conn.executemany(sql, [tuple(r) for r in rows])
