"""/start و /help"""
from __future__ import annotations

from telegram import Chat, Update
from telegram.ext import ContextTypes

from zhoo.core import texts as T
from zhoo.core.context import get_services
from zhoo.core.fmt import mention
from zhoo.handlers.views import help_main_text
from zhoo.keyboards.menus import help_main_keyboard, start_keyboard


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None or user.is_bot:
        return
    svc = get_services(context)
    await svc.tracker.track_user(user)
    if svc.maintenance and not svc.perms.is_developer(user.id):
        await msg.reply_text(T.MAINTENANCE)
        return
    if chat.type == Chat.PRIVATE:
        await svc.users.set_started(user.id, True)  # حتى توصله الإذاعة
        await msg.reply_text(
            T.START_PRIVATE.format(name=mention(user.id, user.first_name)),
            reply_markup=start_keyboard(context.bot.username, svc.perms.is_staff(user.id)),
        )
    else:
        await msg.reply_text(T.START_GROUP)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if msg is None or chat is None or user is None or user.is_bot:
        return
    svc = get_services(context)
    if svc.maintenance and not svc.perms.is_developer(user.id):
        await msg.reply_text(T.MAINTENANCE)
        return
    private = chat.type == Chat.PRIVATE
    rank = await svc.perms.rank_of(context.bot, chat.id, user.id, private=private)
    await msg.reply_text(help_main_text(rank), reply_markup=help_main_keyboard(user.id, rank, private=private))
