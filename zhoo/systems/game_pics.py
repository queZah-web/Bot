"""صور لعبة «صور»: المطور يضيف صور لكل المجموعات، والمالك وفوگ لمجموعته.

- «اضف صورة للعبة» ← ارسل الصورة ← اكتب اسمها (وإذا إلها أكثر من اسم افصل بـ ،)
- «مسح صورة اللعبة الاسم» ⋅ «صور اللعبة» (العدد)
- اللعبة تختار صورة مضافة نص المرات تقريباً، والباقي من صور الإيموجي الجاهزة.
"""
from __future__ import annotations

import random
import re

from telegram import Message

from zhoo.core import conversation
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc
from zhoo.core.ranks import Rank
from zhoo.core.swear import detector
from zhoo.database.db import now

S = "games"
GLOBAL = 0
GROUP_RANK = Rank.OWNER
MAX_PICS = {True: 1000, False: 300}
CUSTOM_CHANCE = 0.5
_SPLIT = re.compile(r"\s*[،,|/]\s*")


def _key(name: str) -> str:
    from zhoo.systems.games import _norm
    return _norm(name)


async def pick(svc: Services, chat_id: int) -> tuple[str, list[str]] | None:
    """صورة مضافة عشوائية (من المجموعة أو العامة)، أو None حتى تنختار صورة إيموجي."""
    if random.random() > CUSTOM_CHANCE:
        return None
    row = await svc.db.fetchone(
        "SELECT file_id, answers FROM game_pictures WHERE scope IN (?, 0) ORDER BY RANDOM() LIMIT 1", (chat_id,))
    if row is None:
        return None
    return row["file_id"], row["answers"].split("|")


async def _start(cx: CommandContext, everywhere: bool) -> None:
    scope = GLOBAL if everywhere else cx.chat.id
    count = await cx.services.db.fetchval("SELECT COUNT(*) FROM game_pictures WHERE scope = ?", (scope,), default=0)
    if count >= MAX_PICS[everywhere]:
        await cx.reply(T.PIC_LIMIT.format(n=MAX_PICS[everywhere]))
        return
    cx.services.conversations.start(cx.chat.id, cx.user.id, "game_pic_add", "photo", scope=scope)
    await cx.reply(T.PIC_ASK_PHOTO.format(scope=T.ZR_SCOPE[everywhere]))


@conversation.handler("game_pic_add")
async def _flow(svc: Services, context, msg: Message, chat, user, p) -> None:
    if p.step == "photo":
        if not msg.photo:
            await msg.reply_text(T.PIC_NOT_PHOTO)
            return
        p.data["file_id"] = msg.photo[-1].file_id
        p.step = "name"
        await msg.reply_text(T.PIC_ASK_NAME)
        return
    text = (msg.text or "").strip()
    names = [n for n in _SPLIT.split(text) if n][:8]
    if not names or any(len(n) > 40 or len(n.split()) > 4 for n in names):
        await msg.reply_text(T.PIC_NAME_BAD)
        return
    if any(detector.scan(n) for n in names):
        await msg.reply_text(T.ZR_BAD_CONTENT)
        return
    scope = p.data["scope"]
    await svc.db.execute(
        "INSERT INTO game_pictures (scope, file_id, key, answers, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (scope, p.data["file_id"], _key(names[0]), "|".join(names), user.id, now()))
    await svc.audit.log("game_pic_add", chat_id=chat.id if scope else None, actor_id=user.id,
                        details={"scope": scope, "name": names[0]})
    svc.conversations.end(chat.id, user.id)
    await msg.reply_text(T.PIC_SAVED.format(name=esc(names[0]), n=len(names), scope=T.ZR_SCOPE[scope == GLOBAL]))


async def _add_global(cx): await _start(cx, True)     # noqa: E704
async def _add_group(cx): await _start(cx, False)     # noqa: E704


registry.command("game_pic_add", ("اضف صورة للعبة", "اضف صوره للعبه", "اضافة صورة للعبة"), section=S,
                 min_rank=Rank.DEVELOPER, where="any", order=40,
                 description="صورة للعبة «صور» بكل المجموعات (للمطور)")(_add_global)
registry.command("game_pic_add_group", ("اضف صورة للعبة مجموعة", "اضف صوره للعبه مجموعه"), section=S,
                 min_rank=GROUP_RANK, order=41, description="صورة للعبة «صور» بهاي المجموعة")(_add_group)


async def _delete(cx: CommandContext, everywhere: bool, cmd: str) -> None:
    name = cx.raw_args.strip()
    if not name:
        await cx.reply(T.PIC_DEL_NEED.format(cmd=cmd))
        return
    scope = GLOBAL if everywhere else cx.chat.id
    n = await cx.services.db.execute("DELETE FROM game_pictures WHERE scope = ? AND key = ?", (scope, _key(name)))
    if not n:
        await cx.reply(T.PIC_NOT_FOUND)
        return
    await cx.services.audit.log("game_pic_del", chat_id=cx.chat.id if scope else None, actor_id=cx.user.id,
                                details={"scope": scope, "name": name, "n": n})
    await cx.reply(T.PIC_DELETED.format(name=esc(name), n=n))


async def _del_global(cx): await _delete(cx, True, "مسح صورة اللعبة")              # noqa: E704
async def _del_group(cx): await _delete(cx, False, "مسح صورة اللعبة مجموعة")       # noqa: E704


registry.command("game_pic_del", ("مسح صورة اللعبة", "مسح صوره اللعبه", "حذف صورة اللعبة"), section=S,
                 min_rank=Rank.DEVELOPER, where="any", args="text", usage="اسم الصورة", order=42,
                 description="يمسح صورة من لعبة «صور» (للمطور)")(_del_global)
registry.command("game_pic_del_group", ("مسح صورة اللعبة مجموعة", "مسح صوره اللعبه مجموعه"), section=S,
                 min_rank=GROUP_RANK, args="text", usage="اسم الصورة", order=43,
                 description="يمسح صورة مضافة من هاي المجموعة")(_del_group)


@registry.command("game_pic_list", ("صور اللعبة", "صور اللعبه"), section=S, min_rank=GROUP_RANK, where="any",
                  order=44, description="الصور المضافة للعبة «صور»")
async def cmd_list(cx: CommandContext) -> None:
    db = cx.services.db
    rows = await db.fetchall("SELECT answers FROM game_pictures WHERE scope = ? ORDER BY id DESC LIMIT 60",
                             (cx.chat.id,)) if cx.chat.id < 0 else []
    total_global = await db.fetchval("SELECT COUNT(*) FROM game_pictures WHERE scope = 0", default=0)
    names = " ⋅ ".join(esc(r["answers"].split("|")[0]) for r in rows) or T.NONE_VALUE
    await cx.reply(T.PIC_LIST.format(group=len(rows), names=names, everywhere=total_global))
