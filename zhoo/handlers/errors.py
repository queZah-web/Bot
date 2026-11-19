"""معالجة الأخطاء المركزية: تسجيل كامل، وتنبيه مختصر للمطور، ولا تفاصيل تقنية للمستخدم."""
from __future__ import annotations

import logging
import time

from telegram import Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import ContextTypes

from zhoo.core import texts as T
from zhoo.core.context import get_services
from zhoo.core.fmt import esc

log = logging.getLogger(__name__)

NOTIFY_EVERY = 60  # ثانية بين كل تنبيه وتنبيه للمطور


def _where(update: object) -> str:
    if isinstance(update, Update):
        chat = update.effective_chat
        user = update.effective_user
        return f"chat={chat.id if chat else '-'} user={user.id if user else '-'}"
    return "-"


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    where = _where(update)

    # أخطاء متوقعة وما تحتاج إزعاج
    if isinstance(err, (TimedOut, NetworkError)) and not isinstance(err, BadRequest):
        log.warning("مشكلة شبكة (%s): %s", where, err)
        return
    if isinstance(err, RetryAfter):
        log.warning("تيليجرام طلب انتظار %s ثانية (%s)", err.retry_after, where)
        return
    if isinstance(err, Forbidden):
        log.info("ممنوع (%s): %s", where, err)
        return

    svc = get_services(context)
    svc.error_count += 1
    log.error("خطأ غير متوقع (%s)", where, exc_info=err)

    now = time.monotonic()
    last = context.application.bot_data.get("_last_error_notice", 0.0)
    if now - last < NOTIFY_EVERY:
        return
    context.application.bot_data["_last_error_notice"] = now
    summary = f"{type(err).__name__}: {err}"[:350]
    try:
        await context.bot.send_message(
            svc.settings.owner_id, T.ERROR_NOTICE.format(error=esc(summary), where=esc(where))
        )
    except Exception:  # noqa: BLE001 — التنبيه نفسه لا يجب أن يسبب خطأ جديد
        pass
