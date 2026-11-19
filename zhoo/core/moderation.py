"""القرار المركزي للعقوبات + تنفيذها الفعلي على تيليجرام.

أي أمر عقوبة يمر من هنا فقط، حتى تبقى القواعد بمكان واحد.
"""
from __future__ import annotations

from telegram import Bot, ChatPermissions

from zhoo.core.ranks import PROTECTED, Rank

KIND_NAMES = {"ban": "حظر", "kick": "طرد", "mute": "كتم", "restrict": "تقييد", "warn": "تحذير"}
KIND_EMOJI = {"ban": "🚫", "kick": "👋", "mute": "🔇", "restrict": "⛓", "warn": "⚠️"}
WARN_ACTIONS = {"mute": "كتم", "kick": "طرد", "ban": "حظر"}


class PunishDecision:
    OK = "ok"
    SELF = "self"
    BOT_SELF = "bot_self"
    PROTECTED = "protected"
    HIGHER = "higher"
    TG_ADMIN = "tg_admin"
    OTHER_BOT = "other_bot"


def check_punish(actor: Rank, target_effective: Rank, target_floor: Rank, kind: str, *,
                 is_self: bool, is_this_bot: bool, target_is_bot: bool) -> str:
    if is_this_bot:
        return PunishDecision.BOT_SELF
    if is_self:
        return PunishDecision.SELF
    if target_effective in PROTECTED:
        return PunishDecision.PROTECTED
    if target_effective >= actor:
        return PunishDecision.HIGHER
    if target_floor >= Rank.ADMIN:  # مشرف تيليجرام: تيليجرام نفسه يرفض تقييده
        return PunishDecision.TG_ADMIN
    if target_is_bot and kind in ("mute", "restrict", "warn"):
        return PunishDecision.OTHER_BOT
    return PunishDecision.OK


def _text_only() -> ChatPermissions:
    """تقييد = يكتب نص فقط، بدون وسائط أو روابط أو ملصقات."""
    data = ChatPermissions.no_permissions().to_dict()
    data["can_send_messages"] = True
    return ChatPermissions(**data)


async def apply(bot: Bot, chat_id: int, user_id: int, kind: str, until: int | None) -> None:
    if kind == "ban":
        await bot.ban_chat_member(chat_id, user_id, until_date=until)
    elif kind == "kick":
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    elif kind == "mute":
        await bot.restrict_chat_member(chat_id, user_id, ChatPermissions.no_permissions(),
                                       until_date=until, use_independent_chat_permissions=True)
    elif kind == "restrict":
        await bot.restrict_chat_member(chat_id, user_id, _text_only(),
                                       until_date=until, use_independent_chat_permissions=True)
    else:
        raise ValueError(kind)


async def lift(bot: Bot, chat_id: int, user_id: int, kind: str) -> None:
    if kind == "ban":
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    elif kind in ("mute", "restrict"):
        chat = await bot.get_chat(chat_id)
        perms = chat.permissions or ChatPermissions.all_permissions()
        await bot.restrict_chat_member(chat_id, user_id, perms, use_independent_chat_permissions=True)
    else:
        raise ValueError(kind)
