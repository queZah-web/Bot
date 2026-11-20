"""التفاعل الاجتماعي: الملف الشخصي، النبذة، الشكر، التصويت، والثنائيات (بموافقة الطرفين)."""
from __future__ import annotations

import logging
import re
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import activity_level, duration, esc, mention
from zhoo.core.ranks import Rank, rank_label
from zhoo.core.targets import Target, TargetError, resolve_target
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "social"

MAX_BIO = 200
THANKS_PAIR_COOLDOWN = 12 * 3600
THANKS_DAILY_LIMIT = 20
POLL_RANK = Rank.VIP
PAIRS_TOGGLE_RANK = Rank.MANAGER


def _date(ts: int | None) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else "—"


async def _optional_target(cx: CommandContext) -> Target | None:
    if cx.message.reply_to_message is None and not cx.args and not any(
            e.type == "text_mention" for e in (cx.message.entities or ())):
        return None
    return await resolve_target(cx)


# ── الملف الشخصي والتقييم ───────────────────────────
def stars(avg: float | None) -> str:
    if avg is None:
        return "☆☆☆☆☆"
    full = max(0, min(5, round(avg / 2)))
    return "★" * full + "☆" * (5 - full)


def rating_keyboard(user_id: int, good: int, bad: int) -> InlineKeyboardMarkup:
    p = f"rt:{user_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(T.BTN_RATE_GOOD.format(n=good), callback_data=f"{p}:g:-"),
         InlineKeyboardButton(T.BTN_RATE_BAD.format(n=bad), callback_data=f"{p}:b:-")],
        [InlineKeyboardButton(str(n), callback_data=f"{p}:s:{n}") for n in range(1, 6)],
        [InlineKeyboardButton(str(n), callback_data=f"{p}:s:{n}") for n in range(6, 11)],
    ])


async def profile_view(svc: Services, bot, chat_id: int, user_id: int, name: str):
    """يبني نص الملف وأزرار التقييم (يُستخدم بالأمر وبعد كل تقييم)."""
    rank = await svc.perms.rank_of(bot, chat_id, user_id)
    messages = await svc.members.message_count(chat_id, user_id) + svc.tracker.pending_count(chat_id, user_id)
    since = await svc.db.fetchval("SELECT first_seen FROM group_members WHERE chat_id = ? AND user_id = ?",
                                  (chat_id, user_id))
    partner = ""
    if (await svc.group_settings.get(chat_id, "pairs_on")) == "1":
        row = await svc.social.partner_of(chat_id, user_id)
        if row is not None and not row["hidden"]:
            pname = " ".join(p for p in (row["first_name"], row["last_name"]) if p) or str(row["partner_id"])
            partner = T.PROFILE_PARTNER.format(partner=mention(row["partner_id"], pname))
    bio = await svc.social.get_bio(user_id)
    good, bad, avg, voters = await svc.ratings.summary(chat_id, user_id)
    rating = T.PROFILE_RATING.format(stars=stars(avg), score=f"{avg:.1f}" if avg is not None else T.RATE_NO_SCORE,
                                     voters=voters, good=good, bad=bad)
    from zhoo.core import levels as L
    xp, _ = await svc.levels.get(chat_id, user_id)
    lvl = L.level_for(xp)
    text = T.PROFILE.format(
        name=mention(user_id, name), rank=rank_label(rank), level=lvl, level_title=L.title_for(lvl),
        messages=messages,
        activity=activity_level(messages), thanks=await svc.social.thanks_count(chat_id, user_id),
        warns=await svc.punishments.warning_count(chat_id, user_id),
        limit=await svc.group_settings.get_int(chat_id, "warn_limit"),
        partner=partner, since=_date(since), rating=rating,
        bio=f"<i>{esc(bio)}</i>" if bio else T.PROFILE_NO_BIO)
    return text, rating_keyboard(user_id, good, bad)


async def _profile(cx: CommandContext, user_id: int, name: str) -> None:
    svc = cx.services
    text, kb = await profile_view(svc, cx.bot, cx.chat.id, user_id, name)
    try:
        photos = await cx.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count:
            await cx.message.reply_photo(photos.photos[0][-1].file_id, caption=text, reply_markup=kb)
            return
    except TelegramError:
        pass
    await cx.reply(text, reply_markup=kb)


async def on_rating_button(q, msg: Message, svc: Services, bot, uid_raw: str, action: str, arg: str) -> None:
    """rt:<target>:g|b|s:<n> — أي عضو يقيّم (عدا نفسه)، وكل شخص تقييم واحد يگدر يغيّره."""
    if not uid_raw.isdigit():
        await q.answer()
        return
    target_id, rater = int(uid_raw), q.from_user.id
    if target_id == rater:
        await q.answer(T.RATE_SELF, show_alert=True)
        return
    target = await svc.users.get(target_id)
    if target is not None and target.is_bot:
        await q.answer(T.RATE_BOT, show_alert=True)
        return
    chat_id = msg.chat.id
    if action in ("g", "b"):
        result = await svc.ratings.set_vibe(chat_id, target_id, rater, 1 if action == "g" else -1)
        await q.answer({1: T.RATE_GOOD_DONE, -1: T.RATE_BAD_DONE, 0: T.RATE_REMOVED}[result])
    elif action == "s" and arg.isdigit() and 1 <= int(arg) <= 10:
        await svc.ratings.set_score(chat_id, target_id, rater, int(arg))
        await q.answer(T.RATE_SCORE_DONE.format(n=arg))
    else:
        await q.answer()
        return
    text, kb = await profile_view(svc, bot, chat_id, target_id, target.full_name if target else str(target_id))
    try:
        if msg.photo:
            await msg.edit_caption(caption=text, reply_markup=kb)
        else:
            await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass


@registry.command("rate", ("قيمه", "قيمها", "تقييم"), section=S, args="text", usage="بالرد + رقم من 1 لـ 10",
                  description="تعطي عضو درجة من 10", order=16)
async def cmd_rate(cx: CommandContext) -> None:
    reply = cx.message.reply_to_message
    raw = (cx.args[0] if cx.args else "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    if reply is None or reply.from_user is None or not raw.isdigit() or not 1 <= int(raw) <= 10:
        await cx.reply(T.RATE_CMD_BAD)
        return
    target = reply.from_user
    if target.id == cx.user.id:
        await cx.reply(T.RATE_SELF)
        return
    if target.is_bot:
        await cx.reply(T.RATE_BOT)
        return
    await cx.services.ratings.set_score(cx.chat.id, target.id, cx.user.id, int(raw))
    await cx.reply(T.RATE_CMD_DONE.format(mention=mention(target.id, target.full_name), n=int(raw)))


@registry.command("top_rated", ("الاعلى تقييما", "الأعلى تقييماً", "توب التقييم"), section=S,
                  description="أعلى 10 أعضاء تقييماً", order=17)
async def cmd_top_rated(cx: CommandContext) -> None:
    rows = await cx.services.ratings.top(cx.chat.id)
    if not rows:
        await cx.reply(f"{T.TOP_RATED_HEADER}\n{T.TOP_RATED_EMPTY}")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {mention(r['user_id'], ' '.join(p for p in (r['first_name'], r['last_name']) if p))}"
             f" ⋅ <b>{r['avg']:.1f}</b>/10 <i>({r['n']})</i> ⋅ ✨ {r['good'] or 0}" for i, r in enumerate(rows)]
    await cx.reply(f"{T.TOP_RATED_HEADER}\n" + "\n".join(lines))


@registry.command("profile", ("ملفي", "بروفايلي"), section=S, description="ملفك الشخصي بالمجموعة", order=1)
async def cmd_profile(cx: CommandContext) -> None:
    await _profile(cx, cx.user.id, cx.user.full_name)


@registry.command("their_profile", ("ملفه", "ملفها", "بروفايله"), section=S, args="target",
                  usage="بالرد/اليوزر/الايدي", description="الملف الشخصي لعضو ثاني", order=2)
async def cmd_their_profile(cx: CommandContext) -> None:
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "ملفه @username")
        return
    await _profile(cx, target.user_id, target.name)


@registry.command("bio_set", ("تعيين نبذتي", "نبذتي"), section=S, args="text", usage="النص",
                  description="نبذة تطلع بملفك الشخصي", where="any", order=3)
async def cmd_bio_set(cx: CommandContext) -> None:
    bio = " ".join(cx.raw_args.split())
    if not bio or len(bio) > MAX_BIO:
        await cx.reply(T.BIO_BAD)
        return
    await cx.services.users.upsert(cx.user.id, cx.user.first_name, cx.user.last_name, cx.user.username, False)
    await cx.services.social.set_bio(cx.user.id, bio)
    await cx.reply(T.BIO_SET)


@registry.command("bio_del", ("حذف نبذتي", "مسح نبذتي"), section=S, description="يمسح نبذتك", where="any", order=4)
async def cmd_bio_del(cx: CommandContext) -> None:
    await cx.services.social.set_bio(cx.user.id, None)
    await cx.reply(T.BIO_DELETED)


# ── الشكر ───────────────────────────────────────────
@registry.command("thanks", ("شكر", "شكرا", "شكراً", "مشكور"), section=S, args="target",
                  usage="بالرد", description="تشكر عضو، والشكر يطلع بملفه", order=5)
async def cmd_thanks(cx: CommandContext) -> None:
    try:
        target = await _optional_target(cx)
    except TargetError:
        return
    if target is None:
        return  # «شكراً» عادية بدون رد = كلام عادي
    svc = cx.services
    if target.user_id == cx.user.id:
        await cx.reply(T.THANKS_SELF)
        return
    if target.is_bot:
        await cx.reply(T.THANKS_BOT)
        return
    who = mention(target.user_id, target.name)
    last = await svc.social.last_thanks(cx.chat.id, cx.user.id, target.user_id)
    if last and time.time() - last < THANKS_PAIR_COOLDOWN:
        await cx.reply(T.THANKS_AGAIN.format(mention=who, left=duration(THANKS_PAIR_COOLDOWN - (time.time() - last))))
        return
    if await svc.social.thanks_given_since(cx.chat.id, cx.user.id, 86400) >= THANKS_DAILY_LIMIT:
        await cx.reply(T.THANKS_LIMIT)
        return
    count = await svc.social.add_thanks(cx.chat.id, cx.user.id, target.user_id)
    await cx.reply(T.THANKS_DONE.format(mention=who, count=count))


@registry.command("top_thanked", ("الاكثر شكرا", "الأكثر شكراً", "توب الشكر"), section=S,
                  description="أكثر 10 أعضاء انشكروا", order=6)
async def cmd_top_thanked(cx: CommandContext) -> None:
    rows = await cx.services.social.top_thanked(cx.chat.id)
    if not rows:
        await cx.reply(f"{T.TOP_THANKED_HEADER}\n{T.TOP_THANKED_EMPTY}")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {mention(r['user_id'], ' '.join(p for p in (r['first_name'], r['last_name']) if p))}"
             f" ⋅ <b>{r['n']}</b> 🤍" for i, r in enumerate(rows)]
    await cx.reply(f"{T.TOP_THANKED_HEADER}\n" + "\n".join(lines))


# ── التصويت ─────────────────────────────────────────
def parse_poll(raw: str) -> tuple[str, list[str]] | None:
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    if len(lines) == 1:  # سطر واحد: السؤال؟ خيار، خيار
        parts = re.split(r"[؟?]", lines[0], maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            q = parts[0].strip() + "؟"
            lines = [q] + [o.strip() for o in re.split(r"[،,|\-]", parts[1]) if o.strip()]
    if len(lines) < 3:
        return None
    question, options = lines[0], list(dict.fromkeys(lines[1:]))  # بدون تكرار
    if not 2 <= len(options) <= 10:
        return None
    return question, options


async def _poll(cx: CommandContext, anonymous: bool) -> None:
    parsed = parse_poll(cx.raw_args)
    if parsed is None:
        await cx.reply(T.POLL_BAD)
        return
    question, options = parsed
    if len(question) > 300 or any(len(o) > 100 for o in options):
        await cx.reply(T.POLL_FAILED)
        return
    try:
        await cx.bot.send_poll(cx.chat.id, question, options, is_anonymous=anonymous)
    except TelegramError as e:
        log.info("فشل التصويت: %s", e)
        await cx.reply(T.POLL_FAILED)


async def _poll_anon(cx): await _poll(cx, True)        # noqa: E704
async def _poll_public(cx): await _poll(cx, False)     # noqa: E704


registry.command("poll", ("تصويت", "استفتاء"), section=S, min_rank=POLL_RANK, args="text",
                 usage="السؤال ثم الخيارات بأسطر", description="تصويت سري (ما يبين منو صوّت)", order=7)(_poll_anon)
registry.command("poll_public", ("تصويت علني", "استفتاء علني"), section=S, min_rank=POLL_RANK, args="text",
                 usage="السؤال ثم الخيارات بأسطر", description="تصويت علني (يبين منو صوّت على شنو)",
                 order=8)(_poll_public)


# ── الثنائيات ───────────────────────────────────────
async def _pairs_on(cx: CommandContext) -> bool:
    if (await cx.services.group_settings.get(cx.chat.id, "pairs_on")) != "1":
        await cx.reply(T.PAIRS_OFF)
        return False
    return True


async def _toggle_pairs(cx: CommandContext, on: bool) -> None:
    await cx.services.group_settings.set(cx.chat.id, "pairs_on", "1" if on else "0", cx.user.id)
    await cx.services.audit.log("setting", chat_id=cx.chat.id, actor_id=cx.user.id,
                                details={"key": "pairs_on", "to": int(on)})
    await cx.reply(T.PAIRS_ON if on else T.PAIRS_DISABLED)


async def _pairs_enable(cx): await _toggle_pairs(cx, True)     # noqa: E704
async def _pairs_disable(cx): await _toggle_pairs(cx, False)   # noqa: E704


registry.command("pairs_on", ("تفعيل الثنائيات",), section=S, min_rank=PAIRS_TOGGLE_RANK,
                 description="يشغّل نظام الثنائيات", order=20)(_pairs_enable)
registry.command("pairs_off", ("تعطيل الثنائيات",), section=S, min_rank=PAIRS_TOGGLE_RANK,
                 description="يوقف نظام الثنائيات", order=21)(_pairs_disable)


@registry.command("pair_request", ("ارتباط", "طلب ارتباط"), section=S, args="target", usage="بالرد/اليوزر",
                  description="طلب ارتباط (لازم الطرف الثاني يوافق)", order=10)
async def cmd_pair_request(cx: CommandContext) -> None:
    if not await _pairs_on(cx):
        return
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "ارتباط @username")
        return
    svc = cx.services
    if target.user_id == cx.user.id:
        await cx.reply(T.PAIR_SELF)
        return
    if target.is_bot:
        await cx.reply(T.PAIR_BOT)
        return
    if await svc.social.partner_of(cx.chat.id, cx.user.id):
        await cx.reply(T.PAIR_YOU_TAKEN)
        return
    who = mention(target.user_id, target.name)
    if await svc.social.partner_of(cx.chat.id, target.user_id):
        await cx.reply(T.PAIR_THEY_TAKEN.format(mention=who))
        return
    data = f"pr:{cx.user.id}:{target.user_id}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(T.BTN_PAIR_ACCEPT, callback_data=f"{data}:a"),
                                InlineKeyboardButton(T.BTN_PAIR_REJECT, callback_data=f"{data}:r")]])
    await cx.reply(T.PAIR_REQUEST.format(from_=mention(cx.user.id, cx.user.full_name), to=who), reply_markup=kb)


async def on_pair_button(q, msg: Message, svc: Services, from_raw: str, to_raw: str, action: str) -> None:
    if not (from_raw.isdigit() and to_raw.isdigit()):
        await q.answer(T.PAIR_EXPIRED)
        return
    a, b = int(from_raw), int(to_raw)
    if q.from_user.id != b:
        await q.answer(T.PAIR_NOT_YOURS, show_alert=True)
        return
    chat_id = msg.chat.id
    ua, ub = await svc.users.get(a), await svc.users.get(b)
    ma = mention(a, ua.full_name if ua else str(a))
    mb = mention(b, q.from_user.full_name)
    if action == "r":
        text = T.PAIR_REJECTED.format(to=mb)
    elif (await svc.group_settings.get(chat_id, "pairs_on")) != "1" or not await svc.social.link(chat_id, a, b):
        await q.answer(T.PAIR_EXPIRED, show_alert=True)
        text = T.PAIR_EXPIRED
    else:
        await svc.audit.log("pair_link", chat_id=chat_id, actor_id=b, target_id=a)
        text = T.PAIR_ACCEPTED.format(a=ma, b=mb)
    await q.answer()
    try:
        await msg.edit_text(text, reply_markup=None)
    except BadRequest:
        pass


@registry.command("pair_unlink", ("فك الارتباط", "فك ارتباطي", "انفصال"), section=S,
                  description="يفك ارتباطك (حقك بأي وقت)", order=11)
async def cmd_pair_unlink(cx: CommandContext) -> None:
    partner_id = await cx.services.social.unlink(cx.chat.id, cx.user.id)
    if partner_id is None:
        await cx.reply(T.PAIR_NONE)
        return
    await cx.services.audit.log("pair_unlink", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=partner_id)
    p = await cx.services.users.get(partner_id)
    await cx.reply(T.PAIR_UNLINKED.format(a=mention(cx.user.id, cx.user.full_name),
                                          b=mention(partner_id, p.full_name if p else str(partner_id))))


@registry.command("pair_show", ("شريكي", "شريكتي"), section=S, description="يعرض شريكك", order=12)
async def cmd_pair_show(cx: CommandContext) -> None:
    row = await cx.services.social.partner_of(cx.chat.id, cx.user.id)
    if row is None:
        await cx.reply(T.PAIR_NONE)
        return
    name = " ".join(p for p in (row["first_name"], row["last_name"]) if p) or str(row["partner_id"])
    await cx.reply(T.PAIR_SHOW.format(mention=mention(row["partner_id"], name), since=_date(row["since"])))


async def _set_hidden(cx: CommandContext, hidden: bool) -> None:
    if not await cx.services.social.set_hidden(cx.chat.id, cx.user.id, hidden):
        await cx.reply(T.PAIR_NONE)
        return
    await cx.reply(T.PAIR_HIDDEN if hidden else T.PAIR_SHOWN)


async def _hide(cx): await _set_hidden(cx, True)       # noqa: E704
async def _show(cx): await _set_hidden(cx, False)      # noqa: E704


registry.command("pair_hide", ("اخفاء ارتباطي", "إخفاء ارتباطي"), section=S,
                 description="يخفي ارتباطك من الملف والقائمة", order=13)(_hide)
registry.command("pair_unhide", ("اظهار ارتباطي", "إظهار ارتباطي"), section=S,
                 description="يرجع ارتباطك ظاهر", order=14)(_show)


@registry.command("pairs_list", ("الثنائيات",), section=S, description="قائمة الثنائيات الظاهرة", order=15)
async def cmd_pairs_list(cx: CommandContext) -> None:
    if not await _pairs_on(cx):
        return
    rows = await cx.services.social.list_pairs(cx.chat.id)
    if not rows:
        await cx.reply(f"{T.PAIRS_HEADER}\n{T.PAIRS_EMPTY}")
        return
    lines = [f"💍 {mention(r['user_id'], r['a_name'] or str(r['user_id']))} و "
             f"{mention(r['partner_id'], r['b_name'] or str(r['partner_id']))}" for r in rows]
    await cx.reply(f"{T.PAIRS_HEADER}\n" + "\n".join(lines))
