"""«الاعداد السريع»: قائمة فحص للمجموعة + زر واحد يطبّق الإعدادات الموصى بها.

يسهّل البداية: المالك يشوف شنو ناقص (صلاحيات زهو، الحماية، قفل السب، الترحيب، القوانين، الرابط)
وبضغطة وحدة: حماية متوسطة + قفل السب بالإنذار + تشغيل الترحيب.
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.ranks import Rank

S = "group"
EDIT_RANK = Rank.MANAGER
RECOMMENDED = {"guard": "medium", "swear": "warn"}


async def checklist(svc: Services, bot, chat_id: int, uid: int) -> tuple[str, InlineKeyboardMarkup]:
    from zhoo.systems import protect, swear
    ok, bad = "✅", "⚠️"
    rights = await svc.perms.bot_rights(bot, chat_id)
    if rights is None:
        bot_line = T.QS_BOT.format(mark=bad, state=T.GROUP_BOT_NOT_ADMIN)
    else:
        lacking = [n for a, n in T.BOT_RIGHT_NAMES.items() if not getattr(rights, a, False)]
        bot_line = T.QS_BOT.format(mark=bad if lacking else ok,
                                   state=T.GROUP_RIGHTS_MISSING.format(names="، ".join(lacking))
                                   if lacking else T.GROUP_RIGHTS_FULL)
    lvl = protect.current_level(await protect.guards_state(svc, chat_id))
    mode = await swear.get_mode(svc, chat_id)
    g = svc.group_settings
    welcome = await g.get(chat_id, "welcome_on") == "1"
    rules = bool(await g.get(chat_id, "rules"))
    link = bool(await g.get(chat_id, "invite_link"))
    lines = [
        bot_line,
        T.QS_GUARD.format(mark=ok if lvl in ("medium", "strict") else bad,
                          state=T.GUARD_LEVELS[lvl] if lvl else T.GUARD_CUSTOM),
        T.QS_SWEAR.format(mark=ok if mode != "off" else bad, state=T.SWEAR_MODES[mode]),
        T.QS_WELCOME.format(mark=ok if welcome else bad, state=T.QS_ON if welcome else T.QS_OFF),
        T.QS_RULES.format(mark=ok if rules else bad, state=T.QS_SET if rules else T.QS_UNSET),
        T.QS_LINK.format(mark=ok if link else bad, state=T.QS_SET if link else T.QS_UNSET),
    ]
    text = T.QS_PANEL.format(items="\n".join(lines))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T.QS_BTN_APPLY, callback_data=f"qs:{uid}:a")],
        [InlineKeyboardButton(T.BTN_CLOSE, callback_data=f"qs:{uid}:x")],
    ])
    return text, kb


async def apply_recommended(svc: Services, chat_id: int, by: int) -> None:
    from zhoo.systems import protect, swear
    await protect._apply_level(svc, chat_id, RECOMMENDED["guard"], by)
    await swear.set_mode(svc, chat_id, RECOMMENDED["swear"], by)
    await svc.group_settings.set(chat_id, "welcome_on", "1", by)
    await svc.audit.log("quick_setup", chat_id=chat_id, actor_id=by)


@registry.command("quick_setup", ("الاعداد السريع", "الإعداد السريع", "تهيئة زهو", "تجهيز المجموعه"), section=S,
                  min_rank=EDIT_RANK, order=0,
                  description="قائمة فحص للمجموعة + زر واحد يطبّق الإعدادات الموصى بها")
async def cmd_quick_setup(cx: CommandContext) -> None:
    text, kb = await checklist(cx.services, cx.bot, cx.chat.id, cx.user.id)
    await cx.reply(text, reply_markup=kb)


async def on_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    if action == "x":
        try:
            await msg.delete()
        except TelegramError:
            pass
        return
    if action != "a":
        await q.answer()
        return
    if await svc.perms.rank_of(bot, msg.chat.id, q.from_user.id) < EDIT_RANK:
        await q.answer(T.SETTINGS_NEED_MANAGER, show_alert=True)
        return
    await apply_recommended(svc, msg.chat.id, q.from_user.id)
    await q.answer(T.QS_APPLIED, show_alert=True)
    text, kb = await checklist(svc, bot, msg.chat.id, q.from_user.id)
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass
