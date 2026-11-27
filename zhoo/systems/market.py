"""سوق الممتلكات 🏙: سيارات، عقارات، يخوت وطائرات، مجوهرات، شركات.

الأسعار تتحرك كل يوم (المجوهرات أكثر شي تتحرك) ← اشتري رخيص وبيع غالي.
البيع = 90% من سعر السوق اليوم. العقارات والشركات تعطي دخل يومي.
«السوق» بالأزرار ⋅ «شراء لامبورغيني» ⋅ «بيع لامبورغيني 2» ⋅ «املاكي» ⋅ «ثروتي» ⋅ «ارباحي» (دخل الكواكب + الممتلكات).

callback: mk:<فعل>:<قيمة>   c=قسم ⋅ b=شراء ⋅ s=بيع ⋅ h=الرئيسية
"""
from __future__ import annotations

import random
import time
import zlib
from dataclasses import dataclass

from telegram import InlineKeyboardButton as Btn
from telegram import InlineKeyboardMarkup, Message
from telegram.error import BadRequest

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration, mention
from zhoo.core.normalize import normalize
from zhoo.repositories.economy import InsufficientFunds
from zhoo.systems import economy

S = "economy"
SELL_RATE = 0.90
MAX_QTY = 1000
PASSIVE_COOLDOWN = 24 * 3600


@dataclass(frozen=True)
class Item:
    key: str
    name: str
    emoji: str
    cat: str
    base: int
    vol: float          # تذبذب السعر اليومي
    income: float       # نسبة الدخل اليومي من السعر الأساسي
    aliases: tuple[str, ...] = ()


CATS = {"cars": "🚗 السيارات", "estate": "🏠 العقارات", "vehicles": "🛥 يخوت وطائرات",
        "jewels": "💎 المجوهرات", "biz": "🏢 الشركات"}
ITEMS: tuple[Item, ...] = (
    Item("camry", "كامري", "🚗", "cars", 3_000, .08, 0, ("تويوتا كامري", "تويوتا")),
    Item("landcruiser", "لاندكروزر", "🚙", "cars", 9_000, .08, 0, ("لاند كروزر", "جكسارة")),
    Item("gclass", "مرسيدس G", "🚐", "cars", 25_000, .08, 0, ("مرسيدس", "جي كلاس")),
    Item("lambo", "لامبورغيني", "🏎", "cars", 60_000, .10, 0, ("لمبرگيني", "لامبورگيني", "لامبرغيني")),
    Item("bugatti", "بوگاتي", "🏁", "cars", 150_000, .10, 0, ("بوغاتي", "بوجاتي")),
    Item("flat", "شقة ببغداد", "🏢", "estate", 15_000, .05, .006, ("شقة", "شقه")),
    Item("house", "بيت بالمنصور", "🏠", "estate", 40_000, .05, .006, ("بيت",)),
    Item("villa", "فيلا", "🏡", "estate", 90_000, .05, .006, ("فله",)),
    Item("palace", "قصر", "🏰", "estate", 250_000, .05, .006, ("قصور",)),
    Item("tower", "ناطحة سحاب", "🌆", "estate", 900_000, .05, .006, ("ناطحه سحاب", "برج")),
    Item("boat", "زورق", "🚤", "vehicles", 8_000, .08, 0, ("قارب", "بلم")),
    Item("yacht", "يخت", "🛥", "vehicles", 120_000, .08, 0, ()),
    Item("jet", "طائرة خاصة", "🛩", "vehicles", 400_000, .08, 0, ("طياره خاصه", "طائره خاصه", "طيارة")),
    Item("ring", "خاتم ذهب", "💍", "jewels", 1_500, .12, 0, ("خاتم",)),
    Item("rolex", "رولكس", "⌚", "jewels", 12_000, .12, 0, ("ساعة رولكس", "ساعه رولكس")),
    Item("diamond", "ألماسة", "💎", "jewels", 50_000, .15, 0, ("الماسه", "الماسة", "ماسة")),
    Item("crown", "تاج ملكي", "👑", "jewels", 300_000, .15, 0, ("تاج",)),
    Item("cafe", "كوفي شوب", "☕", "biz", 20_000, .06, .015, ("كافيه", "قهوة")),
    Item("restaurant", "مطعم", "🍽", "biz", 60_000, .06, .015, ()),
    Item("mall", "مول", "🛍", "biz", 500_000, .06, .015, ("مول تجاري",)),
)
ITEM_MAP = {i.key: i for i in ITEMS}
_NAMES = {normalize(n): i for i in ITEMS for n in (i.name,) + i.aliases}


def find_item(text: str) -> tuple[Item | None, int]:
    """«لامبورغيني 2» ← (العنصر، 2)"""
    words = (text or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")).split()
    qty = 1
    if words and words[-1].isdigit():
        qty = int(words.pop())
    return _NAMES.get(normalize(" ".join(words))), qty


def _day(ts: float | None = None) -> int:
    return int((ts or time.time()) + 3 * 3600) // 86400


def price(item: Item, ts: float | None = None, day_offset: int = 0) -> int:
    rnd = random.Random(_day(ts) + day_offset + zlib.crc32(item.key.encode()) * 1009)
    return max(10, int(item.base * (1 + rnd.uniform(-item.vol, item.vol))) // 10 * 10)


def change_pct(item: Item) -> float:
    return (price(item) / price(item, day_offset=-1) - 1) * 100


def sell_price(item: Item) -> int:
    return int(price(item) * SELL_RATE) // 10 * 10


def daily_income(item: Item) -> int:
    return int(item.base * item.income)


async def holdings(svc: Services, chat_id: int, user_id: int) -> dict[str, tuple[int, int]]:
    rows = await svc.db.fetchall("SELECT item, qty, paid FROM assets WHERE chat_id = ? AND user_id = ? AND qty > 0",
                                 (chat_id, user_id))
    return {r["item"]: (r["qty"], r["paid"]) for r in rows if r["item"] in ITEM_MAP}


async def buy(svc: Services, chat_id: int, user_id: int, item: Item, qty: int) -> tuple[str, int]:
    have = (await holdings(svc, chat_id, user_id)).get(item.key, (0, 0))[0]
    if qty < 1 or have + qty > MAX_QTY:
        return "qty", MAX_QTY
    total = price(item) * qty
    try:
        async with svc.db.transaction() as conn:
            balance = await svc.economy.change_in(conn, chat_id, user_id, -total, "asset_buy", item.key)
            await conn.execute(
                "INSERT INTO assets (chat_id, user_id, item, qty, paid) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (chat_id, user_id, item) DO UPDATE SET qty = qty + ?, paid = paid + ?",
                (chat_id, user_id, item.key, qty, total, qty, total))
    except InsufficientFunds as e:
        return "funds", e.args[0]
    return "ok", balance


async def sell(svc: Services, chat_id: int, user_id: int, item: Item, qty: int) -> tuple[str, int]:
    qty_have, paid = (await holdings(svc, chat_id, user_id)).get(item.key, (0, 0))
    if qty < 1 or qty > qty_have:
        return "none", qty_have
    total = sell_price(item) * qty
    paid_part = paid * qty // qty_have
    async with svc.db.transaction() as conn:
        cur = await conn.execute("UPDATE assets SET qty = qty - ?, paid = paid - ? WHERE chat_id = ? AND user_id = ? "
                                 "AND item = ? AND qty >= ?", (qty, paid_part, chat_id, user_id, item.key, qty))
        if cur.rowcount != 1:
            return "none", 0
        await svc.economy.change_in(conn, chat_id, user_id, total, "asset_sell", item.key)
    return "ok", total


# ── العرض ───────────────────────────────────────────
def _n(x: int) -> str:
    return f"{x:,}"


def _arrow(pct: float) -> str:
    return "🟢 ▲" if pct > 0.05 else "🔴 ▼" if pct < -0.05 else "⚪ ▬"


def home_view() -> tuple[str, InlineKeyboardMarkup]:
    kb = [Btn(label, callback_data=f"mk:c:{key}") for key, label in CATS.items()]
    return T.MK_HOME, InlineKeyboardMarkup([kb[i:i + 2] for i in range(0, len(kb), 2)])


async def cat_view(svc: Services, chat_id: int, user_id: int, cat: str) -> tuple[str, InlineKeyboardMarkup]:
    mine = await holdings(svc, chat_id, user_id)
    lines = [T.title(CATS[cat].split(" ", 1)[1], CATS[cat].split(" ", 1)[0]), T.LINE]
    kb = []
    for it in (i for i in ITEMS if i.cat == cat):
        pct = change_pct(it)
        line = T.MK_LINE.format(emoji=it.emoji, name=it.name, price=_n(price(it)), arrow=_arrow(pct), pct=f"{pct:+.1f}")
        if it.income:
            line += T.MK_LINE_INCOME.format(n=_n(daily_income(it)))
        if it.key in mine:
            line += T.MK_LINE_OWNED.format(n=mine[it.key][0])
        lines.append(line)
        row = [Btn(T.MK_BTN_BUY.format(emoji=it.emoji, name=it.name), callback_data=f"mk:b:{it.key}")]
        if it.key in mine:
            row.append(Btn(T.MK_BTN_SELL.format(price=_n(sell_price(it))), callback_data=f"mk:s:{it.key}"))
        kb.append(row)
    lines += [T.LINE, T.MK_TIP]
    kb.append([Btn(T.MK_BTN_HOME, callback_data="mk:h:0")])
    return "\n".join(lines), InlineKeyboardMarkup(kb)


# ── الأوامر ─────────────────────────────────────────
@registry.command("market", ("السوق", "سوق الممتلكات", "المعرض", "البورصة"), section=S,
                  description="سيارات، عقارات، يخوت، مجوهرات وشركات، وأسعارها تتحرك كل يوم 🏙", order=50)
async def cmd_market(cx: CommandContext) -> None:
    if await economy._guard(cx):
        text, kb = home_view()
        await cx.reply(text, reply_markup=kb)


async def _trade(cx: CommandContext, buying: bool) -> None:
    if not await economy._guard(cx):
        return
    item, qty = find_item(cx.raw_args)
    if item is None:
        await cx.reply(T.MK_ITEM_BAD.format(cmd="شراء" if buying else "بيع"))
        return
    who = mention(cx.user.id, cx.user.full_name)
    if buying:
        result, n = await buy(cx.services, cx.chat.id, cx.user.id, item, qty)
        if result == "ok":
            await cx.reply(T.MK_BOUGHT.format(who=who, qty=qty, emoji=item.emoji, name=item.name,
                                              total=_n(price(item) * qty), cash=_n(n)))
        elif result == "qty":
            await cx.reply(T.MK_QTY_BAD.format(n=MAX_QTY))
        else:
            await cx.reply(T.NO_FUNDS_TEXT.format(price=_n(price(item) * qty), balance=_n(n)))
    else:
        result, n = await sell(cx.services, cx.chat.id, cx.user.id, item, qty)
        if result == "ok":
            await cx.reply(T.MK_SOLD.format(who=who, qty=qty, emoji=item.emoji, name=item.name, total=_n(n)))
        else:
            await cx.reply(T.MK_NOT_OWNED.format(name=item.name, n=n))


async def _buy_cmd(cx): await _trade(cx, True)     # noqa: E704
async def _sell_cmd(cx): await _trade(cx, False)   # noqa: E704


registry.command("market_buy", ("شراء", "اشتري"), section=S, args="text", usage="الاسم + العدد (اختياري)",
                 description="تشتري من السوق: «شراء لامبورغيني» أو «شراء خاتم 3»", order=51)(_buy_cmd)
registry.command("market_sell", ("بيع", "بيعي"), section=S, args="text", usage="الاسم + العدد (اختياري)",
                 description="تبيع للسوق بـ 90% من سعر اليوم", order=52)(_sell_cmd)


@registry.command("assets_mine", ("املاكي", "أملاكي", "ممتلكاتي بالسوق"), section=S,
                  description="أملاكك، قيمتها اليوم، ربحك أو خسارتك 📊", order=53)
async def cmd_assets(cx: CommandContext) -> None:
    if not await economy._guard(cx):
        return
    mine = await holdings(cx.services, cx.chat.id, cx.user.id)
    who = mention(cx.user.id, cx.user.full_name)
    if not mine:
        await cx.reply(T.MK_MINE_EMPTY.format(who=who))
        return
    value = sum(sell_price(ITEM_MAP[k]) * q for k, (q, _) in mine.items())
    paid = sum(p for _, p in mine.values())
    lines = [T.MK_MINE_HEAD.format(who=who), T.LINE]
    for k, (q, _) in sorted(mine.items(), key=lambda kv: -price(ITEM_MAP[kv[0]]) * kv[1][0]):
        it = ITEM_MAP[k]
        lines.append(f"{it.emoji} <b>{it.name}</b> × {q} ⋅ {_n(sell_price(it) * q)} 🌸")
    pl = value - paid
    lines += [T.LINE, T.MK_MINE_TOTAL.format(value=_n(value), pl=f"{pl:+,}", icon="📈" if pl >= 0 else "📉")]
    await cx.reply("\n".join(lines))


async def assets_value(svc: Services, chat_id: int, user_id: int) -> int:
    return sum(sell_price(ITEM_MAP[k]) * q for k, (q, _) in (await holdings(svc, chat_id, user_id)).items())


async def assets_income(svc: Services, chat_id: int, user_id: int) -> int:
    return sum(daily_income(ITEM_MAP[k]) * q for k, (q, _) in (await holdings(svc, chat_id, user_id)).items())


@registry.command("passive_income", ("ارباحي", "أرباحي", "دخل الكواكب", "الدخل اليومي", "دخلي"), section=S,
                  description="تستلم دخل كواكبك وعقاراتك وشركاتك كل 24 ساعة 💰", order=54)
async def cmd_income(cx: CommandContext) -> None:
    from zhoo.systems import bank, space
    if not await economy._guard(cx):
        return
    svc = cx.services
    planets = await space.planets_income(svc, cx.chat.id, cx.user.id)
    assets = await assets_income(svc, cx.chat.id, cx.user.id)
    if planets + assets == 0:
        await cx.reply(T.INCOME_NONE)
        return
    left = await bank.wait_left(svc, cx.chat.id, cx.user.id, "passive")
    if left:
        await cx.reply(T.INCOME_WAIT.format(left=duration(left), total=_n(planets + assets)))
        return
    balance = await svc.economy.change(cx.chat.id, cx.user.id, planets + assets, "passive")
    await bank.set_wait(svc, cx.chat.id, cx.user.id, "passive", PASSIVE_COOLDOWN)
    await cx.reply(T.INCOME_DONE.format(planets=_n(planets), assets=_n(assets), total=_n(planets + assets),
                                        cash=_n(balance)))


@registry.command("net_worth", ("ثروتي", "ثروته", "ثروتها"), section=S,
                  description="ثروتك كلها: الكاش + البنك + الأملاك + الكواكب 💼", order=55)
async def cmd_worth(cx: CommandContext) -> None:
    from zhoo.core import universe as U
    from zhoo.systems import bank, space
    if not await economy._guard(cx):
        return
    reply = cx.message.reply_to_message
    target = reply.from_user if cx.message.text.strip().endswith(("ه", "ها")) and reply and reply.from_user \
        else cx.user
    svc = cx.services
    cash = await bank.cash(svc, cx.chat.id, target.id)
    acc = await bank.account(svc, cx.chat.id, target.id)
    in_bank = acc["balance"] if acc else 0
    assets = await assets_value(svc, cx.chat.id, target.id)
    planets = sum(U.market_price(p) for p in await space.owned_by(svc, cx.chat.id, target.id))
    total = cash + in_bank + assets + planets
    await cx.reply(T.WORTH.format(who=mention(target.id, target.full_name), cash=_n(cash), bank=_n(in_bank),
                                  assets=_n(assets), planets=_n(planets), total=_n(total)))


# ── الأزرار ─────────────────────────────────────────
async def on_button(q, msg: Message, svc: Services, action: str, value: str) -> None:
    chat_id, uid = msg.chat.id, q.from_user.id
    if not await economy.enabled(svc, chat_id):
        await q.answer(T.ECONOMY_OFF.replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    if action == "h":
        await q.answer()
        text, kb = home_view()
    elif action == "c" and value in CATS:
        await q.answer()
        text, kb = await cat_view(svc, chat_id, uid, value)
    elif action in ("b", "s") and value in ITEM_MAP:
        item = ITEM_MAP[value]
        if action == "b":
            result, n = await buy(svc, chat_id, uid, item, 1)
            alert = {"ok": T.MK_ALERT_BOUGHT.format(name=item.name, cash=_n(n)),
                     "qty": T.MK_QTY_BAD.format(n=MAX_QTY).replace(f"{T.BULLET} ", ""),
                     "funds": T.MK_ALERT_FUNDS.format(price=_n(price(item)), have=_n(n))}[result]
        else:
            result, n = await sell(svc, chat_id, uid, item, 1)
            alert = T.MK_ALERT_SOLD.format(name=item.name, total=_n(n)) if result == "ok" else T.MK_ALERT_NONE
        await q.answer(alert, show_alert=result != "ok")
        text, kb = await cat_view(svc, chat_id, uid, item.cat)
    else:
        await q.answer()
        return
    try:
        await msg.edit_text(text, reply_markup=kb)
    except BadRequest:
        pass
