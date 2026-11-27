"""تجارة الأبعاد 🌀 — اشتري مورد رخيص بالبعد اللي ينتجه، سافر، وبيعه غالي بالبعد اللي يطلبه.

- كل بعد يبيع بس موارده (×0.7)، ويشتري أي مورد: اللي يطلبه بـ ×1.45، والباقي ×1.0 (ناقص 8% فرق البيع).
- الأسعار تتحرك كل ساعة (±15%).
- السفر ياخذ دقايق ورسوم، وبالطريق ممكن قراصنة 🏴‍☠️ أو عاصفة أو كنز أو تاجر غريب.
- المخزن يبدي بـ 10 وحدات، ويتوسع بأمر «توسيع المخزن».

الحالة: dim_state (وين انت، ومتى توصل، والحدث المنتظر) ⋅ dim_cargo (حمولتك).
callback: dm:<فعل>:<قيمة>   t=سفر ⋅ b=شراء وحدة ⋅ s=بيع وحدة ⋅ m=السوق ⋅ h=الرئيسية ⋅ c=المخزن
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from telegram import InlineKeyboardButton as Btn
from telegram import InlineKeyboardMarkup, Message
from telegram.error import BadRequest, TelegramError

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services, get_services
from zhoo.core.fmt import duration, mention
from zhoo.core.normalize import normalize
from zhoo.data import dims_bank as D
from zhoo.database.db import now
from zhoo.repositories.economy import InsufficientFunds
from zhoo.systems import economy

S = "space"
PRODUCE, DEMAND, SPREAD = 0.70, 1.45, 0.92
HOUR_SWING = 0.15
START_CAP, CAP_STEP, CAP_MAX = 10, 10, 200
HOME = "earth"


@dataclass(frozen=True)
class Dim:
    key: str
    name: str
    emoji: str
    about: str
    minutes: int
    fee: int
    risk: float
    produces: tuple[str, ...]
    demands: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.name}"


@dataclass(frozen=True)
class Res:
    key: str
    name: str
    emoji: str
    about: str
    base: int

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.name}"


DIMS = {d[0]: Dim(*d) for d in D.DIMENSIONS}
RES = {r[0]: Res(*r) for r in D.RESOURCES}
_RES_NAMES = {normalize(r.name): r for r in RES.values()}
_DIM_NAMES = {normalize(d.name): d for d in DIMS.values()}
for _d in DIMS.values():
    _DIM_NAMES[normalize(_d.name.replace("البعد ", "").replace("بعد ", ""))] = _d


def find_res(text: str) -> Res | None:
    return _RES_NAMES.get(normalize(text or ""))


def find_dim(text: str) -> Dim | None:
    t = normalize((text or "").strip())
    return _DIM_NAMES.get(t) or next((d for k, d in _DIM_NAMES.items() if t and t in k), None)


def upgrade_cost(cap: int) -> int:
    return int(3000 * (1.8 ** ((cap - START_CAP) // CAP_STEP)))


# ── الأسعار ─────────────────────────────────────────
def _swing(dim: str, res: str, ts: float | None = None) -> float:
    hour = int((ts or time.time()) // 3600)
    seed = hour * 7_919 + sum(map(ord, dim)) * 131 + sum(map(ord, res))
    return random.Random(seed).uniform(1 - HOUR_SWING, 1 + HOUR_SWING)


def buy_price(dim: Dim, res: Res, ts: float | None = None) -> int | None:
    """سعر الشراء من البعد (بس للموارد اللي ينتجها)."""
    if res.key not in dim.produces:
        return None
    return max(1, int(res.base * PRODUCE * _swing(dim.key, res.key, ts)))


def sell_price(dim: Dim, res: Res, ts: float | None = None) -> int:
    m = DEMAND if res.key in dim.demands else PRODUCE if res.key in dim.produces else 1.0
    return max(1, int(res.base * m * _swing(dim.key, res.key, ts) * SPREAD))


# ── الحالة ──────────────────────────────────────────
async def state(svc: Services, chat_id: int, user_id: int) -> dict:
    row = await svc.db.fetchone("SELECT * FROM dim_state WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    if row is None:
        return {"dim": HOME, "arrive_at": 0, "cap": START_CAP, "event": None, "dest": None}
    return dict(row)


async def _save_state(conn, chat_id: int, user_id: int, st: dict) -> None:
    await conn.execute(
        "INSERT INTO dim_state (chat_id, user_id, dim, arrive_at, cap, event, dest) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (chat_id, user_id) DO UPDATE SET dim = excluded.dim, arrive_at = excluded.arrive_at, "
        "cap = excluded.cap, event = excluded.event, dest = excluded.dest",
        (chat_id, user_id, st["dim"], st["arrive_at"], st["cap"], st["event"], st["dest"]))


async def cargo(svc: Services, chat_id: int, user_id: int) -> dict[str, tuple[int, int]]:
    rows = await svc.db.fetchall("SELECT res, qty, paid FROM dim_cargo WHERE chat_id = ? AND user_id = ? AND qty > 0",
                                 (chat_id, user_id))
    return {r["res"]: (r["qty"], r["paid"]) for r in rows if r["res"] in RES}


def _load(c: dict[str, tuple[int, int]]) -> int:
    return sum(q for q, _ in c.values())


async def settle(svc: Services, chat_id: int, user_id: int) -> tuple[dict, str | None]:
    """إذا الرحلة خلصت: نوصل ونطبق حدث الطريق. يرجع (الحالة، نص الحدث إذا صار هسه)."""
    st = await state(svc, chat_id, user_id)
    if not st["dest"] or st["arrive_at"] > now():
        return st, None
    # نحجز الوصول ذرياً، حتى لو وصلت رسالتين سوا الحدث ما يتطبق مرتين
    claimed = await svc.db.execute(
        "UPDATE dim_state SET dim = dest, dest = NULL, event = NULL, arrive_at = 0 "
        "WHERE chat_id = ? AND user_id = ? AND dest = ? AND arrive_at = ?",
        (chat_id, user_id, st["dest"], st["arrive_at"]))
    trip = dict(st)
    st.update(dim=st["dest"], dest=None, event=None, arrive_at=0)
    if claimed != 1:
        return await state(svc, chat_id, user_id), None
    return st, await _apply_event(svc, chat_id, user_id, trip)


async def _apply_event(svc: Services, chat_id: int, user_id: int, st: dict) -> str:
    dest = DIMS[st["dest"]]
    event = st["event"] or "calm"
    c = await cargo(svc, chat_id, user_id)
    if event == "pirates" and c:
        pct = random.Random(st["arrive_at"]).randint(20, 50)
        lost = []
        async with svc.db.transaction() as conn:
            for key, (q, paid) in c.items():
                take = q * pct // 100
                if take:
                    await conn.execute("UPDATE dim_cargo SET qty = qty - ?, paid = paid - ? WHERE chat_id = ? "
                                       "AND user_id = ? AND res = ?", (take, paid * take // q, chat_id, user_id, key))
                    lost.append(f"{RES[key].emoji}×{take}")
        return T.DM_EV_PIRATES.format(pct=pct, lost=" ".join(lost) or T.NONE_VALUE, dim=dest.label)
    if event == "treasure":
        r = random.Random(st["arrive_at"] + 1)
        res = r.choice([x for x in RES.values() if x.base <= 600])
        qty = r.randint(1, 3)
        await _add_cargo(svc, chat_id, user_id, res.key, qty, 0, st["cap"])
        return T.DM_EV_TREASURE.format(res=res.label, qty=qty, dim=dest.label)
    if event == "merchant":
        gift = random.Random(st["arrive_at"] + 2).randint(100, 600)
        await svc.economy.change(chat_id, user_id, gift, "dim_event")
        return T.DM_EV_MERCHANT.format(n=f"{gift:,}", dim=dest.label)
    if event == "storm":
        return T.DM_EV_STORM.format(dim=dest.label)
    return T.DM_EV_CALM.format(dim=dest.label)


async def _add_cargo(svc: Services, chat_id: int, user_id: int, res: str, qty: int, paid: int, cap: int) -> int:
    """يضيف للمخزن بحدود السعة، ويرجع اللي انضاف فعلاً."""
    free = cap - _load(await cargo(svc, chat_id, user_id))
    qty = max(0, min(qty, free))
    if qty:
        await svc.db.execute(
            "INSERT INTO dim_cargo (chat_id, user_id, res, qty, paid) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (chat_id, user_id, res) DO UPDATE SET qty = qty + ?, paid = paid + ?",
            (chat_id, user_id, res, qty, paid, qty, paid))
    return qty


# ── العمليات ────────────────────────────────────────
async def buy(svc: Services, chat_id: int, user_id: int, res: Res, qty: int) -> tuple[str, object]:
    st, _ = await settle(svc, chat_id, user_id)
    if st["dest"]:
        return "travelling", st["arrive_at"] - now()
    dim = DIMS[st["dim"]]
    price = buy_price(dim, res)
    if price is None:
        return "not_here", dim
    c = await cargo(svc, chat_id, user_id)
    free = st["cap"] - _load(c)
    if qty < 1 or qty > free:
        return "cap", free
    total = price * qty
    try:
        async with svc.db.transaction() as conn:
            balance = await svc.economy.change_in(conn, chat_id, user_id, -total, "dim_buy", res.key)
            await conn.execute(
                "INSERT INTO dim_cargo (chat_id, user_id, res, qty, paid) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (chat_id, user_id, res) DO UPDATE SET qty = qty + ?, paid = paid + ?",
                (chat_id, user_id, res.key, qty, total, qty, total))
    except InsufficientFunds as e:
        return "funds", e.args[0]
    return "ok", (total, balance)


async def sell(svc: Services, chat_id: int, user_id: int, res: Res, qty: int) -> tuple[str, object]:
    st, _ = await settle(svc, chat_id, user_id)
    if st["dest"]:
        return "travelling", st["arrive_at"] - now()
    have, paid = (await cargo(svc, chat_id, user_id)).get(res.key, (0, 0))
    if qty < 1 or qty > have:
        return "none", have
    dim = DIMS[st["dim"]]
    total = sell_price(dim, res) * qty
    cost = paid * qty // have
    async with svc.db.transaction() as conn:
        cur = await conn.execute("UPDATE dim_cargo SET qty = qty - ?, paid = paid - ? WHERE chat_id = ? AND user_id = ? "
                                 "AND res = ? AND qty >= ?", (qty, cost, chat_id, user_id, res.key, qty))
        if cur.rowcount != 1:
            return "none", 0
        balance = await svc.economy.change_in(conn, chat_id, user_id, total, "dim_sell", res.key)
    return "ok", (total, total - cost, balance)


async def travel(svc: Services, chat_id: int, user_id: int, dest: Dim) -> tuple[str, object]:
    st, _ = await settle(svc, chat_id, user_id)
    if st["dest"]:
        return "travelling", st["arrive_at"] - now()
    if st["dim"] == dest.key:
        return "here", dest
    rnd = random.Random()
    weights = {k: w for k, w in D.TRAVEL_EVENTS}
    weights["pirates"] = int(dest.risk * 100)
    event = rnd.choices(list(weights), weights=list(weights.values()))[0]
    minutes = dest.minutes + (rnd.randint(2, 5) if event == "storm" else 0)
    st.update(dest=dest.key, arrive_at=now() + minutes * 60, event=event)
    try:
        async with svc.db.transaction() as conn:
            await svc.economy.change_in(conn, chat_id, user_id, -dest.fee, "dim_travel", dest.key)
            await _save_state(conn, chat_id, user_id, st)
    except InsufficientFunds as e:
        return "funds", e.args[0]
    return "ok", minutes


async def upgrade(svc: Services, chat_id: int, user_id: int) -> tuple[str, int]:
    st = await state(svc, chat_id, user_id)
    if st["cap"] >= CAP_MAX:
        return "max", CAP_MAX
    cost = upgrade_cost(st["cap"])
    st["cap"] += CAP_STEP
    try:
        async with svc.db.transaction() as conn:
            await svc.economy.change_in(conn, chat_id, user_id, -cost, "dim_upgrade")
            await _save_state(conn, chat_id, user_id, st)
    except InsufficientFunds as e:
        return "funds", e.args[0]
    return "ok", st["cap"]


# ── العرض ───────────────────────────────────────────
def _n(x: int) -> str:
    return f"{x:,}"


async def home_view(svc: Services, chat_id: int, user_id: int, who: str, note: str | None = None):
    st, arrived = await settle(svc, chat_id, user_id)
    c = await cargo(svc, chat_id, user_id)
    lines = [T.DM_HOME_HEAD, T.LINE]
    if arrived:
        lines += [arrived, T.LINE]
    if note:
        lines += [note, T.LINE]
    if st["dest"]:
        lines.append(T.DM_TRAVELLING.format(who=who, dest=DIMS[st["dest"]].label, left=duration(st["arrive_at"] - now())))
    else:
        dim = DIMS[st["dim"]]
        lines.append(T.DM_HERE.format(who=who, dim=dim.label, about=dim.about))
    lines.append(T.DM_CARGO_LINE.format(load=_load(c), cap=st["cap"]))
    lines += [T.LINE, T.DM_HOME_TIP]
    kb = [Btn(f"{d.emoji} {d.name}", callback_data=f"dm:t:{d.key}") for d in DIMS.values()
          if d.key != st["dim"] or st["dest"]]
    rows = [kb[i:i + 2] for i in range(0, len(kb), 2)]
    rows.append([Btn(T.DM_BTN_MARKET, callback_data="dm:m:0"), Btn(T.DM_BTN_CARGO, callback_data="dm:c:0")])
    return "\n".join(lines), InlineKeyboardMarkup(rows)


async def market_view(svc: Services, chat_id: int, user_id: int, note: str | None = None):
    st, arrived = await settle(svc, chat_id, user_id)
    if st["dest"]:
        return T.DM_TRAVELLING.format(who="", dest=DIMS[st["dest"]].label, left=duration(st["arrive_at"] - now())), \
            InlineKeyboardMarkup([[Btn(T.DM_BTN_HOME, callback_data="dm:h:0")]])
    dim = DIMS[st["dim"]]
    c = await cargo(svc, chat_id, user_id)
    lines = [T.title(f"سُـوق {dim.name}", dim.emoji), T.LINE]
    if arrived:
        lines += [arrived, T.LINE]
    if note:
        lines += [note, T.LINE]
    lines.append(T.DM_MK_SELLS)
    kb = []
    for key in dim.produces:
        r = RES[key]
        lines.append(T.DM_MK_LINE.format(res=r.label, price=_n(buy_price(dim, r))))
        kb.append([Btn(T.DM_BTN_BUY.format(res=r.label, price=_n(buy_price(dim, r))), callback_data=f"dm:b:{key}")])
    lines.append(T.DM_MK_WANTS)
    for key in dim.demands:
        r = RES[key]
        lines.append(T.DM_MK_LINE_HOT.format(res=r.label, price=_n(sell_price(dim, r))))
    if c:
        lines.append(T.DM_MK_YOURS)
        for key, (q, _) in c.items():
            r = RES[key]
            lines.append(T.DM_MK_LINE_MINE.format(res=r.label, qty=q, price=_n(sell_price(dim, r))))
            kb.append([Btn(T.DM_BTN_SELL.format(res=r.label, price=_n(sell_price(dim, r))), callback_data=f"dm:s:{key}")])
    lines += [T.LINE, T.DM_CARGO_LINE.format(load=_load(c), cap=st["cap"]), T.DM_MK_TIP]
    kb.append([Btn(T.DM_BTN_HOME, callback_data="dm:h:0"), Btn(T.DM_BTN_CARGO, callback_data="dm:c:0")])
    return "\n".join(lines), InlineKeyboardMarkup(kb)


async def cargo_view(svc: Services, chat_id: int, user_id: int, who: str):
    st, _ = await settle(svc, chat_id, user_id)
    c = await cargo(svc, chat_id, user_id)
    lines = [T.DM_CARGO_HEAD.format(who=who), T.LINE]
    if not c:
        lines.append(T.DM_CARGO_EMPTY)
    here = DIMS[st["dim"]] if not st["dest"] else None
    for key, (q, paid) in c.items():
        r = RES[key]
        value = f" ⋅ هنا: <b>{_n(sell_price(here, r) * q)}</b> 🌸" if here else ""
        lines.append(f"{r.label} × <b>{q}</b> ⋅ دافع {_n(paid)}{value}")
    lines += [T.LINE, T.DM_CARGO_LINE.format(load=_load(c), cap=st["cap"])]
    if st["cap"] < CAP_MAX:
        lines.append(T.DM_UPGRADE_HINT.format(cost=_n(upgrade_cost(st["cap"])), step=CAP_STEP))
    return "\n".join(lines), InlineKeyboardMarkup([[Btn(T.DM_BTN_HOME, callback_data="dm:h:0"),
                                                    Btn(T.DM_BTN_MARKET, callback_data="dm:m:0")]])


def _result_text(kind: str, result: str, value, res: Res | None = None, qty: int = 1) -> str:
    if result == "travelling":
        return T.DM_ERR_TRAVELLING.format(left=duration(value))
    if result == "funds":
        return T.DM_ERR_FUNDS.format(have=_n(value))
    if result == "not_here":
        return T.DM_ERR_NOT_HERE.format(res=res.label, dim=value.label)
    if result == "cap":
        return T.DM_ERR_CAP.format(free=value)
    if result == "none":
        return T.DM_ERR_NONE.format(res=res.label if res else "", have=value)
    if kind == "buy":
        total, balance = value
        return T.DM_BOUGHT.format(qty=qty, res=res.label, total=_n(total), cash=_n(balance))
    total, profit, balance = value
    return T.DM_SOLD.format(qty=qty, res=res.label, total=_n(total), profit=f"{profit:+,}",
                            icon="📈" if profit >= 0 else "📉", cash=_n(balance))


# ── الأوامر ─────────────────────────────────────────
@registry.command("dims", ("الابعاد", "الأبعاد", "تجارة الابعاد", "تجارة الأبعاد", "بين الابعاد"), section=S,
                  description="تجارة بين 7 أبعاد بـ 12 مورد نادر 🌀", order=30)
async def cmd_dims(cx: CommandContext) -> None:
    if await economy._guard(cx):
        await _reply_view(cx, await home_view(cx.services, cx.chat.id, cx.user.id, mention(cx.user.id, cx.user.full_name)))


async def _reply_view(cx: CommandContext, view) -> None:
    text, kb = view
    await cx.reply(text, reply_markup=kb)


@registry.command("dims_market", ("سوق البعد", "سوق الابعاد", "سوق الأبعاد"), section=S,
                  description="أسعار البعد اللي انت بيه: شنو يبيع وشنو يطلب", order=31)
async def cmd_dims_market(cx: CommandContext) -> None:
    if await economy._guard(cx):
        await _reply_view(cx, await market_view(cx.services, cx.chat.id, cx.user.id))


@registry.command("dims_cargo", ("مخزني", "حمولتي", "المخزن"), section=S,
                  description="الموارد اللي تحملها وقيمتها بالبعد الحالي", order=32)
async def cmd_cargo(cx: CommandContext) -> None:
    if await economy._guard(cx):
        await _reply_view(cx, await cargo_view(cx.services, cx.chat.id, cx.user.id, mention(cx.user.id, cx.user.full_name)))


@registry.command("dims_travel", ("سافر", "سفر", "سافر الى", "سافر إلى"), section=S, args="text", usage="اسم البعد",
                  description="تسافر لبعد ثاني (ياخذ دقايق ورسوم)", order=33)
async def cmd_travel(cx: CommandContext) -> None:
    if not await economy._guard(cx):
        return
    dest = find_dim(cx.raw_args)
    if dest is None:
        await cx.reply(T.DM_DIM_BAD.format(names=" ⋅ ".join(d.name for d in DIMS.values())))
        return
    await cx.reply(await _travel_text(cx.context, cx.services, cx.chat.id, cx.user.id, cx.user.full_name, dest))


async def _travel_text(context, svc: Services, chat_id: int, uid: int, name: str, dest: Dim) -> str:
    result, value = await travel(svc, chat_id, uid, dest)
    if result == "here":
        return T.DM_ERR_HERE.format(dim=dest.label)
    if result != "ok":
        return _result_text("travel", result, value)
    jq = getattr(context, "job_queue", None)
    if jq is not None:
        jq.run_once(_arrival_job, value * 60 + 2, data=(chat_id, uid, name))
    return T.DM_DEPARTED.format(who=mention(uid, name), dim=dest.label, minutes=value, fee=_n(dest.fee))


async def _arrival_job(context) -> None:
    chat_id, uid, name = context.job.data
    svc = get_services(context)
    _, note = await settle(svc, chat_id, uid)
    if note:
        try:
            await context.bot.send_message(chat_id, f"{mention(uid, name)}\n{note}", disable_notification=True)
        except TelegramError:
            pass


@registry.command("dims_upgrade", ("توسيع المخزن", "تكبير المخزن"), section=S,
                  description=f"يزيد مخزنك {CAP_STEP} وحدات 📦", order=34)
async def cmd_upgrade(cx: CommandContext) -> None:
    if not await economy._guard(cx):
        return
    result, value = await upgrade(cx.services, cx.chat.id, cx.user.id)
    if result == "ok":
        await cx.reply(T.DM_UPGRADED.format(cap=value))
    elif result == "max":
        await cx.reply(T.DM_UPGRADE_MAX.format(cap=value))
    else:
        st = await state(cx.services, cx.chat.id, cx.user.id)
        await cx.reply(T.NO_FUNDS_TEXT.format(price=_n(upgrade_cost(st["cap"])), balance=_n(value)))


async def trade_command(cx: CommandContext, buying: bool, res: Res, qty: int) -> None:
    """يُنادى من «شراء» و«بيع» العامة إذا الاسم مورد أبعاد."""
    fn = buy if buying else sell
    result, value = await fn(cx.services, cx.chat.id, cx.user.id, res, qty)
    await cx.reply(_result_text("buy" if buying else "sell", result, value, res, qty))


# ── الأزرار ─────────────────────────────────────────
async def on_button(q, msg: Message, svc: Services, context, action: str, value: str) -> None:
    chat_id, uid, user = msg.chat.id, q.from_user.id, q.from_user
    if not await economy.enabled(svc, chat_id):
        await q.answer(T.ECONOMY_OFF.replace(f"{T.BULLET} ", ""), show_alert=True)
        return
    who = mention(uid, user.full_name)
    view = None
    if action == "h":
        await q.answer()
        view = await home_view(svc, chat_id, uid, who)
    elif action == "m":
        await q.answer()
        view = await market_view(svc, chat_id, uid)
    elif action == "c":
        await q.answer()
        view = await cargo_view(svc, chat_id, uid, who)
    elif action == "t" and value in DIMS:
        text = await _travel_text(context, svc, chat_id, uid, user.full_name, DIMS[value])
        await q.answer()
        view = await home_view(svc, chat_id, uid, who, note=text)
    elif action in ("b", "s") and value in RES:
        res = RES[value]
        result, val = await (buy if action == "b" else sell)(svc, chat_id, uid, res, 1)
        text = _result_text("buy" if action == "b" else "sell", result, val, res, 1)
        await q.answer(_plain(text)[:190], show_alert=result != "ok")
        view = await market_view(svc, chat_id, uid)
    else:
        await q.answer()
        return
    try:
        await msg.edit_text(view[0], reply_markup=view[1])
    except BadRequest:
        pass


def _plain(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).replace(f"{T.BULLET} ", "")
