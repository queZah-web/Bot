"""المقايضة 🤝 — بدّل أي شي بأي شي ويه أي شخص: كاش، أملاك، كواكب، موارد الأبعاد.

بالرد على الشخص:
  «مقايضة خاتم 2 مقابل 5000»
  «مقايضة كوكب 2-1250 + 1000 مقابل لامبورغيني»
  «مقايضة رماد العنقاء 3 مقابل ألماسة»
الطرف الثاني يشوف العرض بأزرار «قبول / رفض»، وصاحب العرض يگدر يلغيه. العرض ينتهي بعد 10 دقايق.
التبديل كله بمعاملة وحدة: يا يصير كله، يا ما يصير شي (ولا أحد يخسر نص الصفقة).

«وصف لامبورغيني» ⋅ «وصف رماد العنقاء» ⋅ «وصف بعد الزمن» ⋅ «وصف مجرة بابل» ⋅ «وصف 2-1250».
"""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass, field

from telegram import InlineKeyboardButton as Btn
from telegram import InlineKeyboardMarkup, Message
from telegram.error import BadRequest

from zhoo.core import texts as T
from zhoo.core import universe as U
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.database.db import now
from zhoo.repositories.economy import InsufficientFunds
from zhoo.systems import dims, economy, market, space

S = "economy"
OFFER_TTL = 600
MAX_GOODS = 4
_SPLIT_SIDES = re.compile(r"\s+(?:مقابل|بمقابل|بدل)\s+")
_SPLIT_GOODS = re.compile(r"\s*\+\s*|\s+و\s+")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


class TradeFail(Exception):
    pass


@dataclass(frozen=True)
class Good:
    kind: str           # cash | asset | planet | res
    key: str
    qty: int

    @property
    def label(self) -> str:
        if self.kind == "cash":
            return f"💵 <b>{self.qty:,}</b> 🌸"
        if self.kind == "asset":
            it = market.ITEM_MAP[self.key]
            return f"{it.emoji} {it.name} × <b>{self.qty}</b>"
        if self.kind == "planet":
            p = U.parse_code(self.key)
            return f"🪐 {p.name} <code>{p.code}</code>"
        return f"{dims.RES[self.key].label} × <b>{self.qty}</b>"


@dataclass
class Offer:
    id: str
    chat_id: int
    from_id: int
    to_id: int
    give: list[Good]
    want: list[Good]
    expires: float = field(default_factory=lambda: time.monotonic() + OFFER_TTL)


_offers: dict[str, Offer] = {}


# ── قراءة البضاعة ───────────────────────────────────
def parse_good(text: str) -> Good | None:
    raw = " ".join(text.translate(_DIGITS).replace(",", "").split())
    if not raw:
        return None
    k = raw.lower().rstrip("k")
    if raw.isdigit() or (raw.lower().endswith("k") and k.isdigit()):
        n = int(k) * (1000 if raw.lower().endswith("k") else 1)
        return Good("cash", "cash", n) if n > 0 else None
    words = raw.split()
    if words[0] in ("كوكب", "الكوكب") and len(words) == 2:
        words = words[1:]
    p = U.parse_code(" ".join(words))
    if p is not None:
        return Good("planet", p.code, 1)
    item, qty = market.find_item(raw)
    if item is not None:
        return Good("asset", item.key, qty) if qty > 0 else None
    qty = 1
    if words[-1].isdigit():
        qty = int(words.pop())
    res = dims.find_res(" ".join(words))
    if res is not None and qty > 0:
        return Good("res", res.key, qty)
    return None


def parse_side(text: str) -> list[Good] | None:
    parts = [x for x in _SPLIT_GOODS.split(text.strip()) if x.strip()]
    if not parts or len(parts) > MAX_GOODS:
        return None
    goods = [parse_good(x) for x in parts]
    if any(g is None for g in goods):
        return None
    return goods


async def has_goods(svc: Services, chat_id: int, user_id: int, goods: list[Good]) -> Good | None:
    """يرجع أول شي ما يملكه الشخص، أو None إذا عنده كلشي."""
    cash = (await svc.economy.wallet(chat_id, user_id))["balance"]
    assets = await market.holdings(svc, chat_id, user_id)
    cargo = await dims.cargo(svc, chat_id, user_id)
    need_cash = sum(g.qty for g in goods if g.kind == "cash")
    for g in goods:
        if g.kind == "cash" and need_cash > cash:
            return g
        if g.kind == "asset" and assets.get(g.key, (0, 0))[0] < g.qty:
            return g
        if g.kind == "res" and cargo.get(g.key, (0, 0))[0] < g.qty:
            return g
        if g.kind == "planet":
            p = U.parse_code(g.key)
            row = await space.owner_row(svc, chat_id, p)
            if row is None or row["owner_id"] != user_id:
                return g
    return None


# ── التنفيذ الذري ───────────────────────────────────
async def _move(svc: Services, conn, chat_id: int, src: int, dst: int, g: Good) -> None:
    if g.kind == "cash":
        try:
            await svc.economy.change_in(conn, chat_id, src, -g.qty, "barter_out", str(dst))
        except InsufficientFunds:
            raise TradeFail(g)
        await svc.economy.change_in(conn, chat_id, dst, g.qty, "barter_in", str(src))
        return
    if g.kind == "planet":
        p = U.parse_code(g.key)
        cur = await conn.execute("UPDATE space_planets SET owner_id = ?, listed = NULL, bought_at = ? "
                                 "WHERE chat_id = ? AND galaxy = ? AND idx = ? AND owner_id = ?",
                                 (dst, now(), chat_id, p.galaxy, p.idx, src))
        if cur.rowcount != 1:
            raise TradeFail(g)
        cur = await conn.execute("SELECT COUNT(*) FROM space_planets WHERE chat_id = ? AND owner_id = ?", (chat_id, dst))
        if (await cur.fetchone())[0] > space.MAX_PLANETS:
            raise TradeFail(g)
        return
    table, col = ("assets", "item") if g.kind == "asset" else ("dim_cargo", "res")
    cur = await conn.execute(f"SELECT qty, paid FROM {table} WHERE chat_id = ? AND user_id = ? AND {col} = ?",
                             (chat_id, src, g.key))
    row = await cur.fetchone()
    if row is None or row[0] < g.qty:
        raise TradeFail(g)
    paid = row[1] * g.qty // row[0]
    await conn.execute(f"UPDATE {table} SET qty = qty - ?, paid = paid - ? WHERE chat_id = ? AND user_id = ? AND {col} = ?",
                       (g.qty, paid, chat_id, src, g.key))
    await conn.execute(f"INSERT INTO {table} (chat_id, user_id, {col}, qty, paid) VALUES (?, ?, ?, ?, ?) "
                       f"ON CONFLICT (chat_id, user_id, {col}) DO UPDATE SET qty = qty + ?, paid = paid + ?",
                       (chat_id, dst, g.key, g.qty, paid, g.qty, paid))


async def execute(svc: Services, offer: Offer) -> Good | None:
    """ينفذ المقايضة كاملة. يرجع None إذا نجحت، أو الشي اللي ناقص."""
    for side, owner, other in ((offer.give, offer.from_id, offer.to_id), (offer.want, offer.to_id, offer.from_id)):
        res = [g for g in side if g.kind == "res"]
        if res:   # سعة مخزن المستلم
            st = await dims.state(svc, offer.chat_id, other)
            load = sum(q for q, _ in (await dims.cargo(svc, offer.chat_id, other)).values())
            if load + sum(g.qty for g in res) > st["cap"]:
                return res[0]
    try:
        async with svc.db.transaction() as conn:
            for g in offer.give:
                await _move(svc, conn, offer.chat_id, offer.from_id, offer.to_id, g)
            for g in offer.want:
                await _move(svc, conn, offer.chat_id, offer.to_id, offer.from_id, g)
    except TradeFail as e:
        return e.args[0]
    await svc.audit.log("barter", chat_id=offer.chat_id, actor_id=offer.from_id, target_id=offer.to_id,
                        details={"give": [g.__dict__ for g in offer.give], "want": [g.__dict__ for g in offer.want]})
    return None


# ── الأوامر ─────────────────────────────────────────
def _offer_text(o: Offer, a: str, b: str, status: str = "") -> str:
    lines = [T.TR_HEAD, T.LINE, T.TR_FROM.format(who=a), *[f"   {g.label}" for g in o.give],
             T.TR_TO.format(who=b), *[f"   {g.label}" for g in o.want], T.LINE]
    lines.append(status or T.TR_WAITING.format(who=b, minutes=OFFER_TTL // 60))
    return "\n".join(lines)


def _offer_kb(o: Offer) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [Btn(T.TR_BTN_ACCEPT, callback_data=f"tr:a:{o.id}"), Btn(T.TR_BTN_DECLINE, callback_data=f"tr:d:{o.id}")],
        [Btn(T.TR_BTN_CANCEL, callback_data=f"tr:c:{o.id}")],
    ])


@registry.command("barter", ("مقايضة", "مقايضه", "تبادل", "صفقة", "صفقه"), section=S, args="text",
                  usage="بالرد: الشي مقابل الشي", description="بدّل أي شي بأي شي ويه عضو 🤝", order=60)
async def cmd_barter(cx: CommandContext) -> None:
    if not await economy._guard(cx):
        return
    reply = cx.message.reply_to_message
    sides = _SPLIT_SIDES.split(cx.raw_args.strip(), maxsplit=1)
    if reply is None or reply.from_user is None or reply.sender_chat is not None or len(sides) != 2:
        await cx.reply(T.TR_HOW)
        return
    other = reply.from_user
    if other.id == cx.user.id or other.is_bot:
        await cx.reply(T.TR_SELF)
        return
    give, want = parse_side(sides[0]), parse_side(sides[1])
    if give is None or want is None:
        await cx.reply(T.TR_BAD_GOODS)
        return
    svc = cx.services
    missing = await has_goods(svc, cx.chat.id, cx.user.id, give)
    if missing:
        await cx.reply(T.TR_YOU_MISSING.format(good=missing.label))
        return
    if len(_offers) > 2000:
        t = time.monotonic()
        for k in [k for k, o in _offers.items() if o.expires < t]:
            _offers.pop(k, None)
    await svc.users.upsert(other.id, other.first_name, other.last_name, other.username, False)
    offer = Offer(secrets.token_hex(4), cx.chat.id, cx.user.id, other.id, give, want)
    _offers[offer.id] = offer
    await cx.reply(_offer_text(offer, mention(cx.user.id, cx.user.full_name), mention(other.id, other.full_name)),
                   reply_markup=_offer_kb(offer))


async def on_button(q, msg: Message, svc: Services, action: str, offer_id: str) -> None:
    o = _offers.get(offer_id)
    if o is None or o.expires < time.monotonic():
        _offers.pop(offer_id, None)
        await q.answer(T.TR_EXPIRED, show_alert=True)
        try:
            await msg.edit_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        return
    uid = q.from_user.id
    a = await space._name(svc, o.from_id)
    b = await space._name(svc, o.to_id)
    if action == "c":
        if uid != o.from_id:
            await q.answer(T.TR_ONLY_OWNER, show_alert=True)
            return
        status = T.TR_CANCELLED
    elif action in ("a", "d"):
        if uid != o.to_id:
            await q.answer(T.TR_ONLY_TARGET, show_alert=True)
            return
        if action == "d":
            status = T.TR_DECLINED.format(who=b)
        else:
            missing = await has_goods(svc, o.chat_id, o.from_id, o.give)
            if missing:
                status = T.TR_FAIL_FROM.format(who=a, good=missing.label)
            elif (missing := await has_goods(svc, o.chat_id, o.to_id, o.want)) is not None:
                await q.answer(T.TR_YOU_MISSING_ALERT, show_alert=True)
                return
            else:
                missing = await execute(svc, o)
                status = T.TR_DONE if missing is None else T.TR_FAIL.format(good=missing.label)
    else:
        await q.answer()
        return
    _offers.pop(offer_id, None)
    await q.answer()
    try:
        await msg.edit_text(_offer_text(o, a, b, status), reply_markup=None)
    except BadRequest:
        pass


# ── الوصف ───────────────────────────────────────────
def describe(text: str) -> str | None:
    t = " ".join((text or "").split())
    if not t:
        return None
    p = U.parse_code(t.replace("كوكب", "").strip())
    if p is not None:
        from zhoo.data import space_bank as B
        kind = B.PLANET_TYPES[p.kind]
        g = U.galaxy(p.galaxy)
        return T.DESC_PLANET.format(name=p.name, code=p.code, kind=f"{kind[1]} {kind[0]}",
                                    rarity=" ".join(B.RARITIES[p.rarity][:2][::-1]), g=f"{g.emoji} {g.name}",
                                    price=f"{U.market_price(p):,}", income=f"{p.income:,}")
    item, _ = market.find_item(t)
    if item is not None:
        extra = T.DESC_INCOME.format(n=f"{market.daily_income(item):,}") if item.income else ""
        return T.DESC_ITEM.format(emoji=item.emoji, name=item.name, desc=market.DESCS.get(item.key, ""),
                                  cat=market.CATS[item.cat], price=f"{market.price(item):,}",
                                  sell=f"{market.sell_price(item):,}", extra=extra)
    res = dims.find_res(t)
    if res is not None:
        made = " ⋅ ".join(d.label for d in dims.DIMS.values() if res.key in d.produces)
        wanted = " ⋅ ".join(d.label for d in dims.DIMS.values() if res.key in d.demands)
        return T.DESC_RES.format(label=res.label, desc=res.about, base=f"{res.base:,}", made=made, wanted=wanted)
    d = dims.find_dim(t.replace("وصف", ""))
    if d is not None:
        return T.DESC_DIM.format(label=d.label, desc=d.about, minutes=d.minutes, fee=f"{d.fee:,}",
                                 risk=T.DESC_RISK[0 if d.risk < 0.07 else 1 if d.risk < 0.15 else 2],
                                 made=" ⋅ ".join(dims.RES[k].label for k in d.produces),
                                 wanted=" ⋅ ".join(dims.RES[k].label for k in d.demands))
    g = U.find_galaxy(t)
    if g is not None:
        return T.DESC_GALAXY.format(emoji=g.emoji, name=g.name, desc=g.about, n=f"{g.count:,}", mult=g.mult)
    return None


@registry.command("describe", ("وصف", "معلومات عن"), section=S, args="text", usage="اسم أي شي",
                  description="وصف أي شي: سيارة، عقار، مورد، بعد، مجرة، كوكب 📖", where="any", order=61)
async def cmd_describe(cx: CommandContext) -> None:
    text = describe(cx.raw_args)
    await cx.reply(text or T.DESC_NONE.format(q=esc(cx.raw_args.strip()[:40])))
