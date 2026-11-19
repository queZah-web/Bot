"""نقطة تشغيل زهو — شغّل: python main.py"""
from __future__ import annotations

import sys

if sys.version_info < (3, 10):
    sys.exit("❌ زهو يحتاج Python 3.10 أو أحدث")

from zhoo.app import ALLOWED_UPDATES, build_application  # noqa: E402
from zhoo.config import ConfigError, load_settings  # noqa: E402
from zhoo.core.logging_setup import setup_logging  # noqa: E402


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as e:
        sys.exit(f"❌ خطأ بالإعدادات: {e}")

    setup_logging(settings.log_dir, settings.log_level, secrets=[settings.token])
    app = build_application(settings)
    app.run_polling(allowed_updates=ALLOWED_UPDATES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
