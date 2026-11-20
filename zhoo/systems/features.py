"""تفعيل وتعطيل الميزات لكل مجموعة: «تفعيل الكت» ، «تعطيل المنشن» ، أو من لوحة «الميزات».

- الأمر المعطّل يرد «معطّل» على الكل، عدا المالك وفوگ (يگدرون يستخدمونه دائماً).
- بعض الميزات مو أوامر (مثل الحماية والردود والاقتباس) — الأنظمة تسأل `enabled()` قبل ما تشتغل.
"""
from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank
from zhoo.repositories.group_settings import DEFAULTS

S = "group"
EDIT_RANK = Rank.MANAGER
VIEW_RANK = Rank.ADMIN
BYPASS_RANK = Rank.OWNER


@dataclass(frozen=True)
class Feature:
    key: str
    name: str
    aliases: tuple[str, ...]
    default: str
    commands: tuple[str, ...] = ()
    setting: str | None = None   # مفتاح موجود من قبل (مثل guard_captcha)

    @property
    def setting_key(self) -> str:
        return self.setting or f"feat_{self.key}"


_PROMOTE = tuple(f"promote_{r}" for r in ("owner", "general_manager", "manager", "supervisor", "admin", "vip"))
_DEMOTE = ("demote",) + tuple(f"demote_{r}" for r in ("owner", "general_manager", "manager", "supervisor",
                                                       "admin", "vip"))

FEATURES: tuple[Feature, ...] = (
    Feature("id", "الايدي", ("الأيدي", "ايدي"), "1", ("id",)),
    Feature("id_photo", "الايدي بالصورة", ("الايدي بالصوره", "الأيدي بالصورة"), "1"),
    Feature("link", "الرابط", (), "1", ("link",)),
    Feature("kickme", "اطردني", (), "1", ("kickme",)),
    Feature("ban", "الحظر", ("الطرد",), "1", ("ban", "kick", "unban")),
    Feature("promote", "الرفع", (), "1", _PROMOTE),
    Feature("demote", "التنزيل", (), "1", _DEMOTE),
    Feature("transfer", "التحويل", (), "1", ("transfer",)),
    Feature("warn", "التحذير", ("الانذار", "الإنذار"), "1", ("warn", "clear_warns")),
    Feature("mention_all", "المنشن", ("النداء", "التاك للكل"), "1", ("mention_all",)),
    Feature("protection", "الحماية", ("الحمايه",), "1"),
    Feature("replies", "الردود", (), "1"),
    Feature("source_replies", "ردود زهو", ("ردود السورس", "ردود البوت"), "1"),
    Feature("azkar", "الأذكار", ("الاذكار",), "0", ("azkar_now",)),
    Feature("fun", "التسلية", ("التسليه",), "1",
            ("fun_love", "fun_beauty", "fun_smart", "fun_kind", "fun_luck_pct", "fun_luck", "fun_choose")),
    Feature("kt", "الكت", ("كت تويت",), "1", ("kt",)),
    Feature("avatar", "افتاري", ("الافتار", "الأفتار"), "1", ("avatar", "their_avatar")),
    Feature("whoadded", "ضافني", (), "1", ("whoadded", "their_adder")),
    Feature("service", "الخدمية", ("الخدميه", "الاوامر الخدميه"), "1", ("time", "date", "calc")),
    Feature("youtube", "اليوتيوب", ("يوتيوب", "يوت"), "1", ("youtube",)),
    Feature("quote", "الاقتباس", ("وضع الاقتباسات", "الاقتباسات", "وضع الاقتباس"), "1"),
    Feature("captcha", "التحقق", (), "0", (), "guard_captcha"),
    Feature("pairs", "الثنائي", ("الثنائيات",), "0", (), "pairs_on"),
)
FEATURE_MAP = {f.key: f for f in FEATURES}
COMMAND_FEATURE = {cmd: f.key for f in FEATURES for cmd in f.commands}
_NAME_INDEX = {normalize(n): f for f in FEATURES for n in (f.name,) + f.aliases}

for _f in FEATURES:  # القيم الافتراضية
    DEFAULTS.setdefault(_f.setting_key, _f.default)


def parse_feature(rest: str) -> Feature | None:
    return _NAME_INDEX.get(normalize(rest))


async def enabled(svc: Services, chat_id: int, key: str) -> bool:
    if chat_id > 0:
        return True
    return (await svc.group_settings.get(chat_id, FEATURE_MAP[key].setting_key)) not in ("0", "")


async def blocked(svc: Services, chat_id: int, command_key: str, rank: Rank) -> bool:
    """هل الأمر معطّل لهذا الشخص؟"""
    key = COMMAND_FEATURE.get(command_key)
    return key is not None and rank < BYPASS_RANK and not await enabled(svc, chat_id, key)


async def set_enabled(svc: Services, chat_id: int, key: str, on: bool, by: int) -> bool:
    """يرجع False إذا كانت أصلاً بنفس الحالة."""
    if await enabled(svc, chat_id, key) == on:
        return False
    f = FEATURE_MAP[key]
    await svc.group_settings.set(chat_id, f.setting_key, "1" if on else "0", by)
    await svc.audit.log("feature", chat_id=chat_id, actor_id=by, details={"key": key, "on": on})
    return True


def _accept(rest: str) -> bool:
    return parse_feature(rest) is not None


async def _toggle(cx: CommandContext, on: bool) -> None:
    f = parse_feature(cx.raw_args) if cx.raw_args.strip() else None
    if f is None:
        await cx.reply(T.FEATURES_HINT)
        return
    changed = await set_enabled(cx.services, cx.chat.id, f.key, on, cx.user.id)
    if not changed:
        await cx.reply((T.FEATURE_ALREADY_ON if on else T.FEATURE_ALREADY_OFF).format(what=f.name))
    else:
        await cx.reply((T.FEATURE_ON if on else T.FEATURE_OFF_DONE).format(what=f.name))


async def _enable(cx): await _toggle(cx, True)       # noqa: E704
async def _disable(cx): await _toggle(cx, False)     # noqa: E704


registry.command("feature_on", ("تفعيل",), section=S, min_rank=EDIT_RANK, accept=_accept, usage="اسم الميزة",
                 description="يشغّل ميزة، مثل: تفعيل الكت", order=40)(_enable)
registry.command("feature_off", ("تعطيل",), section=S, min_rank=EDIT_RANK, accept=_accept, usage="اسم الميزة",
                 description="يطفي ميزة، مثل: تعطيل المنشن", order=41)(_disable)


# ── لوحة الميزات ────────────────────────────────────
async def panel_keyboard(svc: Services, chat_id: int, uid: int) -> InlineKeyboardMarkup:
    buttons = []
    for f in FEATURES:
        mark = "✅" if await enabled(svc, chat_id, f.key) else "▫️"
        buttons.append(InlineKeyboardButton(f"{mark} {f.name}", callback_data=f"ft:{uid}:{f.key}"))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(T.BTN_CLOSE, callback_data=f"ft:{uid}:x")])
    return InlineKeyboardMarkup(rows)


@registry.command("features_panel", ("الميزات", "المميزات"), section=S, min_rank=VIEW_RANK,
                  description="لوحة تفعيل وتعطيل الميزات بالأزرار", order=39)
async def cmd_panel(cx: CommandContext) -> None:
    await cx.reply(T.FEATURES_PANEL, reply_markup=await panel_keyboard(cx.services, cx.chat.id, cx.user.id))


async def on_button(q, msg: Message, svc: Services, bot, uid_raw: str, key: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.HELP_NOT_YOURS, show_alert=True)
        return
    if key == "x":
        try:
            await msg.delete()
        except TelegramError:
            pass
        return
    if key not in FEATURE_MAP:
        await q.answer()
        return
    if await svc.perms.rank_of(bot, msg.chat.id, q.from_user.id) < EDIT_RANK:
        await q.answer(T.SETTINGS_NEED_MANAGER, show_alert=True)
        return
    on = not await enabled(svc, msg.chat.id, key)
    await set_enabled(svc, msg.chat.id, key, on, q.from_user.id)
    await q.answer(("✅ " if on else "▫️ ") + FEATURE_MAP[key].name)
    try:
        await msg.edit_reply_markup(reply_markup=await panel_keyboard(svc, msg.chat.id, q.from_user.id))
    except BadRequest:
        pass
