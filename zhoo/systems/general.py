"""الأوامر العامة: الأوامر، ايدي، معلوماتي، رتبتي، نشاطي..."""
from __future__ import annotations

import random
import re

from telegram.error import TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext
from zhoo.core.fmt import activity_level, esc, mention, username_text
from zhoo.core.ranks import Rank, rank_label
from zhoo.core.targets import Target, TargetError, resolve_target
from zhoo.handlers.views import about_text, help_main_text
from zhoo.keyboards.menus import help_main_keyboard

S = "general"
TOP_ACTIVE_LIMIT = 10
BAR_WIDTH = 10
_last_zhoo: dict[int, str] = {}   # آخر رد لـ«زهو» بكل مجموعة (حتى ما يتكرر)


async def reply_target_error(cx: CommandContext, err: TargetError, example: str) -> None:
    if err.reason == "none":
        await cx.reply(T.NEED_TARGET.format(example=esc(example)))
    elif err.reason == "channel":
        await cx.reply(T.TARGET_IS_CHANNEL)
    else:
        await cx.reply(T.TARGET_NOT_FOUND)


async def optional_target(cx: CommandContext) -> Target | None:
    """الهدف إذا انذكر (رد/يوزر/ايدي)، وإلا None = نفس الشخص."""
    if cx.message.reply_to_message is None and not cx.args and not any(
        e.type == "text_mention" for e in (cx.message.entities or ())
    ):
        return None
    return await resolve_target(cx)


@registry.command("help", ("الاوامر", "الأوامر", "اوامر", "مساعده", "مساعدة"), section=S,
                  description="يفتح قائمة الأوامر بالأزرار", where="any", order=0)
async def cmd_help(cx: CommandContext) -> None:
    await cx.reply(help_main_text(cx.rank),
                   reply_markup=help_main_keyboard(cx.user.id, cx.rank, private=cx.is_private))


@registry.command("id", ("ايدي", "ا", "id", "معلوماتي"), section=S, usage="اختياري: بالرد",
                  description="يعرض الايدي والمعلومات مع صورة الحساب", order=1, args="target")
async def cmd_id(cx: CommandContext) -> None:
    try:
        target = await optional_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "ايدي @username")
        return

    if target is None:
        user_id, name, username = cx.user.id, cx.user.full_name, cx.user.username
        rank = cx.rank
    else:
        user_id, name, username = target.user_id, target.name, target.username
        rank = await cx.services.perms.rank_of(cx.bot, cx.chat.id, user_id)

    count = await cx.services.members.message_count(cx.chat.id, user_id) \
        + cx.services.tracker.pending_count(cx.chat.id, user_id)
    extra = (
        f"{T.BULLET} الرسائل: <b>{count}</b> ✉️\n"
        f"{T.BULLET} التفاعل: {activity_level(count)}\n"
        f"{T.LINE}\n"
        f"{T.BULLET} ايدي المجموعة: <code>{cx.chat.id}</code>"
    )
    template = await cx.services.group_settings.get(cx.chat.id, "id_template")
    if template:
        text = render_id_template(template, {
            "name": mention(user_id, name), "username": username_text(username), "id": f"<code>{user_id}</code>",
            "rank": rank_label(rank), "messages": f"<b>{count}</b>", "activity": activity_level(count),
            "group": esc(cx.chat.title or "")})
    else:
        text = T.ID_TEXT.format(name=mention(user_id, name), user_id=user_id,
                                username=username_text(username), rank=rank_label(rank), extra=extra)

    photo_id = None
    from zhoo.systems import features
    try:
        if not await features.enabled(cx.services, cx.chat.id, "id_photo"):
            raise TelegramError("الايدي بالصورة معطّل")
        photos = await cx.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count:
            photo_id = photos.photos[0][-1].file_id
    except TelegramError:
        pass

    if photo_id:
        try:
            await cx.message.reply_photo(photo_id, caption=text)
            return
        except TelegramError:
            pass
    await cx.reply(text)


# ── كليشة الايدي ───────────────────────────────────
ID_TPL_RANK = Rank.MANAGER
ID_TPL_MAX = 800
_TPL_VAR = re.compile(r"\{([^{}\s]{2,12})\}")


def render_id_template(template: str, values: dict[str, str]) -> str:
    """الكليشة نص من المشرف: نهربها كاملة، وبعدين نبدّل المتغيرات المعروفة بس."""
    def sub(m: re.Match) -> str:
        key = T.ID_TPL_VARS.get(m.group(1))
        return values.get(key, m.group(0)) if key else m.group(0)
    return _TPL_VAR.sub(sub, esc(template))


def _has_vars(template: str) -> bool:
    return any(m.group(1) in T.ID_TPL_VARS for m in _TPL_VAR.finditer(template))


@registry.command("id_tpl_set", ("تعيين الايدي", "تعيين كليشة الايدي", "ضع الايدي", "ضع كليشة الايدي"), section=S,
                  min_rank=ID_TPL_RANK, args="text", usage="الكليشة بالمتغيرات",
                  description="كليشة ايدي خاصة بالمجموعة: {الاسم} {الايدي} {الرتبة}...", order=3)
async def cmd_id_tpl_set(cx: CommandContext) -> None:
    tpl = cx.raw_args.strip()
    if not tpl:
        await cx.reply(T.ID_TPL_HELP)
        return
    if not 5 <= len(tpl) <= ID_TPL_MAX or not _has_vars(tpl):
        await cx.reply(T.ID_TPL_BAD)
        return
    await cx.services.group_settings.set(cx.chat.id, "id_template", tpl, cx.user.id)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id, details={"key": "id_template"})
    preview = render_id_template(tpl, {
        "name": mention(cx.user.id, cx.user.full_name), "username": username_text(cx.user.username),
        "id": f"<code>{cx.user.id}</code>", "rank": rank_label(cx.rank), "messages": "<b>0</b>",
        "activity": activity_level(0), "group": esc(cx.chat.title or "")})
    await cx.reply(f"{T.ID_TPL_SET}\n{T.LINE}\n{preview}")


@registry.command("id_tpl_reset", ("حذف الايدي", "مسح الايدي", "حذف كليشة الايدي"), section=S,
                  min_rank=ID_TPL_RANK, description="يرجع كليشة الايدي الأصلية", order=4)
async def cmd_id_tpl_reset(cx: CommandContext) -> None:
    await cx.services.group_settings.set(cx.chat.id, "id_template", "", cx.user.id)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"key": "id_template", "to": ""})
    await cx.reply(T.ID_TPL_RESET)


@registry.command("id_tpl_show", ("كليشة الايدي", "كليشه الايدي"), section=S, min_rank=ID_TPL_RANK,
                  description="يعرض كليشة الايدي الحالية والمتغيرات", order=5)
async def cmd_id_tpl_show(cx: CommandContext) -> None:
    tpl = await cx.services.group_settings.get(cx.chat.id, "id_template")
    head = T.ID_TPL_CURRENT.format(tpl=esc(tpl)) if tpl else T.ID_TPL_DEFAULT
    await cx.reply(f"{head}\n\n{T.ID_TPL_HELP}")


@registry.command("my_rank", ("رتبتي",), section=S, description="يعرض رتبتك بالمجموعة", order=2)
async def cmd_my_rank(cx: CommandContext) -> None:
    await cx.reply(T.MY_RANK.format(rank=rank_label(cx.rank)))


@registry.command("their_rank", ("رتبته", "رتبتها", "رتبه"), section=S, usage="بالرد/اليوزر/الايدي",
                  description="يعرض رتبة عضو آخر", order=3, args="target")
async def cmd_their_rank(cx: CommandContext) -> None:
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "رتبته @username")
        return
    rank = await cx.services.perms.rank_of(cx.bot, cx.chat.id, target.user_id)
    await cx.reply(T.THEIR_RANK.format(mention=mention(target.user_id, target.name), rank=rank_label(rank)))


@registry.command("activity", ("نشاطي", "رسائلي", "تفاعلي"), section=S,
                  description="عدد رسائلك ومستوى تفاعلك", order=4)
async def cmd_activity(cx: CommandContext) -> None:
    count = await cx.services.members.message_count(cx.chat.id, cx.user.id) \
        + cx.services.tracker.pending_count(cx.chat.id, cx.user.id)
    await cx.reply(T.ACTIVITY.format(mention=mention(cx.user.id, cx.user.full_name),
                                     count=count, level=activity_level(count)))


@registry.command("top_active", ("المتفاعلين", "الاكثر تفاعل", "توب", "التوب"), section=S,
                  description="أكثر 10 أعضاء تفاعلاً، برسائلهم ونسبتهم، وترتيبك انت", order=5)
async def cmd_top_active(cx: CommandContext) -> None:
    svc = cx.services
    await svc.tracker.flush()
    rows = await svc.members.top_active(cx.chat.id, TOP_ACTIVE_LIMIT)
    if not rows:
        await cx.reply(T.NO_ACTIVITY)
        return
    total, members = await svc.members.activity_totals(cx.chat.id)
    top = rows[0]["msg_count"] or 1
    lines = []
    for i, r in enumerate(rows):
        name = " ".join(p for p in (r["first_name"], r["last_name"]) if p) or str(r["user_id"])
        count = r["msg_count"]
        filled = max(1, round(count / top * BAR_WIDTH))
        lines.append(T.TOP_ACTIVE_ITEM.format(
            medal=T.TOP_MEDALS[i] if i < len(T.TOP_MEDALS) else f"{i + 1}.",
            mention=mention(r["user_id"], name), count=f"{count:,}",
            bar="▰" * filled + "▱" * (BAR_WIDTH - filled), pct=round(count * 100 / max(total, 1))))
    mine = await svc.members.message_count(cx.chat.id, cx.user.id)
    pos = await svc.members.activity_position(cx.chat.id, mine) if mine else None
    footer = T.TOP_ACTIVE_ME.format(pos=pos, count=f"{mine:,}", level=activity_level(mine)) if pos \
        else T.TOP_ACTIVE_ME_NONE
    await cx.reply(T.TOP_ACTIVE.format(title=esc(cx.chat.title or ""), total=f"{total:,}", members=f"{members:,}",
                                       items="\n".join(lines), me=footer))


@registry.command("about", ("معلومات البوت", "عن البوت", "عن زهو"), section=S,
                  description="معلومات وإحصائيات زهو", where="any", order=6)
async def cmd_about(cx: CommandContext) -> None:
    await cx.reply(await about_text(cx.services))


@registry.command("zhoo", ("زهو", "زهوو", "بوت"), section=S,
                  description="نادِ زهو 🤍", where="any", order=7)
async def cmd_zhoo(cx: CommandContext) -> None:
    choices = [r for r in T.ZHOO_REPLIES if r != _last_zhoo.get(cx.chat.id)]
    reply = random.choice(choices)
    _last_zhoo[cx.chat.id] = reply
    if len(_last_zhoo) > 20_000:
        _last_zhoo.clear()
    await cx.reply(reply.replace("{name}", esc(cx.user.first_name[:30])).replace("  ", " "))
