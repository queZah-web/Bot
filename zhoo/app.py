"""بناء تطبيق البوت وربط كل المعالجات."""
from __future__ import annotations

import logging

from telegram import BotCommand, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (Application, ApplicationBuilder, CallbackQueryHandler, ChatMemberHandler,
                          CommandHandler, ContextTypes, Defaults, MessageHandler, filters)

from zhoo import __version__
from zhoo.config import Settings
from zhoo.core.context import Services
from zhoo.database.db import Database
from zhoo.handlers import callbacks, errors, membership, router, start

# استيراد الأنظمة يسجل أوامرها بالسجل المركزي
from zhoo.systems import general, owner, ranks  # noqa: F401

log = logging.getLogger(__name__)

FLUSH_INTERVAL = 60


async def _flush_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.application.bot_data["services"].tracker.flush()


async def _post_init(app: Application) -> None:
    svc: Services = app.bot_data["services"]
    await svc.db.connect()
    await svc.bot_settings.load()
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
    log.info("زهو %s اشتغل باسم @%s", __version__, app.bot.username)


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
    app = (
        ApplicationBuilder()
        .token(settings.token)
        .defaults(defaults)
        .concurrent_updates(16)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    app.bot_data["services"] = Services.build(settings, Database(settings.db_path))

    chats = filters.ChatType.PRIVATE | filters.ChatType.GROUPS
    app.add_handler(CommandHandler("start", start.cmd_start, filters=chats))
    app.add_handler(CommandHandler("help", start.cmd_help, filters=chats))
    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE, router.on_migrate))
    app.add_handler(MessageHandler(filters.UpdateType.MESSAGE & chats & ~filters.COMMAND, router.on_message))
    app.add_handler(CallbackQueryHandler(callbacks.on_callback))
    app.add_handler(ChatMemberHandler(membership.on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(membership.on_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_error_handler(errors.on_error)
    return app


ALLOWED_UPDATES = Update.ALL_TYPES
