"""إعداد السجلات مع إخفاء التوكن تلقائياً من أي سطر يُكتب."""
from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

# أي شيء يشبه توكن بوت يُخفى، حتى لو لم يكن التوكن الحالي
_TOKEN_PATTERN = re.compile(r"\d{5,}:[A-Za-z0-9_-]{30,}|sk-ant-[A-Za-z0-9_-]{10,}")


class RedactingFormatter(logging.Formatter):
    def __init__(self, fmt: str, secrets: list[str]):
        super().__init__(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        self._secrets = [s for s in secrets if s]

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        for secret in self._secrets:
            text = text.replace(secret, "***")
        return _TOKEN_PATTERN.sub("***TOKEN***", text)


def setup_logging(log_dir: Path, level: str, secrets: list[str]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = RedactingFormatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", secrets)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_dir / "zhoo.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)

    # httpx يكتب روابط فيها التوكن، نخليه على التحذيرات فقط
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
