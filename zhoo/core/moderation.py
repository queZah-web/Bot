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


def _mute_permissions() -> ChatPermissions:
    """كتم = ما يكتب ولا يرسل أي شي، بس يگدر يتفاعل (رياكت)."""
    data = ChatPermissions.no_permissions().to_dict()
    data["can_react_to_messages"] = True
    return ChatPermissions(**data)


def _restrict_permissions() -> ChatPermissions:
    """تقييد = يشوف المجموعة بس: لا كتابة ولا وسائط ولا رياكت ولا أي تفاعل."""
    return ChatPermissions.no_permissions()


async def apply(bot: Bot, chat_id: int, user_id: int, kind: str, until: int | None) -> None:
    if kind == "ban":
        await bot.ban_chat_member(chat_id, user_id, until_date=until)
    elif kind == "kick":
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
    elif kind == "mute":
        await bot.restrict_chat_member(chat_id, user_id, _mute_permissions(),
                                       until_date=until, use_independent_chat_permissions=True)
    elif kind == "restrict":
        await bot.restrict_chat_member(chat_id, user_id, _restrict_permissions(),
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


# ── عقوبات السب التدريجية ───────────────────────────
# كل خطة = خطوات حسب رقم المخالفة (خلال SWEAR_WINDOW). آخر خطوة تتكرر.
# الخطوة: (النوع، المدة بالثواني أو None = دائم). كل الخطوات تمسح الرسالة أولاً.
SWEAR_WINDOW = 7 * 86400
SWEAR_PLANS: dict[str, tuple[tuple[str, int | None], ...]] = {
    "off": (),
    "delete": (("delete", None),),
    "gradual": (("warn", None), ("warn", None), ("mute", 3600), ("mute", 86400),
                ("ban", 86400), ("ban", None)),
    "mute": (("mute", 3600), ("mute", 86400), ("mute", 7 * 86400), ("mute", None)),
    "ban": (("ban", 86400), ("ban", 7 * 86400), ("ban", None)),
}
SWEAR_PLAN_ORDER = ("gradual", "mute", "ban", "delete", "off")
# الوضع العام للقفل ← الخطة لكل مستوى (smart = حسب إعداد كل مستوى)
SWEAR_FIXED_MODES = {"delete": (("delete", None),), "mute": (("mute", None),), "ban": (("ban", None),)}


def swear_step(plan: tuple[tuple[str, int | None], ...], strike: int) -> tuple[str, int | None] | None:
    """الخطوة المناسبة لرقم المخالفة (يبدأ من 1). None = تجاهل."""
    if not plan:
        return None
    return plan[min(max(strike, 1), len(plan)) - 1]
