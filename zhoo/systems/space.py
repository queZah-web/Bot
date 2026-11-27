"""الكون 🌌 — 14 مجرة و30 ألف كوكب، كل كوكب إله صورة مرسومة واسم ونوع وندرة وسعر ودخل يومي.

تشتري الكواكب بكاش المحفظة 🌸، وتبيعها للبنك المركزي (85% من سعر السوق) أو تعرضها للاعبين.
السوق يتحرك كل يوم، وكل 6 ساعات مجرتين عليهن تخفيض (20%–50%) ← اشتري بالتخفيض وبيع بعدين وتربح.
كل مجموعة إلها كونها الخاص (الملكية بالمجموعة، مثل المحفظة).

callback: sp:<فعل>:<مجرة>:<كوكب أو صفحة>
  v=عرض كوكب ⋅ b=شراء من البنك ⋅ s=بيع (تأكيد) ⋅ S=تأكيد البيع ⋅ x=رجوع ⋅ m=شراء عرض لاعب
  e=استكشاف ⋅ g=مجرة ⋅ r=الأندر بالمجرة ⋅ u=قائمة الكون ⋅ k=كواكبي ⋅ t=التخفيضات ⋅ q=سوق اللاعبين ⋅ w=الأباطرة
"""
from __future__ import annotations

import io
import logging
import random
import sqlite3

from telegram import InlineKeyboardButton as Btn
from telegram import InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import space_art, universe as U
from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration, esc, mention
from zhoo.core.ratelimit import RateLimiter
from zhoo.data import space_bank as B
from zhoo.database.db import now
from zhoo.repositories.economy import InsufficientFunds
from zhoo.systems import economy

log = logging.getLogger(__name__)
S = "space"
MAX_PLANETS = 100
LIST_FEE = 5                 # % من سعر البيع بين اللاعبين
LIST_MAX_MULT = 10           # أعلى سعر عرض = 10 أضعاف السوق
INCOME_COOLDOWN = 24 * 3600
_photo_cache: dict[str, str] = {}
_explore_limiter = RateLimiter(1, 8)


def _n(x: int) -> str:
    return f"{x:,}"


# ── الملكية ─────────────────────────────────────────
async def owner_row(svc: Services, chat_id: int, p: U.Planet):
    return await svc.db.fetchone("SELECT * FROM space_planets WHERE chat_id = ? AND galaxy = ? AND idx = ?",
                                 (chat_id, p.galaxy, p.idx))


async def owned_by(svc: Services, chat_id: int, user_id: int) -> list[U.Planet]:
    rows = await svc.db.fetchall("SELECT galaxy, idx FROM space_planets WHERE chat_id = ? AND owner_id = ? "
                                 "ORDER BY bought_at", (chat_id, user_id))
    return [p for p in (U.planet(r["galaxy"], r["idx"]) for r in rows) if p]


async def _name(svc: Services, user_id: int) -> str:
    u = await svc.users.get(user_id)
    return mention(user_id, u.full_name if u else str(user_id))


# ── البطاقات ────────────────────────────────────────
def _rarity(p: U.Planet) -> str:
    name, emoji, *_ = B.RARITIES[p.rarity]
    return f"{emoji} {name}"


def _kind(p: U.Planet) -> str:
    t = B.PLANET_TYPES[p.kind]
    return f"{t[1]} {t[0]}"


async def planet_caption(svc: Services, chat_id: int, p: U.Planet) -> tuple[str, object]:
    g = U.galaxy(p.galaxy)
    price, off = U.buy_price(p)
    row = await owner_row(svc, chat_id, p)
    lines = [
        T.title(f"{p.name}", "🪐"), T.LINE,
        T.SP_LINE_CODE.format(code=p.code),
        T.SP_LINE_GALAXY.format(g=f"{g.emoji} {g.name}"),
        T.SP_LINE_KIND.format(kind=_kind(p), rarity=_rarity(p)),
        T.SP_LINE_SIZE.format(d=_n(p.diameter), moons=p.moons, rings=T.SP_RINGS if p.rings else ""),
        T.SP_LINE_TEMP.format(t=p.temp, life=T.SP_LIFE[p.life]),
        T.LINE,
    ]
    if row is None:
        lines.append(T.SP_LINE_PRICE_SALE.format(price=_n(price), old=_n(U.market_price(p)), off=off) if off
                     else T.SP_LINE_PRICE.format(price=_n(price)))
        lines.append(T.SP_LINE_INCOME.format(n=_n(p.income)))
        lines.append(T.SP_LINE_FREE)
    else:
        lines.append(T.SP_LINE_VALUE.format(price=_n(U.market_price(p)), sell=_n(U.sell_price(p))))
        lines.append(T.SP_LINE_INCOME.format(n=_n(p.income)))
        lines.append(T.SP_LINE_OWNER.format(who=await _name(svc, row["owner_id"])))
        if row["listed"]:
            lines.append(T.SP_LINE_LISTED.format(price=_n(row["listed"])))
    return "\n".join(lines), row


def planet_keyboard(p: U.Planet, row, price: int) -> InlineKeyboardMarkup:
    g, i = p.galaxy, p.idx
    kb = []
    if row is None:
        kb.append([Btn(T.SP_BTN_BUY.format(price=_n(price)), callback_data=f"sp:b:{g}:{i}")])
    else:
        if row["listed"]:
            kb.append([Btn(T.SP_BTN_BUY_LISTED.format(price=_n(row["listed"])), callback_data=f"sp:m:{g}:{i}")])
        kb.append([Btn(T.SP_BTN_SELL.format(price=_n(U.sell_price(p))), callback_data=f"sp:s:{g}:{i}")])
    kb.append([Btn(T.SP_BTN_EXPLORE, callback_data=f"sp:e:{g}:0"), Btn(T.SP_BTN_GALAXY, callback_data=f"sp:g:{g}:0")])
    return InlineKeyboardMarkup(kb)


async def _photo(key: str, render) -> object:
    """file_id محفوظ، أو صورة جديدة (bytes)، أو None إذا Pillow مو موجودة."""
    if key in _photo_cache:
        return _photo_cache[key]
    data = render()
    return io.BytesIO(data) if data else None


def _remember(key: str, sent) -> None:
    photo = getattr(sent, "photo", None)
    if photo:
        if len(_photo_cache) > 30000:
            _photo_cache.clear()
        _photo_cache[key] = photo[-1].file_id


async def send_planet(bot, svc: Services, chat_id: int, p: U.Planet, reply_to: int | None = None) -> None:
    caption, row = await planet_caption(svc, chat_id, p)
    kb = planet_keyboard(p, row, U.buy_price(p)[0])
    key = f"p{p.code}"
    photo = await _photo(key, lambda: space_art.planet_png(p.seed, **U.art_args(p)))
    kw = {"reply_to_message_id": reply_to} if reply_to else {}
    try:
        if photo is None:
            await bot.send_message(chat_id, caption, reply_markup=kb, **kw)
        else:
            _remember(key, await bot.send_photo(chat_id, photo, caption=caption, reply_markup=kb, **kw))
    except TelegramError as e:
        log.info("ما گدرت أرسل الكوكب: %s", e)


async def galaxy_caption(svc: Services, chat_id: int, g: U.Galaxy) -> str:
    owned = await svc.db.fetchval("SELECT COUNT(*) FROM space_planets WHERE chat_id = ? AND galaxy = ?",
                                  (chat_id, g.num), default=0)
    f = U.market_factor(g.num)
    off = U.sales().get(g.num)
    return "\n".join([
        T.title(f"مَـجَـرَّة {g.name}", g.emoji), T.LINE,
        f"{T.BULLET} <i>{g.about}</i>",
        T.SP_G_PLANETS.format(n=_n(g.count), owned=owned),
        T.SP_G_MARKET.format(arrow="📈" if f >= 1 else "📉", pct=f"{(f - 1) * 100:+.0f}"),
        T.SP_G_LEVEL.format(mult=g.mult),
        T.SP_G_SALE.format(off=off, left=duration(U.sale_left())) if off else T.SP_G_NO_SALE,
    ])


def galaxy_keyboard(g: U.Galaxy) -> InlineKeyboardMarkup:
    n = g.num
    return InlineKeyboardMarkup([
        [Btn(T.SP_BTN_EXPLORE_HERE, callback_data=f"sp:e:{n}:0")],
        [Btn(T.SP_BTN_RARE["legendary"], callback_data=f"sp:r:{n}:0"),
         Btn(T.SP_BTN_RARE["epic"], callback_data=f"sp:r:{n}:1")],
        [Btn(T.SP_BTN_UNIVERSE, callback_data="sp:u:0:0")],
    ])


async def send_galaxy(bot, svc: Services, chat_id: int, g: U.Galaxy, reply_to: int | None = None) -> None:
    caption = await galaxy_caption(svc, chat_id, g)
    key = f"g{g.num}"
    photo = await _photo(key, lambda: space_art.galaxy_png(g.num * 7 + 3, g.color))
    kw = {"reply_to_message_id": reply_to} if reply_to else {}
    try:
        if photo is None:
            await bot.send_message(chat_id, caption, reply_markup=galaxy_keyboard(g), **kw)
        else:
            _remember(key, await bot.send_photo(chat_id, photo, caption=caption, reply_markup=galaxy_keyboard(g), **kw))
    except TelegramError as e:
        log.info("ما گدرت أرسل المجرة: %s", e)


async def universe_view(svc: Services, chat_id: int, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    owned = await svc.db.fetchval("SELECT COUNT(*) FROM space_planets WHERE chat_id = ?", (chat_id,), default=0)
    mine = await svc.db.fetchval("SELECT COUNT(*) FROM space_planets WHERE chat_id = ? AND owner_id = ?",
                                 (chat_id, user_id), default=0)
    sale = " ⋅ ".join(f"{U.galaxy(g).emoji} {U.galaxy(g).name} <b>-{off}%</b>" for g, off in U.sales().items())
    text = T.SP_UNIVERSE.format(galaxies=len(U.GALAXIES), planets=_n(sum(g.count for g in U.GALAXIES)),
                                owned=_n(owned), mine=mine, sale=sale, left=duration(U.sale_left()))
    gb = [Btn(f"{g.emoji} {g.name}", callback_data=f"sp:g:{g.num}:0") for g in U.GALAXIES]
    rows = [gb[i:i + 2] for i in range(0, len(gb), 2)]
    rows += [
        [Btn(T.SP_BTN_EXPLORE, callback_data="sp:e:0:0"), Btn(T.SP_BTN_MINE, callback_data="sp:k:0:0")],
        [Btn(T.SP_BTN_SALES, callback_data="sp:t:0:0"), Btn(T.SP_BTN_MARKET, callback_data="sp:q:0:0")],
        [Btn(T.SP_BTN_EMPERORS, callback_data="sp:w:0:0")],
    ]
    return text, InlineKeyboardMarkup(rows)


# ── العمليات ────────────────────────────────────────
async def buy(svc: Services, chat_id: int, user_id: int, p: U.Planet) -> tuple[str, int]:
    """يرجع (ok|owned|limit|funds، الرقم المهم)."""
    count = await svc.db.fetchval("SELECT COUNT(*) FROM space_planets WHERE chat_id = ? AND owner_id = ?",
                                  (chat_id, user_id), default=0)
    if count >= MAX_PLANETS:
        return "limit", MAX_PLANETS
    price, _ = U.buy_price(p)
    try:
        async with svc.db.transaction() as conn:
            await conn.execute("INSERT INTO space_planets (chat_id, galaxy, idx, owner_id, paid, bought_at) "
                               "VALUES (?, ?, ?, ?, ?, ?)", (chat_id, p.galaxy, p.idx, user_id, price, now()))
            balance = await svc.economy.change_in(conn, chat_id, user_id, -price, "planet_buy", p.code)
    except sqlite3.IntegrityError:
        return "owned", 0
    except InsufficientFunds as e:
        return "funds", e.args[0]
    await svc.audit.log("planet_buy", chat_id=chat_id, actor_id=user_id, details={"code": p.code, "price": price})
    return "ok", balance


async def sell(svc: Services, chat_id: int, user_id: int, p: U.Planet) -> tuple[str, int]:
    price = U.sell_price(p)
    async with svc.db.transaction() as conn:
        cur = await conn.execute("DELETE FROM space_planets WHERE chat_id = ? AND galaxy = ? AND idx = ? AND owner_id = ?",
                                 (chat_id, p.galaxy, p.idx, user_id))
        if cur.rowcount != 1:
            return "not_owner", 0
        await svc.economy.change_in(conn, chat_id, user_id, price, "planet_sell", p.code)
    await svc.audit.log("planet_sell", chat_id=chat_id, actor_id=user_id, details={"code": p.code, "price": price})
    return "ok", price


async def buy_listed(svc: Services, chat_id: int, buyer: int, p: U.Planet) -> tuple[str, int, int | None]:
    row = await owner_row(svc, chat_id, p)
    if row is None or not row["listed"]:
        return "not_listed", 0, None
    if row["owner_id"] == buyer:
        return "self", 0, None
    count = await svc.db.fetchval("SELECT COUNT(*) FROM space_planets WHERE chat_id = ? AND owner_id = ?",
                                  (chat_id, buyer), default=0)
    if count >= MAX_PLANETS:
        return "limit", MAX_PLANETS, None
    price, seller = row["listed"], row["owner_id"]
    try:
        async with svc.db.transaction() as conn:
            cur = await conn.execute(
                "UPDATE space_planets SET owner_id = ?, paid = ?, bought_at = ?, listed = NULL "
                "WHERE chat_id = ? AND galaxy = ? AND idx = ? AND owner_id = ? AND listed = ?",
                (buyer, price, now(), chat_id, p.galaxy, p.idx, seller, price))
            if cur.rowcount != 1:
                return "not_listed", 0, None
            await svc.economy.change_in(conn, chat_id, buyer, -price, "planet_buy", p.code)
            await svc.economy.change_in(conn, chat_id, seller, price * (100 - LIST_FEE) // 100, "planet_sell", p.code)
    except InsufficientFunds as e:
        return "funds", e.args[0], None
    await svc.audit.log("planet_trade", chat_id=chat_id, actor_id=buyer, target_id=seller,
                        details={"code": p.code, "price": price})
    return "ok", price, seller


# ── الأوامر ─────────────────────────────────────────
async def _guard(cx: CommandContext) -> bool:
    return await economy._guard(cx)


async def _planet_arg(cx: CommandContext, example: str) -> U.Planet | None:
    p = U.parse_code(cx.args[0] if cx.args else "")
    if p is None:
        await cx.reply(T.SP_CODE_BAD.format(example=example))
    return p


@registry.command("space_menu", ("الكون", "الفضاء", "المجرات", "لعبة الكون"), section=S,
                  description="الكون: 14 مجرة و30 ألف كوكب للبيع والشراء 🌌", order=1)
async def cmd_universe(cx: CommandContext) -> None:
    if await _guard(cx):
        text, kb = await universe_view(cx.services, cx.chat.id, cx.user.id)
        await cx.reply(text, reply_markup=kb)


@registry.command("space_galaxy", ("مجرة", "مجره"), section=S, args="text", usage="الاسم أو الرقم",
                  description="بطاقة مجرة بصورتها وسوقها", order=2)
async def cmd_galaxy(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    g = U.find_galaxy(cx.raw_args)
    if g is None:
        await cx.reply(T.SP_GALAXY_BAD)
        return
    await send_galaxy(cx.bot, cx.services, cx.chat.id, g, cx.message.message_id)


@registry.command("space_planet", ("كوكب",), section=S, args="text", usage="الكود (مثال: 2-1250)",
                  description="بطاقة كوكب بصورته ومعلوماته وسعره 🪐", order=3)
async def cmd_planet(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    p = await _planet_arg(cx, "كوكب 2-1250")
    if p:
        await send_planet(cx.bot, cx.services, cx.chat.id, p, cx.message.message_id)


@registry.command("space_explore", ("استكشاف", "استكشف", "اكتشاف"), section=S,
                  description="تلگى كوكب عشوائي بالكون 🔭", order=4)
async def cmd_explore(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    if not _explore_limiter.hit((cx.chat.id, cx.user.id)):
        await cx.reply(T.SP_EXPLORE_SLOW)
        return
    await send_planet(cx.bot, cx.services, cx.chat.id, U.random_planet(), cx.message.message_id)


async def _reply_buy(cx_reply, svc, chat_id, uid, p, name) -> None:
    result, n = await buy(svc, chat_id, uid, p)
    if result == "ok":
        await cx_reply(T.SP_BOUGHT.format(who=name, name=p.name, code=p.code, cash=_n(n)))
    elif result == "owned":
        await cx_reply(T.SP_ALREADY_OWNED.format(code=p.code))
    elif result == "limit":
        await cx_reply(T.SP_LIMIT.format(n=n))
    else:
        await cx_reply(T.NO_FUNDS_TEXT.format(price=_n(U.buy_price(p)[0]), balance=_n(n)))


@registry.command("space_buy", ("شراء كوكب", "اشتري كوكب"), section=S, args="text", usage="الكود",
                  description="تشتري كوكب من البنك المركزي", order=5)
async def cmd_buy(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    p = await _planet_arg(cx, "شراء كوكب 2-1250")
    if p:
        await _reply_buy(cx.reply, cx.services, cx.chat.id, cx.user.id, p, mention(cx.user.id, cx.user.full_name))


@registry.command("space_sell", ("بيع كوكب",), section=S, args="text", usage="الكود",
                  description="تبيع كوكبك للبنك المركزي (85% من سعر السوق)", order=6)
async def cmd_sell(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    p = await _planet_arg(cx, "بيع كوكب 2-1250")
    if p is None:
        return
    result, price = await sell(cx.services, cx.chat.id, cx.user.id, p)
    await cx.reply(T.SP_SOLD.format(name=p.name, code=p.code, price=_n(price)) if result == "ok"
                   else T.SP_NOT_YOURS.format(code=p.code))


@registry.command("space_list", ("عرض كوكب",), section=S, args="text", usage="الكود + السعر",
                  description="تعرض كوكبك للبيع بسوق اللاعبين", order=7)
async def cmd_list(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    p = U.parse_code(cx.args[0]) if cx.args else None
    raw = (cx.args[1] if len(cx.args) > 1 else "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")).replace(",", "")
    if p is None or not raw.isdigit():
        await cx.reply(T.SP_LIST_HOW)
        return
    price = int(raw)
    if not 10 <= price <= U.market_price(p) * LIST_MAX_MULT:
        await cx.reply(T.SP_LIST_RANGE.format(hi=_n(U.market_price(p) * LIST_MAX_MULT)))
        return
    n = await cx.services.db.execute("UPDATE space_planets SET listed = ? WHERE chat_id = ? AND galaxy = ? AND idx = ? "
                                     "AND owner_id = ?", (price, cx.chat.id, p.galaxy, p.idx, cx.user.id))
    if not n:
        await cx.reply(T.SP_NOT_YOURS.format(code=p.code))
        return
    await cx.reply(T.SP_LISTED.format(name=p.name, code=p.code, price=_n(price), fee=LIST_FEE))


@registry.command("space_unlist", ("الغاء عرض كوكب", "سحب عرض كوكب"), section=S, args="text", usage="الكود",
                  description="تسحب كوكبك من سوق اللاعبين", order=8)
async def cmd_unlist(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    p = await _planet_arg(cx, "الغاء عرض كوكب 2-1250")
    if p is None:
        return
    n = await cx.services.db.execute("UPDATE space_planets SET listed = NULL WHERE chat_id = ? AND galaxy = ? "
                                     "AND idx = ? AND owner_id = ? AND listed IS NOT NULL",
                                     (cx.chat.id, p.galaxy, p.idx, cx.user.id))
    await cx.reply(T.SP_UNLISTED.format(code=p.code) if n else T.SP_NOT_LISTED)


async def my_planets_text(svc: Services, chat_id: int, user_id: int, who: str) -> tuple[str, InlineKeyboardMarkup | None]:
    planets = await owned_by(svc, chat_id, user_id)
    if not planets:
        return T.SP_MINE_EMPTY.format(who=who), None
    value = sum(U.market_price(p) for p in planets)
    income = sum(p.income for p in planets)
    planets.sort(key=lambda p: -U.market_price(p))
    lines = [T.SP_MINE_HEAD.format(who=who, n=len(planets), value=_n(value), income=_n(income)), T.LINE]
    for i, p in enumerate(planets[:25], 1):
        lines.append(f"{i}. {B.RARITIES[p.rarity][1]} <b>{p.name}</b> <code>{p.code}</code> ⋅ {_n(U.market_price(p))} 🌸")
    if len(planets) > 25:
        lines.append(T.STAFF_MORE.format(n=len(planets) - 25))
    kb = [Btn(f"🪐 {p.name}", callback_data=f"sp:v:{p.galaxy}:{p.idx}") for p in planets[:8]]
    return "\n".join(lines), InlineKeyboardMarkup([kb[i:i + 2] for i in range(0, len(kb), 2)])


@registry.command("space_mine", ("كواكبي", "امبراطوريتي", "إمبراطوريتي"), section=S,
                  description="كواكبك وقيمتها ودخلها اليومي", order=9)
async def cmd_mine(cx: CommandContext) -> None:
    if await _guard(cx):
        text, kb = await my_planets_text(cx.services, cx.chat.id, cx.user.id, mention(cx.user.id, cx.user.full_name))
        await cx.reply(text, reply_markup=kb)


@registry.command("space_theirs", ("كواكبه", "كواكبها"), section=S, description="كواكب عضو (بالرد)", order=10)
async def cmd_theirs(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    reply = cx.message.reply_to_message
    if reply is None or reply.from_user is None:
        await cx.reply(T.BANK_NEED_REPLY.format(cmd="كواكبه"))
        return
    u = reply.from_user
    text, kb = await my_planets_text(cx.services, cx.chat.id, u.id, mention(u.id, u.full_name))
    await cx.reply(text, reply_markup=kb)


def sales_text() -> str:
    lines = [T.SP_SALES_HEAD, T.LINE]
    for g, off in U.sales().items():
        gal = U.galaxy(g)
        lines.append(T.SP_SALE_LINE.format(g=f"{gal.emoji} {gal.name}", num=gal.num, off=off))
    lines += [T.LINE, T.SP_SALES_LEFT.format(left=duration(U.sale_left())), T.SP_SALES_TIP]
    return "\n".join(lines)


@registry.command("space_sales", ("التخفيضات", "تخفيضات", "تخفيضات الكون"), section=S,
                  description="المجرات اللي عليها تخفيض هسه، ووقت التخفيض الجاي ⏳", order=11)
async def cmd_sales(cx: CommandContext) -> None:
    if await _guard(cx):
        await cx.reply(sales_text())


async def market_text(svc: Services, chat_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    rows = await svc.db.fetchall("SELECT galaxy, idx, owner_id, listed FROM space_planets WHERE chat_id = ? "
                                 "AND listed IS NOT NULL ORDER BY listed LIMIT 15", (chat_id,))
    if not rows:
        return f"{T.SP_MARKET_HEAD}\n{T.LINE}\n{T.SP_MARKET_EMPTY}", None
    lines, kb = [T.SP_MARKET_HEAD, T.LINE], []
    for i, r in enumerate(rows, 1):
        p = U.planet(r["galaxy"], r["idx"])
        lines.append(f"{i}. {B.RARITIES[p.rarity][1]} <b>{p.name}</b> <code>{p.code}</code> ⋅ "
                     f"<b>{_n(r['listed'])}</b> 🌸 ⋅ {await _name(svc, r['owner_id'])}")
        kb.append(Btn(f"🪐 {p.name} ⋅ {_n(r['listed'])}", callback_data=f"sp:v:{p.galaxy}:{p.idx}"))
    return "\n".join(lines), InlineKeyboardMarkup([kb[i:i + 2] for i in range(0, len(kb), 2)])


@registry.command("space_market", ("سوق الكواكب", "سوق الكون"), section=S,
                  description="كواكب اللاعبين المعروضة للبيع 🛍", order=12)
async def cmd_market(cx: CommandContext) -> None:
    if await _guard(cx):
        text, kb = await market_text(cx.services, cx.chat.id)
        await cx.reply(text, reply_markup=kb)


async def emperors_text(svc: Services, chat_id: int) -> str:
    rows = await svc.db.fetchall("SELECT owner_id, galaxy, idx FROM space_planets WHERE chat_id = ?", (chat_id,))
    totals: dict[int, list[int]] = {}
    for r in rows:
        p = U.planet(r["galaxy"], r["idx"])
        t = totals.setdefault(r["owner_id"], [0, 0])
        t[0] += U.market_price(p)
        t[1] += 1
    head = f"{T.SP_EMPERORS_HEAD}\n{T.LINE}"
    if not totals:
        return f"{head}\n{T.LEADERBOARD_EMPTY}"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    best = sorted(totals.items(), key=lambda kv: -kv[1][0])[:10]
    lines = [f"{medals[i]} {await _name(svc, uid)} ⋅ <b>{_n(v)}</b> 🌸 ⋅ 🪐 {c}" for i, (uid, (v, c)) in enumerate(best)]
    return head + "\n" + "\n".join(lines)


@registry.command("space_emperors", ("اباطرة الكون", "أباطرة الكون", "توب الكون", "توب الكواكب"), section=S,
                  description="أكبر 10 إمبراطوريات كونية 👑", order=13)
async def cmd_emperors(cx: CommandContext) -> None:
    if await _guard(cx):
        await cx.reply(await emperors_text(cx.services, cx.chat.id))


async def planets_income(svc: Services, chat_id: int, user_id: int) -> int:
    return sum(p.income for p in await owned_by(svc, chat_id, user_id))


@registry.command("cosmic_fact", ("معلومة كونية", "معلومه كونيه", "معلومة فضائية", "حقيقة كونية"), section=S,
                  description="معلومة حقيقية عن الفضاء والكون 🔭", where="any", order=20)
async def cmd_cosmic_fact(cx: CommandContext) -> None:
    await cx.reply(f"{T.SP_FACT_TITLE}\n{T.LINE}\n{random.choice(B.COSMIC_FACTS)}")


@registry.command("random_fact", ("معلومة", "معلومه", "معلومة عشوائية", "معلومه عشوائيه", "هل تعلم"), section="social",
                  description="معلومة عامة حقيقية 💡", where="any", order=60)
async def cmd_fact(cx: CommandContext) -> None:
    await cx.reply(f"{T.FACT_TITLE}\n{T.LINE}\n{random.choice(B.FACTS)}")


# ── الأزرار ─────────────────────────────────────────
async def _edit_markup(msg: Message, kb) -> None:
    try:
        await msg.edit_reply_markup(reply_markup=kb)
    except BadRequest:
        pass


async def on_button(q, msg: Message, svc: Services, bot, action: str, g_raw: str, i_raw: str) -> None:
    chat_id, uid, user = msg.chat.id, q.from_user.id, q.from_user
    if not g_raw.isdigit() or not i_raw.isdigit():
        await q.answer()
        return
    if not await economy.enabled(svc, chat_id):
        await q.answer(T.ECONOMY_OFF.replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    gnum, idx = int(g_raw), int(i_raw)
    p = U.planet(gnum, idx) if action in "vbsSxm" else None
    if action in "vbsSxm" and p is None:
        await q.answer()
        return
    who = mention(uid, user.full_name)

    if action == "v":
        await q.answer()
        await send_planet(bot, svc, chat_id, p)
    elif action == "e":
        if not _explore_limiter.hit((chat_id, uid)):
            await q.answer(T.SP_EXPLORE_SLOW, show_alert=True)
            return
        await q.answer("🔭")
        await send_planet(bot, svc, chat_id, U.random_planet(gnum=gnum or None))
    elif action == "g":
        g = U.galaxy(gnum)
        await q.answer()
        if g:
            await send_galaxy(bot, svc, chat_id, g)
    elif action == "r":
        g = U.galaxy(gnum)
        rarity = "legendary" if idx == 0 else "epic"
        await q.answer()
        picks = U.rarest(gnum, rarity, 30)
        free = []
        for i in picks:
            pl = U.planet(gnum, i)
            if await owner_row(svc, chat_id, pl) is None:
                free.append(pl)
            if len(free) >= 8:
                break
        if not free:
            await bot.send_message(chat_id, T.SP_RARE_NONE)
            return
        kb = [Btn(f"{B.RARITIES[x.rarity][1]} {x.name} ⋅ {_n(U.buy_price(x)[0])}", callback_data=f"sp:v:{x.galaxy}:{x.idx}")
              for x in free]
        await bot.send_message(chat_id, T.SP_RARE_HEAD.format(rarity=T.SP_BTN_RARE[rarity], g=f"{g.emoji} {g.name}"),
                               reply_markup=InlineKeyboardMarkup([kb[i:i + 2] for i in range(0, len(kb), 2)]))
    elif action == "b":
        result, n = await buy(svc, chat_id, uid, p)
        if result != "ok":
            await q.answer({"owned": T.SP_ALERT_OWNED, "limit": T.SP_ALERT_LIMIT.format(n=n),
                            "funds": T.SP_ALERT_FUNDS.format(price=_n(U.buy_price(p)[0]), have=_n(n))}[result],
                           show_alert=True)
            return
        await q.answer(T.SP_ALERT_BOUGHT)
        row = await owner_row(svc, chat_id, p)
        await _edit_markup(msg, planet_keyboard(p, row, 0))
        await bot.send_message(chat_id, T.SP_BOUGHT.format(who=who, name=p.name, code=p.code, cash=_n(n)))
    elif action == "m":
        result, price, seller = await buy_listed(svc, chat_id, uid, p)
        if result != "ok":
            await q.answer({"not_listed": T.SP_ALERT_NOT_LISTED, "self": T.SP_ALERT_SELF,
                            "limit": T.SP_ALERT_LIMIT.format(n=price),
                            "funds": T.SP_ALERT_FUNDS.format(price="؟", have=_n(price))}[result], show_alert=True)
            return
        await q.answer(T.SP_ALERT_BOUGHT)
        await _edit_markup(msg, planet_keyboard(p, await owner_row(svc, chat_id, p), 0))
        await bot.send_message(chat_id, T.SP_TRADED.format(who=who, seller=await _name(svc, seller), name=p.name,
                                                           code=p.code, price=_n(price)))
    elif action in ("s", "S", "x"):
        row = await owner_row(svc, chat_id, p)
        if row is None or row["owner_id"] != uid:
            await q.answer(T.SP_ALERT_NOT_YOURS, show_alert=True)
            return
        if action == "s":
            await q.answer()
            await _edit_markup(msg, InlineKeyboardMarkup([[
                Btn(T.SP_BTN_SELL_CONFIRM.format(price=_n(U.sell_price(p))), callback_data=f"sp:S:{gnum}:{idx}"),
                Btn(T.PL_BTN_CANCEL, callback_data=f"sp:x:{gnum}:{idx}")]]))
        elif action == "x":
            await q.answer()
            await _edit_markup(msg, planet_keyboard(p, row, 0))
        else:
            result, price = await sell(svc, chat_id, uid, p)
            await q.answer(T.SP_ALERT_SOLD if result == "ok" else T.SP_ALERT_NOT_YOURS, show_alert=result != "ok")
            if result == "ok":
                await _edit_markup(msg, planet_keyboard(p, None, U.buy_price(p)[0]))
                await bot.send_message(chat_id, T.SP_SOLD.format(name=p.name, code=p.code, price=_n(price)))
    elif action == "u":
        await q.answer()
        text, kb = await universe_view(svc, chat_id, uid)
        await bot.send_message(chat_id, text, reply_markup=kb)
    elif action == "k":
        await q.answer()
        text, kb = await my_planets_text(svc, chat_id, uid, who)
        await bot.send_message(chat_id, text, reply_markup=kb)
    elif action == "t":
        await q.answer()
        await bot.send_message(chat_id, sales_text())
    elif action == "q":
        await q.answer()
        text, kb = await market_text(svc, chat_id)
        await bot.send_message(chat_id, text, reply_markup=kb)
    elif action == "w":
        await q.answer()
        await bot.send_message(chat_id, await emperors_text(svc, chat_id))
    else:
        await q.answer()
