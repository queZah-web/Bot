"""نقطة تشغيل زهو — شغّل: python main.py"""
from __future__ import annotations

import asyncio
import sys
import time

if sys.version_info < (3, 10):
    sys.exit("❌ زهو يحتاج Python 3.10 أو أحدث")

from telegram import Bot  # noqa: E402
from telegram.error import InvalidToken, NetworkError  # noqa: E402
from telegram.request import HTTPXRequest  # noqa: E402

from zhoo.app import ALLOWED_UPDATES, build_application  # noqa: E402
from zhoo.config import ConfigError, Settings, load_settings  # noqa: E402
from zhoo.core.logging_setup import setup_logging  # noqa: E402

MAX_ATTEMPTS = 5

NETWORK_HELP = """
❌ ما كدرت أوصل لسيرفر تيليجرام (api.telegram.org)

الأسباب والحلول:
  1) النت ضعيف ← جرب واي فاي أو انتظر شوية
  2) شركة الاتصالات حاجبة سيرفر البوتات ← شغّل VPN وأعد التشغيل
     (تتأكد: افتح بالمتصفح https://api.telegram.org — إذا ما فتح فهو محجوب)
  3) عندك بروكسي ← أضف بملف env.txt سطر:  PROXY_URL=http://IP:PORT
"""


async def _check(settings: Settings) -> str:
    request = HTTPXRequest(connect_timeout=15, read_timeout=20, proxy=settings.proxy_url)
    async with Bot(settings.token, request=request) as bot:
        return bot.username


def check_connection(settings: Settings) -> None:
    """فحص اتصال قبل التشغيل مع إعادة محاولة ورسائل واضحة."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            username = asyncio.run(_check(settings))
            print(f"✅ تم الاتصال بتيليجرام — البوت: @{username}", flush=True)
            return
        except InvalidToken:
            sys.exit("❌ التوكن غلط أو انلغى. انسخه من جديد من @BotFather وحطه بملف env.txt")
        except NetworkError as e:
            if attempt == MAX_ATTEMPTS:
                print(NETWORK_HELP, flush=True)
                sys.exit(1)
            wait = 5 * attempt
            print(f"⚠️ فشل الاتصال ({type(e).__name__}) — محاولة {attempt}/{MAX_ATTEMPTS}، "
                  f"أعيد بعد {wait} ثانية...", flush=True)
            time.sleep(wait)


def main() -> None:
    try:
        settings = load_settings()
    except ConfigError as e:
        sys.exit(f"❌ خطأ بالإعدادات: {e}")

    setup_logging(settings.log_dir, settings.log_level, secrets=[settings.token])
    print("⏳ جاري الاتصال بتيليجرام...", flush=True)
    check_connection(settings)

    asyncio.set_event_loop(asyncio.new_event_loop())  # asyncio.run يسكر حلقته، نبدأ وحدة جديدة
    app = build_application(settings)
    app.run_polling(allowed_updates=ALLOWED_UPDATES, drop_pending_updates=True, bootstrap_retries=5)


if __name__ == "__main__":
    main()
