"""النسخ الاحتياطي والاستعادة.

- النسخة تنسوي بـ SQLite backup API (متسقة حتى والبوت شغّال)، وتنفحص سلامتها قبل الإرسال.
- نسخة تلقائية يومية تنرسل للمطور بصمت (لأن الاستضافة ممكن تضيع ملفاتها)، ونحتفظ بآخر 7 محلياً.
- الاستعادة: فحص الملف ← تأكيد ← نسخة أمان من الحالية ← تبديل ← إعادة اتصال وترحيلات.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import tempfile
import time
from pathlib import Path

import aiosqlite
from telegram.error import TelegramError

from zhoo.core import texts as T
from zhoo.core.context import Services

log = logging.getLogger(__name__)

KEEP_AUTO = 7
MAX_UPLOAD = 20 * 1024 * 1024
REQUIRED_TABLES = {"schema_version", "groups", "users", "group_members"}


def base_dir(svc: Services) -> Path:
    db_path = str(svc.settings.db_path)
    if db_path == ":memory:" or str(svc.db.path) == ":memory:":
        return Path(tempfile.gettempdir()) / "zhoo-backups-test"
    return Path(db_path).parent


def backup_dir(svc: Services) -> Path:
    d = base_dir(svc) / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def verify_file(path: Path) -> dict | None:
    """يفحص ملف قاعدة بيانات: سليم، ومن زهو. يرجع إحصائيات أو None."""
    try:
        with open(path, "rb") as f:
            if f.read(16) != b"SQLite format 3\x00":
                return None
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return None
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if not REQUIRED_TABLES <= tables:
                return None
            return {
                "groups": conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0],
                "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "version": conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0],
                "size": human_size(path.stat().st_size),
            }
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None


async def make_backup(svc: Services, label: str = "manual") -> tuple[Path, dict]:
    path = backup_dir(svc) / f"zhoo-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{label}.db"
    async with aiosqlite.connect(str(path)) as dst:
        await svc.db.conn.backup(dst)
    stats = await asyncio.to_thread(verify_file, path)
    if stats is None:
        path.unlink(missing_ok=True)
        raise RuntimeError("النسخة فشلت بفحص السلامة")
    if label == "auto":
        autos = sorted(backup_dir(svc).glob("zhoo-*-auto.db"))
        for old in autos[:-KEEP_AUTO]:
            old.unlink(missing_ok=True)
    await svc.audit.log("backup", details={"file": path.name, "label": label})
    return path, stats


async def send_backup(bot, svc: Services, chat_id: int, path: Path, stats: dict, silent: bool = False) -> None:
    with open(path, "rb") as f:
        await bot.send_document(chat_id, f, filename=path.name, caption=T.BACKUP_CAPTION.format(**stats),
                                disable_notification=silent)


def last_backup_age(svc: Services) -> float | None:
    files = sorted(backup_dir(svc).glob("zhoo-*.db"), key=lambda p: p.stat().st_mtime)
    return time.time() - files[-1].stat().st_mtime if files else None


async def daily_job(context) -> None:
    """نسخة تلقائية كل يوم، تنرسل للمطور بصمت."""
    from zhoo.core.context import get_services
    svc = get_services(context)
    try:
        path, stats = await make_backup(svc, "auto")
        await send_backup(context.bot, svc, svc.settings.owner_id, path, stats, silent=True)
    except TelegramError as e:
        log.warning("ما گدرت أدز النسخة التلقائية للمطور: %s", e)
    except Exception:
        log.exception("فشلت النسخة التلقائية")


async def download_upload(bot, svc: Services, file_id: str) -> Path:
    path = base_dir(svc) / "restore-upload.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    tg_file = await bot.get_file(file_id)
    await tg_file.download_to_drive(str(path))
    return path


async def restore(svc: Services, upload: Path) -> Path:
    """يبدل القاعدة الحالية بالملف المرفوع. يرجع مسار نسخة الأمان. يرجّع القديمة إذا فشل."""
    db_path = Path(str(svc.db.path))
    if str(svc.db.path) == ":memory:":
        raise RuntimeError("memory")
    if await asyncio.to_thread(verify_file, upload) is None:  # فحص ثاني هنا حتى لو انطلبت مباشرة
        raise ValueError("invalid backup file")
    pre, _ = await make_backup(svc, "pre-restore")
    svc.restoring = True
    try:
        await svc.db.close()
        for suffix in ("-wal", "-shm"):
            Path(str(db_path) + suffix).unlink(missing_ok=True)
        os.replace(upload, db_path)
        try:
            await svc.db.connect()  # يشغّل أي ترحيل ناقص بالنسخة
            if (await svc.db.fetchval("PRAGMA quick_check")) != "ok":
                raise RuntimeError("quick_check")
        except Exception:
            log.exception("فشلت الاستعادة، دا أرجّع النسخة السابقة")
            await svc.db.close()
            os.replace(pre, db_path)
            await svc.db.connect()
            raise
        await svc.bot_settings.load()
        svc.perms.helpers = {int(x) for x in (svc.bot_settings.get("helpers") or "").split(",") if x.isdigit()}
        svc.reset_caches()
    finally:
        svc.restoring = False
    await svc.audit.log("restore", details={"pre": pre.name})
    return pre
