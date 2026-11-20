"""معالجة ضغطات الأزرار (قوائم الأوامر، شاشة البداية، مركز المالك)."""
from __future__ import annotations

import logging

from telegram import Chat, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import Services, get_services
from zhoo.core.fmt import mention
from zhoo.handlers.views import about_text, audit_text, groups_text, help_main_text, owner_panel_text
from zhoo.systems import botstate, feedback, games, group, locks, protect, punish, social
from zhoo.keyboards.menus import (SECTION_MAP, back_to_start_keyboard, help_main_keyboard,
                                  owner_keyboard, owner_sub_keyboard, section_keyboard, section_text,
                                  start_keyboard)

log = logging.getLogger(__name__)

STALE = T.STALE


async def _edit(msg: Message, text: str, markup: InlineKeyboardMarkup | None) -> None:
    try:
        await msg.edit_text(text, reply_markup=markup)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


class _Query:
    """غلاف يضمن الرد على الضغطة مرة وحدة بالضبط."""

    def __init__(self, raw):
        self.raw = raw
        self.from_user = raw.from_user
        self.answered = False

    async def answer(self, text: str | None = None, show_alert: bool = False) -> None:
        if self.answered:
            return
        self.answered = True
        try:
            await self.raw.answer(text, show_alert=show_alert)
        except BadRequest:  # الضغطة قديمة
            pass


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query is None:
        return
    q = _Query(update.callback_query)
    svc = get_services(context)
    user = q.from_user
    msg = q.raw.message
    if not isinstance(msg, Message):  # رسالة قديمة جداً ما نكدر نعدلها
        await q.answer(STALE, show_alert=True)
        return

    is_dev = svc.perms.is_developer(user.id)
    if not is_dev and not svc.button_limiter.hit(user.id):
        await q.answer(T.SLOW_DOWN)
        return
    if svc.maintenance and not is_dev and not (q.raw.data or "").startswith("c:"):  # التحقق يشتغل دائماً
        await q.answer(T.MAINTENANCE.replace("⌯ ", ""), show_alert=True)
        return

    parts = (q.raw.data or "").split(":")
    kind = parts[0]
    if msg.chat.type != Chat.PRIVATE and kind != "c" and await botstate.is_quiet(svc, msg.chat.id):
        await q.answer(T.BOT_QUIET_ALERT, show_alert=True)
        return
    try:
        if kind == "h" and len(parts) == 3:
            await _help(q, msg, svc, context, parts[1], parts[2])
        elif kind == "s" and len(parts) == 2:
            await _start(q, msg, svc, context, parts[1])
        elif kind == "o" and len(parts) == 2:
            await _owner(q, msg, svc, parts[1])
        elif kind == "g" and len(parts) == 4:
            await protect.on_panel_button(q, msg, svc, context.bot, parts[1], parts[2], parts[3])
        elif kind == "l" and len(parts) == 4:
            await locks.on_panel_button(q, msg, svc, context.bot, parts[1], parts[2], parts[3])
        elif kind == "st" and len(parts) == 4:
            await group.on_settings_button(q, msg, svc, context.bot, parts[1], parts[2], parts[3])
        elif kind == "r" and len(parts) == 2:
            await group.on_rules_button(q, msg, svc)
        elif kind == "sg" and len(parts) == 3:
            await feedback.on_suggestion_button(q, msg, svc, context.bot, parts[1], parts[2])
        elif kind == "cp" and len(parts) == 3:
            await feedback.on_complaint_button(q, msg, svc, context.bot, parts[1])
        elif kind == "gm" and len(parts) == 2:
            await games.on_menu_button(q, msg, svc, context, parts[1])
        elif kind == "rt" and len(parts) == 4:
            await social.on_rating_button(q, msg, svc, context.bot, parts[1], parts[2], parts[3])
        elif kind == "pr" and len(parts) == 4:
            await social.on_pair_button(q, msg, svc, parts[1], parts[2], parts[3])
        elif kind == "c" and len(parts) == 2:
            await protect.on_captcha_button(q, msg, svc, context.bot, parts[1])
        elif kind == "p" and len(parts) == 3:
            await punish.on_undo_button(q, msg, svc, context.bot, parts[1], parts[2])
        else:
            await q.answer(STALE)
    finally:
        # نجاوب دائماً حتى ما يبقى مؤشر التحميل
        await q.answer()


async def _help(q, msg: Message, svc: Services, context, uid_raw: str, section: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    private = msg.chat.type == Chat.PRIVATE
    rank = await svc.perms.rank_of(context.bot, msg.chat.id, q.from_user.id, private=private)
    uid = q.from_user.id

    if section == "close":
        try:
            await msg.delete()
        except BadRequest:
            await _edit(msg, "✖️", None)
        return
    if section == "main":
        await _edit(msg, help_main_text(rank), help_main_keyboard(uid, rank, private=private))
        return

    sec = SECTION_MAP.get(section)
    if sec is None:
        await q.answer(STALE)
        return
    if rank < sec.min_rank:
        await q.answer(T.OWNER_ONLY, show_alert=True)
        return
    await _edit(msg, section_text(sec, registry, rank, private=private), section_keyboard(uid))


async def _start(q, msg: Message, svc: Services, context, action: str) -> None:
    user = q.from_user
    is_dev = svc.perms.is_developer(user.id)
    if msg.chat.type != Chat.PRIVATE:
        await q.answer(STALE)
        return
    if action == "home":
        await _edit(msg, T.START_PRIVATE.format(name=mention(user.id, user.first_name)),
                    start_keyboard(context.bot.username, is_dev))
    elif action == "help":
        rank = await svc.perms.rank_of(context.bot, msg.chat.id, user.id, private=True)
        await _edit(msg, help_main_text(rank), help_main_keyboard(user.id, rank, private=True))
    elif action == "about":
        await _edit(msg, await about_text(svc), back_to_start_keyboard())
    else:
        await q.answer(STALE)


async def _owner(q, msg: Message, svc: Services, action: str) -> None:
    user_id = q.from_user.id
    if not svc.perms.is_developer(user_id) or msg.chat.type != Chat.PRIVATE:
        await q.answer(T.OWNER_ONLY, show_alert=True)
        return
    if action == "main":
        await _edit(msg, await owner_panel_text(svc), owner_keyboard(svc.maintenance))
    elif action == "maint":
        new_state = not svc.maintenance
        await svc.bot_settings.set("maintenance", "1" if new_state else "0")
        await svc.audit.log("maintenance_on" if new_state else "maintenance_off", actor_id=user_id)
        await q.answer(T.MAINTENANCE_ON if new_state else T.MAINTENANCE_OFF)
        await _edit(msg, await owner_panel_text(svc), owner_keyboard(svc.maintenance))
    elif action == "audit":
        await _edit(msg, await audit_text(svc), owner_sub_keyboard())
    elif action == "groups":
        await _edit(msg, await groups_text(svc), owner_sub_keyboard())
    else:
        await q.answer(STALE)
