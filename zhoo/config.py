"""تحميل الإعدادات من متغيرات البيئة أو من ملف .env.

الأسرار (التوكن) لا تُكتب في الكود ولا تُطبع في السجلات.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{30,}$")


class ConfigError(Exception):
    """خطأ في الإعدادات يمنع التشغيل."""


def _load_dotenv(path: Path) -> None:
    """قارئ بسيط لملف .env (بدون مكتبات إضافية). متغيرات البيئة الحقيقية لها الأولوية."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and not os.environ.get(key):
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    owner_id: int
    db_path: Path
    log_dir: Path
    log_level: str = "INFO"
    proxy_url: str | None = field(default=None, repr=False)


def load_settings(env_file: Path | None = None) -> Settings:
    if env_file is not None:
        _load_dotenv(env_file)
    else:
        # env.txt بديل أسهل على الموبايل (الملفات اللي تبدأ بنقطة تنخفي)
        _load_dotenv(ROOT / ".env")
        _load_dotenv(ROOT / "env.txt")

    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise ConfigError("BOT_TOKEN غير موجود. ضعه في ملف .env أو في متغيرات الاستضافة.")
    if not _TOKEN_RE.match(token):
        raise ConfigError("BOT_TOKEN شكله غير صحيح. انسخه كاملاً من @BotFather.")

    owner_raw = os.environ.get("OWNER_ID", "").strip()
    if not owner_raw.isdigit():
        raise ConfigError("OWNER_ID لازم يكون رقم ايدي حسابك (تعرفه من @userinfobot).")

    db_path = Path(os.environ.get("DB_PATH", "data/zhoo.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path

    level = os.environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        level = "INFO"

    proxy = os.environ.get("PROXY_URL", "").strip() or None
    if proxy and not proxy.startswith(("http://", "https://", "socks5://", "socks5h://")):
        raise ConfigError("PROXY_URL لازم يبدأ بـ http:// أو socks5://")

    return Settings(
        proxy_url=proxy,
        token=token,
        owner_id=int(owner_raw),
        db_path=db_path,
        log_dir=ROOT / "logs",
        log_level=level,
    )
