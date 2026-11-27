"""بناء تطبيق البوت وربط كل المعالجات."""
from __future__ import annotations

import logging
from datetime import time as dtime

from telegram import BotCommand, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (Application, ApplicationBuilder, CallbackQueryHandler, ChatMemberHandler,
                          CommandHandler, ContextTypes, Defaults, MessageHandler,
                          MessageReactionHandler, filters)

from telegram.request import HTTPXRequest

from zhoo import __version__
from zhoo.config import Settings
from zhoo.core.safebot import SafeBot
from zhoo.core.context import Services
from zhoo.database.db import Database
from zhoo.handlers import callbacks, errors, membership, router, start

# استيراد الأنظمة يسجل أوامرها بالسجل المركزي
from zhoo.systems import (aliases, backup, channels, chatinfo, cleanup, inspect, media, quicksetup, suspect, watchdog, botstate, general, group, locks, owner, protect, punish, punish_lists, guardian, logchannel,  # noqa: F401
                          ranks, reports, features, extras, youtube, ai,
                          bank, economy, feedback, game_pics, games, market, space, dims, trade, levels, replies, social, swear)

log = logging.getLogger(__name__)

FLUSH_INTERVAL = 60


async def _flush_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    svc = context.application.bot_data["services"]
    await svc.tracker.flush()
    await svc.punishments.expire()  # العقوبات المؤقتة المنتهية (تيليجرام يرفعها بنفسه)
    await protect.sweep_captcha(context)  # طرد اللي ما تحققوا بالوقت
    await svc.swear_logs.prune()  # سجل السب يبقى 30 يوم بس
    await svc.levels.prune_daily()
    await guardian.expire_warnings(svc)  # التحذيرات القديمة (إذا المجموعة محددة مدة)
    await economy.prune(svc)  # المهام القديمة  # الخبرة اليومية تبقى 40 يوم (للترتيب الأسبوعي والشهري)


async def _post_init(app: Application) -> None:
    svc: Services = app.bot_data["services"]
    await svc.db.connect()
    await svc.bot_settings.load()
    svc.perms.helpers = {int(x) for x in (svc.bot_settings.get("helpers") or "").split(",") if x.isdigit()}
    try:
        await app.bot.set_my_commands([
            BotCommand("start", "بدء زهو"),
            BotCommand("help", "قائمة الأوامر"),
        ])
    except TelegramError as e:
        log.warning("تعذر ضبط قائمة الأوامر: %s", e)
    if app.job_queue is not None:
        app.job_queue.run_repeating(_flush_job, interval=FLUSH_INTERVAL, first=FLUSH_INTERVAL,
                                    name="flush_counts")
        # نسخة احتياطية تلقائية كل يوم (03:17 UTC) وتقرير أسبوعي كل أحد (09:13 UTC)
        app.job_queue.run_daily(backup.daily_job, time=dtime(3, 17), name="daily_backup")
        app.job_queue.run_daily(reports.weekly_job, time=dtime(9, 13), days=(0,), name="weekly_report")
        app.job_queue.run_repeating(extras.azkar_job, interval=3 * 3600, first=600, name="azkar")
        app.job_queue.run_repeating(guardian.night_job, interval=60, first=30, name="night_mode")
    # قناة السجل: كل عملية مهمة تنرسل لقناة الإدارة
    svc.audit.listeners.append(lambda *a: logchannel.on_audit(app.bot, svc, *a))
    await _notify_started(app, svc)
    log.info("زهو %s اشتغل باسم @%s", __version__, app.bot.username)


async def _notify_started(app: Application, svc: Services) -> None:
    """رسالة للمطور: زهو اشتغلت، وإذا القاعدة فارغة (يمكن الاستضافة مسحتها) تنبيه للاستعادة."""
    from zhoo.core import texts as T
    groups = await svc.groups.count_active()
    text = T.STARTED.format(version=__version__, groups=groups)
    if groups == 0:
        text += "\n" + T.STARTED_EMPTY_DB
    try:
        await app.bot.send_message(svc.settings.owner_id, text, disable_notification=groups > 0)
    except TelegramError as e:
        log.info("ما گدرت أبلغ المطور بالتشغيل: %s", e)


async def _post_shutdown(app: Application) -> None:
    svc: Services = app.bot_data["services"]
    try:
        await svc.tracker.flush()
    finally:
        await svc.db.close()
    log.info("زهو توقف بأمان")


def build_application(settings: Settings) -> Application:
    defaults = Defaults(parse_mode=ParseMode.HTML,
                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    # مهل أطول حتى يتحمل نت الموبايل البطيء
    request = HTTPXRequest(connection_pool_size=256, connect_timeout=20, read_timeout=30, write_timeout=30,
                           pool_timeout=10, proxy=settings.proxy_url)
    updates_request = HTTPXRequest(connect_timeout=20, read_timeout=40, proxy=settings.proxy_url)
    # SafeBot: كل نص طالع من زهو ينفحص ويتغطى أي سب بيه
    bot = SafeBot(settings.token, defaults=defaults, request=request, get_updates_request=updates_request)
    app = (
        ApplicationBuilder()
        .bot(bot)
        .concurrent_updates(32)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    app.bot_data["services"] = Services.build(settings, Database(settings.db_path))

    chats = filters.ChatType.PRIVATE | filters.ChatType.GROUPS
    app.add_handler(CommandHandler("start", start.cmd_start, filters=chats))
    app.add_handler(CommandHandler("help", start.cmd_help, filters=chats))
    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, router.on_migrate))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS & filters.ChatType.GROUPS,
                                   protect.on_new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER & filters.ChatType.GROUPS,
                                   group.on_left_member))
    app.add_handler(MessageHandler(filters.UpdateType.MESSAGE & chats & ~filters.COMMAND, router.on_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE & filters.ChatType.GROUPS, locks.on_edited))
    app.add_handler(CallbackQueryHandler(callbacks.on_callback))
    app.add_handler(MessageReactionHandler(locks.on_reaction))
    app.add_handler(ChatMemberHandler(membership.on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(membership.on_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_error_handler(errors.on_error)
    return app


ALLOWED_UPDATES = Update.ALL_TYPES
