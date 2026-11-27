"""ردود زهو المضافة + «لا تردي عليه».

- «اضف رد زهو» (المطور) ← رد يشتغل بكل المجموعات.
- «اضف رد زهو مجموعة» (المالك وفوگ) ← رد يشتغل بهاي المجموعة بس.
- «مسح رد زهو الكلام» / «مسح رد زهو مجموعة الكلام» ← يمسح كل ردود هذا الكلام.
- «ردود زهو المضافة» ← القائمة.
- الكلمة الوحدة إلها لحد 10 ردود، وزهو تختار وحد عشوائي بدون ما تكرر نفس الرد ورا بعض.
- رد المجموعة يغلب رد الكل، ورد الكل يغلب ردود زهو الأساسية.

السوالف (ردود زهو وردود المجموعة ونداء «زهو»): رد وحد لكل شخص كل GATE_SECONDS ثانية،
حتى زهو ما تصير مزعجة. الأوامر والحماية ما تتأثر.

«لا تردي عليه» ← زهو توقف السوالف ويه هذا الشخص بالمجموعة، والأوامر والحماية تبقى.
"""
from __future__ import annotations

import random

from telegram import Message
from telegram.error import TelegramError

from zhoo.core import conversation
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import RANK_NAMES, Rank
from zhoo.core.ratelimit import RateLimiter
from zhoo.core.swear import detector
from zhoo.core.targets import TargetError, resolve_target
from zhoo.database.db import now
from zhoo.systems.general import reply_target_error
from zhoo.systems.replies import trigger_key

S = "replies"
GLOBAL = 0
GROUP_RANK = Rank.OWNER
NOREPLY_OTHERS_RANK = Rank.ADMIN
MAX_WORDS, MAX_LEN, MAX_REPLY_LEN = 6, 60, 500
MAX_ITEMS = 10
MAX_TRIGGERS = {True: 500, False: 200}       # بكل المجموعات / بالمجموعة
PREFIX_MAX_WORDS = 7                          # «زهو تحبين الورد؟ 🌸» تنحسب، الجمل الطويلة لا
GATE_SECONDS = 10
NAME_TAG = "{الاسم}"
DONE_WORD = normalize("تم")

# رد وحد لكل شخص كل 10 ثواني بالسوالف
gate = RateLimiter(1, GATE_SECONDS)
_cache: dict[int, dict[tuple[str, ...], tuple[str, list[str]]]] = {}
_last: dict[tuple[int, str], int] = {}


def allow(chat_id: int, user_id: int) -> bool:
    """يستهلك فرصة الرد: True إذا مر أكثر من 10 ثواني على آخر سالفة ويه هذا الشخص."""
    return gate.hit((chat_id, user_id))


# ── لا تردي عليه ────────────────────────────────────
def _nr_key(user_id: int) -> str:
    return f"noreply_{user_id}"


async def muted(svc: Services, chat_id: int, user_id: int) -> bool:
    return await svc.group_settings.get(chat_id, _nr_key(user_id)) == "1"


# ── التخزين ─────────────────────────────────────────
async def _load(svc: Services, scope: int) -> dict[tuple[str, ...], tuple[str, list[str]]]:
    if scope in _cache:
        return _cache[scope]
    rows = await svc.db.fetchall("SELECT trigger, display, reply FROM zhoo_replies WHERE scope = ? ORDER BY id",
                                 (scope,))
    data: dict[tuple[str, ...], tuple[str, list[str]]] = {}
    for r in rows:
        data.setdefault(tuple(r["trigger"].split()), (r["display"], []))[1].append(r["reply"])
    if len(_cache) > 5000:
        _cache.clear()
    _cache[scope] = data
    return data


def _forget(scope: int) -> None:
    _cache.pop(scope, None)


def _match(data: dict[tuple[str, ...], tuple[str, list[str]]], words: tuple[str, ...]) -> tuple[str, ...] | None:
    if not data or not words:
        return None
    if words in data:
        return words
    if len(words) > PREFIX_MAX_WORDS:
        return None
    for n in range(len(words) - 1, 0, -1):
        if words[:n] in data:
            return words[:n]
    return None


async def find(svc: Services, chat_id: int, text: str) -> tuple[int, tuple[str, ...], list[str]] | None:
    words = tuple(trigger_key(text).split())
    for scope in (chat_id, GLOBAL):
        data = await _load(svc, scope)
        key = _match(data, words)
        if key is not None:
            return scope, key, data[key][1]
    return None


def _pick(chat_id: int, key: str, replies: list[str]) -> str:
    choices = [i for i in range(len(replies)) if i != _last.get((chat_id, key))] or [0]
    idx = random.choice(choices)
    if len(_last) > 20_000:
        _last.clear()
    _last[(chat_id, key)] = idx
    return replies[idx]


async def maybe_reply(svc: Services, msg: Message, chat) -> bool:
    """رد مضاف لزهو (المجموعة أول، بعدين الكل). يرجع True إذا انرسل."""
    if not msg.text or len(msg.text) > 200:
        return False
    hit = await find(svc, chat.id, msg.text)
    if hit is None:
        return False
    user = msg.from_user
    if user is None or not allow(chat.id, user.id):
        return True          # لگينا رد بس الشخص لسه مستلم رد قبل شوية: نسكت وما نرد بالأساسي
    scope, key, replies = hit
    text = _pick(chat.id, f"{scope}:{' '.join(key)}", replies).replace(NAME_TAG, esc(user.first_name[:30]))
    try:
        await msg.reply_text(text)
    except TelegramError:
        return False
    return True


# ── الإضافة (بخطوات) ────────────────────────────────
def _clean(text: str) -> bool:
    return detector.scan(text) is None


async def _start_add(cx: CommandContext, everywhere: bool) -> None:
    scope = GLOBAL if everywhere else cx.chat.id
    cx.services.conversations.start(cx.chat.id, cx.user.id, "zhoo_reply_add", "word", scope=scope, items=[])
    await cx.reply(T.ZR_ASK_WORD.format(scope=T.ZR_SCOPE[everywhere]))


async def _save(svc: Services, msg: Message, chat, user, p) -> None:
    scope, word, key, items = p.data["scope"], p.data["word"], p.data["key"], p.data["items"]
    t = now()
    await svc.db.executemany(
        "INSERT INTO zhoo_replies (scope, trigger, display, reply, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [(scope, key, word, r, user.id, t) for r in items])
    _forget(scope)
    await svc.audit.log("zhoo_reply_add", chat_id=chat.id if scope else None, actor_id=user.id,
                        details={"scope": scope, "word": word, "n": len(items)})
    svc.conversations.end(chat.id, user.id)
    await msg.reply_text(T.ZR_SAVED.format(word=esc(word), count=len(items), scope=T.ZR_SCOPE[scope == GLOBAL]))


@conversation.handler("zhoo_reply_add")
async def _flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    from zhoo.systems import aliases
    text = (msg.text or "").strip()
    scope = p.data["scope"]

    if p.step == "word":
        key = trigger_key(text)
        if not text or not key or len(text.split()) > MAX_WORDS or len(text) > MAX_LEN:
            await msg.reply_text(T.ZR_WORD_BAD)
            return
        if registry.parse(text) is not None or (chat.id < 0 and await aliases.expand(svc, chat.id, text)):
            await msg.reply_text(T.ZR_WORD_IS_COMMAND.format(word=esc(text)))
            return
        if not _clean(text):
            await msg.reply_text(T.ZR_BAD_CONTENT)
            return
        data = await _load(svc, scope)
        if tuple(key.split()) not in data and len(data) >= MAX_TRIGGERS[scope == GLOBAL]:
            svc.conversations.end(chat.id, user.id)
            await msg.reply_text(T.ZR_LIMIT.format(n=MAX_TRIGGERS[scope == GLOBAL]))
            return
        p.data.update(word=text, key=key)
        p.step = "reply"
        await msg.reply_text(T.ZR_ASK_REPLY.format(word=esc(text), name_tag=NAME_TAG))
        return

    # خطوة الردود
    if text and normalize(text) == DONE_WORD:
        if not p.data["items"]:
            await msg.reply_text(T.ZR_NO_REPLIES)
            return
        await _save(svc, msg, chat, user, p)
        return
    if not text or len(text) > MAX_REPLY_LEN:
        await msg.reply_text(T.ZR_REPLY_BAD)
        return
    if not _clean(text):
        await msg.reply_text(T.ZR_BAD_CONTENT)
        return
    p.data["items"].append(esc(text))
    left = MAX_ITEMS - len(p.data["items"])
    if left <= 0:
        await _save(svc, msg, chat, user, p)
        return
    await msg.reply_text(T.ZR_REPLY_ADDED.format(left=left))


async def _add_global(cx): await _start_add(cx, True)      # noqa: E704
async def _add_group(cx): await _start_add(cx, False)      # noqa: E704


registry.command("zhoo_reply_add", ("اضف رد زهو", "اضافة رد زهو", "إضافة رد زهو", "اضافه رد زهو"), section=S,
                 min_rank=Rank.DEVELOPER, where="any", order=60,
                 description="رد لزهو يشتغل بكل المجموعات (للمطور)")(_add_global)
registry.command("zhoo_reply_add_group", ("اضف رد زهو مجموعة", "اضف رد زهو مجموعه", "اضف رد زهو للمجموعة",
                                          "اضف رد زهو للمجموعه"), section=S,
                 min_rank=GROUP_RANK, order=61, description="رد لزهو يشتغل بهاي المجموعة بس")(_add_group)


# ── المسح ───────────────────────────────────────────
async def _delete(cx: CommandContext, everywhere: bool, cmd_name: str) -> None:
    word = cx.raw_args.strip()
    key = trigger_key(word)
    if not key:
        await cx.reply(T.ZR_DEL_NEED.format(cmd=cmd_name))
        return
    scope = GLOBAL if everywhere else cx.chat.id
    where = T.ZR_SCOPE[everywhere]
    n = await cx.services.db.execute("DELETE FROM zhoo_replies WHERE scope = ? AND trigger = ?", (scope, key))
    _forget(scope)
    if not n:
        await cx.reply(T.ZR_NOT_FOUND.format(scope=where))
        return
    await cx.services.audit.log("zhoo_reply_del", chat_id=cx.chat.id if scope else None, actor_id=cx.user.id,
                                details={"scope": scope, "word": word})
    await cx.reply(T.ZR_DELETED.format(word=esc(word), scope=where))


async def _del_global(cx): await _delete(cx, True, "مسح رد زهو")                # noqa: E704
async def _del_group(cx): await _delete(cx, False, "مسح رد زهو مجموعة")         # noqa: E704


registry.command("zhoo_reply_del", ("مسح رد زهو", "حذف رد زهو"), section=S, min_rank=Rank.DEVELOPER,
                 where="any", args="text", usage="الكلام", order=62,
                 description="يمسح رد زهو من كل المجموعات (للمطور)")(_del_global)
registry.command("zhoo_reply_del_group", ("مسح رد زهو مجموعة", "مسح رد زهو مجموعه", "حذف رد زهو مجموعة",
                                          "حذف رد زهو مجموعه"), section=S, min_rank=GROUP_RANK,
                 args="text", usage="الكلام", order=63,
                 description="يمسح رد زهو من هاي المجموعة")(_del_group)


@registry.command("zhoo_reply_list", ("ردود زهو المضافة", "ردود زهو المضافه"), section=S, min_rank=GROUP_RANK,
                  where="any", order=64, description="ردود زهو المضافة (بالمجموعة وبالكل)")
async def cmd_list(cx: CommandContext) -> None:
    parts = [T.ZR_LIST_TITLE, T.LINE]
    scopes = []
    if cx.chat.id < 0:
        scopes.append((T.ZR_LIST_GROUP, cx.chat.id))
    if cx.services.perms.is_developer(cx.user.id):
        scopes.append((T.ZR_LIST_GLOBAL, GLOBAL))
    shown = False
    for header, scope in scopes:
        data = await _load(cx.services, scope)
        if not data:
            continue
        shown = True
        parts.append(header)
        parts += [T.ZR_LIST_LINE.format(word=esc(d), n=len(r)) for d, r in list(data.values())[:80]]
    if not shown:
        parts.append(T.ZR_LIST_EMPTY)
    await cx.reply("\n".join(parts))


# ── لا تردي عليه / ردي عليه ─────────────────────────
async def _noreply(cx: CommandContext, on: bool) -> None:
    if cx.message.reply_to_message is None and not cx.args:
        uid, name = cx.user.id, cx.user.full_name
    else:
        try:
            target = await resolve_target(cx)
        except TargetError as e:
            await reply_target_error(cx, e, "لا تردي عليه (بالرد)")
            return
        uid, name = target.user_id, target.name
    if uid != cx.user.id and cx.rank < NOREPLY_OTHERS_RANK:
        await cx.reply(T.NOREPLY_OTHERS_RANK.format(rank=RANK_NAMES[NOREPLY_OTHERS_RANK]))
        return
    who = mention(uid, name)
    svc = cx.services
    if await muted(svc, cx.chat.id, uid) == on:
        await cx.reply((T.NOREPLY_ALREADY if on else T.NOREPLY_NOT).format(mention=who))
        return
    await svc.group_settings.set(cx.chat.id, _nr_key(uid), "1" if on else "", cx.user.id)
    await svc.audit.log("noreply_on" if on else "noreply_off", chat_id=cx.chat.id, actor_id=cx.user.id,
                        target_id=uid)
    await cx.reply((T.NOREPLY_ON if on else T.NOREPLY_OFF).format(mention=who))


async def _nr_on(cx): await _noreply(cx, True)      # noqa: E704
async def _nr_off(cx): await _noreply(cx, False)    # noqa: E704


registry.command("noreply_on", ("لا تردي عليه", "لاتردي عليه", "لا تردي عليها", "لاتردي عليها", "لا تردي علي",
                                "لاتردي علي", "لا تردين عليه", "لاتردين عليه", "لا تردين عليها", "لاتردين عليها"),
                 section=S, args="target", usage="بالرد، أو بدون رد على نفسك", order=65,
                 description="زهو توقف السوالف ويه الشخص (الأوامر تبقى)")(_nr_on)
registry.command("noreply_off", ("ردي عليه", "ردي عليها", "ردي علي", "رجعي ردي عليه", "رجعي ردي عليها"),
                 section=S, args="target", usage="بالرد، أو بدون رد على نفسك", order=66,
                 description="زهو ترجع ترد على الشخص")(_nr_off)
