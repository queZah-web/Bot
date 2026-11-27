"""بنك زهو 🏦 — فلوس افتراضية للمتعة بس (نفس زهرات المحفظة 🌸، ما تنسحب ولا تمثل فلوس حقيقية).

الحساب: «انشاء حساب بنكي» (تختار البطاقة بالأزرار + هدية افتتاح) ⋅ «حسابي» ⋅ «ايداع» ⋅ «سحب» ⋅ «الفائدة».
الفلوس اللي بالبنك محمية من الزرف، واللي بالمحفظة (الكاش) ممكن تنزرف.

الكسب: بخشيش (كل 10 دقايق) ⋅ كنز (كل 3 ساعات) ⋅ عجلة الحظ (كل يوم) ⋅ الفائدة (كل يوم).
المخاطرة: حظ ⋅ استثمار ⋅ مضاربة.
الزرف: «زرف» بالرد ⋅ «حماية» تحميك 6 ساعات ⋅ «توب الحرامية».

كل حركة ذرية وتنسجل بسجل المحفظة، والرصيد ما ينزل تحت الصفر أبداً.
"""
from __future__ import annotations

import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import BadRequest

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration, mention
from zhoo.database.db import now
from zhoo.repositories.economy import InsufficientFunds
from zhoo.systems.economy import _guard, framed

S = "economy"

CARDS = {"zhoo": "💳 زهو كارد", "gold": "🌟 الذهبية", "diamond": "💎 الماسية", "rose": "🌸 الوردية"}
WELCOME_BONUS = 500
MIN_BET, MAX_BET = 50, 500_000
MAX_MOVE = 10_000_000
COOLDOWN = {                       # بالثواني
    "tip": 10 * 60, "treasure": 3 * 3600, "wheel": 24 * 3600, "interest": 24 * 3600,
    "luck": 20, "invest": 10 * 60, "speculate": 5 * 60, "rob": 30 * 60,
}
ROBBED_SAFE = 20 * 60              # اللي انزرف ما ينزرف مرة ثانية خلال 20 دقيقة
SHIELD_PRICE, SHIELD_SECS = 1500, 6 * 3600
ROB_MIN_CASH = 200
ROB_CHANCE = 0.45
ROB_MAX = 20_000
INTEREST_PCT, INTEREST_MAX, INTEREST_MIN_BALANCE = 2, 2000, 500
WHEEL = [  # (النص، المبلغ، الوزن)
    ("50", 50, 22), ("100", 100, 22), ("200", 200, 18), ("300", 300, 14), ("500", 500, 10),
    ("1,000", 1000, 6), ("2,500", 2500, 2), ("shield", 0, 6),
]
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
ALL_WORDS = {"الكل", "كلها", "كله", "كل", "الكلش"}


# ── أساسيات ─────────────────────────────────────────
async def account(svc: Services, chat_id: int, user_id: int):
    return await svc.db.fetchone("SELECT * FROM bank_accounts WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))


async def cash(svc: Services, chat_id: int, user_id: int) -> int:
    return (await svc.economy.wallet(chat_id, user_id))["balance"]


async def wait_left(svc: Services, chat_id: int, user_id: int, key: str) -> int:
    until = await svc.db.fetchval("SELECT until FROM bank_cooldowns WHERE chat_id = ? AND user_id = ? AND key = ?",
                                  (chat_id, user_id, key), default=0)
    return max(0, until - now())


async def set_wait(svc: Services, chat_id: int, user_id: int, key: str, secs: int) -> None:
    await svc.db.execute(
        "INSERT INTO bank_cooldowns (chat_id, user_id, key, until) VALUES (?, ?, ?, ?) "
        "ON CONFLICT (chat_id, user_id, key) DO UPDATE SET until = excluded.until", (chat_id, user_id, key, now() + secs))


def _num(n: int) -> str:
    return f"{n:,}"


def _amount(raw: str, available: int, hi: int) -> int | None:
    """المبلغ من الرسالة: رقم، أو «الكل». None إذا غلط."""
    raw = (raw or "").strip().translate(_DIGITS).replace(",", "").replace("،", "")
    if raw in ALL_WORDS:
        return min(available, hi) if available > 0 else None
    if raw.endswith("k") and raw[:-1].isdigit():
        raw = str(int(raw[:-1]) * 1000)
    if not raw.isdigit() or int(raw) <= 0:
        return None
    return int(raw)


async def _need_account(cx: CommandContext):
    if not await _guard(cx):
        return None
    acc = await account(cx.services, cx.chat.id, cx.user.id)
    if acc is None:
        await cx.reply(T.BANK_NO_ACCOUNT)
    return acc


async def _cooldown(cx: CommandContext, key: str) -> bool:
    """True إذا لازم ينتظر (وتنكتب له المدة)."""
    left = await wait_left(cx.services, cx.chat.id, cx.user.id, key)
    if left:
        await cx.reply(T.BANK_WAIT.format(what=T.BANK_NAMES[key], left=duration(left)))
        return True
    return False


# ── الحساب ──────────────────────────────────────────
def _account_no() -> str:
    digits = "".join(str(random.randint(0, 9)) for _ in range(16))
    return " ".join(digits[i:i + 4] for i in range(0, 16, 4))


def cards_keyboard(uid: int) -> InlineKeyboardMarkup:
    b = [InlineKeyboardButton(name, callback_data=f"bk:{uid}:{key}") for key, name in CARDS.items()]
    return InlineKeyboardMarkup([b[:2], b[2:]])


async def card_text(svc: Services, chat_id: int, user_id: int, name: str, acc) -> str:
    w = await svc.economy.wallet(chat_id, user_id)
    total = w["balance"] + acc["balance"]
    pos = 1 + await svc.db.fetchval(
        "SELECT COUNT(*) FROM wallets w LEFT JOIN bank_accounts b ON b.chat_id = w.chat_id AND b.user_id = w.user_id "
        "WHERE w.chat_id = ? AND w.balance + COALESCE(b.balance, 0) > ?", (chat_id, total), default=0)
    shield = await wait_left(svc, chat_id, user_id, "shield")
    return T.BANK_CARD.format(
        name=framed(w, mention(user_id, name)), card=CARDS.get(acc["card"], CARDS["zhoo"]), no=acc["account_no"],
        cash=_num(w["balance"]), bank=_num(acc["balance"]), total=_num(total), pos=pos,
        shield=T.BANK_SHIELD_ON.format(left=duration(shield)) if shield else T.BANK_SHIELD_OFF)


@registry.command("bank_open", ("انشاء حساب بنكي", "إنشاء حساب بنكي", "فتح حساب بنكي", "انشاء حساب", "فتح حساب"),
                  section=S, description="تفتح حساب ببنك زهو وتختار بطاقتك 💳 (+500 هدية)", order=30)
async def cmd_open(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    acc = await account(cx.services, cx.chat.id, cx.user.id)
    if acc is not None:
        await cx.reply(T.BANK_HAS_ACCOUNT + "\n\n" + await card_text(cx.services, cx.chat.id, cx.user.id,
                                                                     cx.user.full_name, acc))
        return
    await cx.reply(T.BANK_CHOOSE_CARD.format(bonus=WELCOME_BONUS), reply_markup=cards_keyboard(cx.user.id))


@registry.command("bank_card", ("تغيير البطاقة", "تغيير البطاقه", "تغيير بطاقتي"), section=S,
                  description="تبدّل شكل بطاقتك البنكية", order=31)
async def cmd_card(cx: CommandContext) -> None:
    if await _need_account(cx) is not None:
        await cx.reply(T.BANK_CHOOSE_NEW_CARD, reply_markup=cards_keyboard(cx.user.id))


async def on_card_button(q, msg: Message, svc: Services, uid_raw: str, card: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.BANK_NOT_YOURS, show_alert=True)
        return
    if card not in CARDS:
        await q.answer()
        return
    chat_id, uid = msg.chat.id, q.from_user.id
    acc = await account(svc, chat_id, uid)
    if acc is None:
        async with svc.db.transaction() as conn:
            await conn.execute("INSERT OR IGNORE INTO bank_accounts (chat_id, user_id, account_no, card, balance, "
                               "created_at) VALUES (?, ?, ?, ?, 0, ?)", (chat_id, uid, _account_no(), card, now()))
            await svc.economy.change_in(conn, chat_id, uid, WELCOME_BONUS, "bank_bonus")
        await svc.users.upsert(uid, q.from_user.first_name, q.from_user.last_name, q.from_user.username, False)
        await svc.audit.log("bank_open", chat_id=chat_id, actor_id=uid, details={"card": card})
        head = T.BANK_OPENED.format(bonus=WELCOME_BONUS)
    else:
        await svc.db.execute("UPDATE bank_accounts SET card = ? WHERE chat_id = ? AND user_id = ?", (card, chat_id, uid))
        head = T.BANK_CARD_CHANGED
    await q.answer(CARDS[card])
    acc = await account(svc, chat_id, uid)
    try:
        await msg.edit_text(head + "\n\n" + await card_text(svc, chat_id, uid, q.from_user.full_name, acc),
                            reply_markup=None)
    except BadRequest:
        pass


@registry.command("bank_me", ("حسابي", "حسابي البنكي", "بطاقتي", "البطاقة"), section=S,
                  description="بطاقتك البنكية: الكاش، البنك، والترتيب", order=32)
async def cmd_me(cx: CommandContext) -> None:
    acc = await _need_account(cx)
    if acc is not None:
        await cx.reply(await card_text(cx.services, cx.chat.id, cx.user.id, cx.user.full_name, acc))


@registry.command("bank_their", ("حسابه", "حسابها"), section=S, description="بطاقة عضو ثاني (بالرد)", order=33)
async def cmd_their(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    reply = cx.message.reply_to_message
    if reply is None or reply.from_user is None or reply.from_user.is_bot:
        await cx.reply(T.BANK_NEED_REPLY.format(cmd="حسابه"))
        return
    who = reply.from_user
    acc = await account(cx.services, cx.chat.id, who.id)
    if acc is None:
        await cx.reply(T.BANK_THEY_NO_ACCOUNT.format(mention=mention(who.id, who.full_name)))
        return
    await cx.reply(await card_text(cx.services, cx.chat.id, who.id, who.full_name, acc))


async def _move(cx: CommandContext, deposit: bool) -> None:
    acc = await _need_account(cx)
    if acc is None:
        return
    svc = cx.services
    have = await cash(svc, cx.chat.id, cx.user.id) if deposit else acc["balance"]
    amount = _amount(cx.raw_args, have, MAX_MOVE)
    if amount is None:
        await cx.reply(T.BANK_MOVE_BAD.format(cmd="ايداع" if deposit else "سحب"))
        return
    if amount > have:
        await cx.reply((T.BANK_NO_CASH if deposit else T.BANK_NO_BANK).format(have=_num(have)))
        return
    async with svc.db.transaction() as conn:
        if deposit:
            await svc.economy.change_in(conn, cx.chat.id, cx.user.id, -amount, "deposit")
            await conn.execute("UPDATE bank_accounts SET balance = balance + ? WHERE chat_id = ? AND user_id = ?",
                               (amount, cx.chat.id, cx.user.id))
        else:
            cur = await conn.execute("UPDATE bank_accounts SET balance = balance - ? WHERE chat_id = ? AND user_id = ? "
                                     "AND balance >= ?", (amount, cx.chat.id, cx.user.id, amount))
            if cur.rowcount != 1:
                raise InsufficientFunds(acc["balance"])
            await svc.economy.change_in(conn, cx.chat.id, cx.user.id, amount, "withdraw")
    acc = await account(svc, cx.chat.id, cx.user.id)
    w = await cash(svc, cx.chat.id, cx.user.id)
    await cx.reply((T.BANK_DEPOSITED if deposit else T.BANK_WITHDRAWN).format(
        amount=_num(amount), bank=_num(acc["balance"]), cash=_num(w)))


async def _deposit(cx): await _move(cx, True)      # noqa: E704
async def _withdraw(cx): await _move(cx, False)    # noqa: E704


registry.command("bank_deposit", ("ايداع", "إيداع", "اودع"), section=S, args="text", usage="المبلغ أو الكل",
                 description="تحط فلوسك بالبنك حتى تكون بأمان من الزرف 🔐", order=34)(_deposit)
registry.command("bank_withdraw", ("سحب", "اسحب"), section=S, args="text", usage="المبلغ أو الكل",
                 description="تسحب من البنك للمحفظة", order=35)(_withdraw)


@registry.command("bank_interest", ("الفائدة", "الفائده", "فائدة", "فائده", "الارباح"), section=S,
                  description=f"فائدة يومية {INTEREST_PCT}% على فلوس البنك 📈", order=36)
async def cmd_interest(cx: CommandContext) -> None:
    acc = await _need_account(cx)
    if acc is None or await _cooldown(cx, "interest"):
        return
    if acc["balance"] < INTEREST_MIN_BALANCE:
        await cx.reply(T.BANK_INTEREST_LOW.format(n=_num(INTEREST_MIN_BALANCE)))
        return
    gain = min(INTEREST_MAX, max(1, acc["balance"] * INTEREST_PCT // 100))
    await cx.services.economy.change(cx.chat.id, cx.user.id, gain, "interest")
    await set_wait(cx.services, cx.chat.id, cx.user.id, "interest", COOLDOWN["interest"])
    await cx.reply(T.BANK_INTEREST.format(amount=_num(gain), pct=INTEREST_PCT, bank=_num(acc["balance"])))


# ── الكسب المجاني ───────────────────────────────────
async def _free(cx: CommandContext, key: str, amount: int, text: str) -> None:
    balance = await cx.services.economy.change(cx.chat.id, cx.user.id, amount, key)
    await set_wait(cx.services, cx.chat.id, cx.user.id, key, COOLDOWN[key])
    await cx.reply(text.format(mention=mention(cx.user.id, cx.user.full_name), amount=_num(amount), cash=_num(balance)))


@registry.command("bank_tip", ("بخشيش", "بقشيش"), section=S, description="بخشيش صغير كل 10 دقايق 💵", order=37)
async def cmd_tip(cx: CommandContext) -> None:
    if await _need_account(cx) is not None and not await _cooldown(cx, "tip"):
        await _free(cx, "tip", random.randint(10, 60), random.choice(T.BANK_TIP))


@registry.command("bank_treasure", ("كنز", "الكنز"), section=S, description="تدور على كنز كل 3 ساعات 💰", order=38)
async def cmd_treasure(cx: CommandContext) -> None:
    if await _need_account(cx) is None or await _cooldown(cx, "treasure"):
        return
    roll = random.random()
    if roll < 0.05:
        await _free(cx, "treasure", random.randint(1500, 3000), T.BANK_TREASURE_GOLD)
    elif roll < 0.30:
        await _free(cx, "treasure", random.randint(300, 700), T.BANK_TREASURE_BIG)
    else:
        await _free(cx, "treasure", random.randint(80, 250), T.BANK_TREASURE)


@registry.command("bank_wheel", ("عجلة الحظ", "عجله الحظ", "العجلة", "العجله", "دولاب الحظ"), section=S,
                  description="لفّة مجانية كل يوم 🎡", order=39)
async def cmd_wheel(cx: CommandContext) -> None:
    if await _need_account(cx) is None or await _cooldown(cx, "wheel"):
        return
    label, amount, _ = random.choices(WHEEL, weights=[w for *_, w in WHEEL])[0]
    svc = cx.services
    strip = " ".join(random.sample([x if x != "shield" else "🛡" for x, *_ in WHEEL], len(WHEEL)))
    await set_wait(svc, cx.chat.id, cx.user.id, "wheel", COOLDOWN["wheel"])
    if label == "shield":
        await set_wait(svc, cx.chat.id, cx.user.id, "shield", SHIELD_SECS)
        prize = T.BANK_WHEEL_SHIELD.format(hours=SHIELD_SECS // 3600)
    else:
        await svc.economy.change(cx.chat.id, cx.user.id, amount, "wheel")
        prize = T.BANK_WHEEL_MONEY.format(amount=label)
    await cx.reply(T.BANK_WHEEL.format(mention=mention(cx.user.id, cx.user.full_name), strip=strip, prize=prize))


# ── المخاطرة ────────────────────────────────────────
async def _bet(cx: CommandContext, key: str) -> tuple[int, int] | None:
    """يتحقق من الحساب والانتظار والمبلغ. يرجع (المبلغ، الكاش) أو None."""
    if await _need_account(cx) is None or await _cooldown(cx, key):
        return None
    have = await cash(cx.services, cx.chat.id, cx.user.id)
    amount = _amount(cx.raw_args, have, MAX_BET)
    if amount is None or not MIN_BET <= amount <= MAX_BET:
        await cx.reply(T.BANK_BET_BAD.format(cmd=T.BANK_CMD[key], lo=_num(MIN_BET), hi=_num(MAX_BET)))
        return None
    if amount > have:
        await cx.reply(T.BANK_NO_CASH.format(have=_num(have)))
        return None
    return amount, have


async def _settle(cx: CommandContext, key: str, delta: int) -> int:
    balance = await cx.services.economy.change(cx.chat.id, cx.user.id, delta, key)
    await set_wait(cx.services, cx.chat.id, cx.user.id, key, COOLDOWN[key])
    return balance


@registry.command("bank_luck", ("حظ", "رهان"), section=S, args="text", usage="المبلغ أو الكل",
                  description="يا تضاعف فلوسك يا تخسرها 🎲 (50%)", order=40)
async def cmd_luck(cx: CommandContext) -> None:
    bet = await _bet(cx, "luck")
    if bet is None:
        return
    amount, _ = bet
    win = random.random() < 0.5
    balance = await _settle(cx, "luck", amount if win else -amount)
    await cx.reply((T.BANK_LUCK_WIN if win else T.BANK_LUCK_LOSE).format(
        mention=mention(cx.user.id, cx.user.full_name), amount=_num(amount), cash=_num(balance)))


@registry.command("bank_invest", ("استثمار", "استثمر"), section=S, args="text", usage="المبلغ أو الكل",
                  description="استثمار آمن: ربح غالباً وخسارة قليلة 📊 (كل 10 دقايق)", order=41)
async def cmd_invest(cx: CommandContext) -> None:
    bet = await _bet(cx, "invest")
    if bet is None:
        return
    amount, _ = bet
    if random.random() < 0.75:
        pct = random.randint(5, 20)
        change = max(1, amount * pct // 100)
        balance = await _settle(cx, "invest", change)
        text = T.BANK_INVEST_WIN
    else:
        pct = random.randint(5, 15)
        change = max(1, amount * pct // 100)
        balance = await _settle(cx, "invest", -change)
        text = T.BANK_INVEST_LOSE
    await cx.reply(text.format(mention=mention(cx.user.id, cx.user.full_name), amount=_num(amount), pct=pct,
                               change=_num(change), cash=_num(balance)))


@registry.command("bank_speculate", ("مضاربة", "مضاربه", "ضارب"), section=S, args="text", usage="المبلغ أو الكل",
                  description="مخاطرة عالية: ربح كبير أو خسارة كبيرة 📉📈 (كل 5 دقايق)", order=42)
async def cmd_speculate(cx: CommandContext) -> None:
    bet = await _bet(cx, "speculate")
    if bet is None:
        return
    amount, _ = bet
    pct = random.randint(30, 90)
    change = max(1, amount * pct // 100)
    win = random.random() < 0.5
    balance = await _settle(cx, "speculate", change if win else -change)
    await cx.reply((T.BANK_SPEC_WIN if win else T.BANK_SPEC_LOSE).format(
        mention=mention(cx.user.id, cx.user.full_name), amount=_num(amount), pct=pct, change=_num(change),
        cash=_num(balance)))


# ── الزرف والحماية ──────────────────────────────────
@registry.command("bank_rob", ("زرف", "ازرف", "اسرق", "سرقة"), section=S, args="target", usage="بالرد",
                  description="تحاول تزرف من كاش عضو 🥷 (كل 30 دقيقة)", order=43)
async def cmd_rob(cx: CommandContext) -> None:
    if await _need_account(cx) is None:
        return
    reply = cx.message.reply_to_message
    if reply is None or reply.from_user is None or reply.sender_chat is not None:
        await cx.reply(T.BANK_NEED_REPLY.format(cmd="زرف"))
        return
    victim = reply.from_user
    if victim.id == cx.user.id:
        await cx.reply(T.BANK_ROB_SELF)
        return
    if victim.is_bot:
        await cx.reply(T.BANK_ROB_BOT)
        return
    if await _cooldown(cx, "rob"):
        return
    svc, chat_id, uid = cx.services, cx.chat.id, cx.user.id
    vm = mention(victim.id, victim.full_name)
    if await wait_left(svc, chat_id, victim.id, "shield"):
        await cx.reply(T.BANK_ROB_SHIELD.format(victim=vm))
        return
    if await wait_left(svc, chat_id, victim.id, "robbed"):
        await cx.reply(T.BANK_ROB_RECENT.format(victim=vm))
        return
    v_cash, my_cash = await cash(svc, chat_id, victim.id), await cash(svc, chat_id, uid)
    if v_cash < ROB_MIN_CASH:
        await cx.reply(T.BANK_ROB_POOR.format(victim=vm))
        return
    if my_cash < ROB_MIN_CASH:
        await cx.reply(T.BANK_ROB_NEED_CASH.format(n=_num(ROB_MIN_CASH)))
        return
    await set_wait(svc, chat_id, uid, "rob", COOLDOWN["rob"])
    me = mention(uid, cx.user.full_name)
    success = random.random() < ROB_CHANCE
    if success:
        amount = min(ROB_MAX, max(1, v_cash * random.randint(10, 30) // 100))
        src, dst, text = victim.id, uid, T.BANK_ROB_WIN
        await set_wait(svc, chat_id, victim.id, "robbed", ROBBED_SAFE)
    else:
        amount = min(my_cash, max(50, my_cash // 10))
        src, dst, text = uid, victim.id, T.BANK_ROB_FAIL
    try:
        async with svc.db.transaction() as conn:
            await svc.economy.change_in(conn, chat_id, src, -amount, "rob_out" if success else "rob_fine", str(dst))
            await svc.economy.change_in(conn, chat_id, dst, amount, "rob_in" if success else "rob_comp", str(src))
    except InsufficientFunds:
        await cx.reply(T.BANK_ROB_POOR.format(victim=vm))
        return
    await svc.users.upsert(victim.id, victim.first_name, victim.last_name, victim.username, False)
    await svc.audit.log("bank_rob", chat_id=chat_id, actor_id=uid, target_id=victim.id,
                        details={"ok": success, "amount": amount})
    await cx.reply(text.format(robber=me, victim=vm, amount=_num(amount)))


@registry.command("bank_shield", ("حماية", "حمايه", "شراء حماية", "شراء حمايه", "درع"), section=S,
                  description=f"تحمي كاشك من الزرف 6 ساعات ({SHIELD_PRICE:,} 🌸)", order=44)
async def cmd_shield(cx: CommandContext) -> None:
    if await _need_account(cx) is None:
        return
    svc = cx.services
    left = await wait_left(svc, cx.chat.id, cx.user.id, "shield")
    if left:
        await cx.reply(T.BANK_SHIELD_HAVE.format(left=duration(left)))
        return
    try:
        balance = await svc.economy.change(cx.chat.id, cx.user.id, -SHIELD_PRICE, "shield")
    except InsufficientFunds as e:
        await cx.reply(T.NO_FUNDS_TEXT.format(price=SHIELD_PRICE, balance=e.args[0]))
        return
    await set_wait(svc, cx.chat.id, cx.user.id, "shield", SHIELD_SECS)
    await cx.reply(T.BANK_SHIELD_BOUGHT.format(hours=SHIELD_SECS // 3600, price=_num(SHIELD_PRICE),
                                               cash=_num(balance)))


@registry.command("bank_thieves", ("توب الحرامية", "توب الحراميه", "الحرامية", "الحراميه", "توب الزرف"),
                  section=S, description="أكثر 10 زرفوا 🥷", order=45)
async def cmd_thieves(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    rows = await cx.services.db.fetchall(
        "SELECT t.user_id, SUM(t.amount) AS value, u.first_name, u.last_name FROM transactions t "
        "LEFT JOIN users u ON u.user_id = t.user_id WHERE t.chat_id = ? AND t.kind = 'rob_in' "
        "GROUP BY t.user_id ORDER BY value DESC LIMIT 10", (cx.chat.id,))
    header = f"{T.BANK_THIEVES_HEADER}\n{T.LINE}"
    if not rows:
        await cx.reply(f"{header}\n{T.LEADERBOARD_EMPTY}")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {mention(r['user_id'], ' '.join(p for p in (r['first_name'], r['last_name']) if p))}"
             f" ⋅ <b>{r['value']:,}</b> {T.COIN}" for i, r in enumerate(rows)]
    await cx.reply(f"{header}\n" + "\n".join(lines))


@registry.command("bank_menu", ("البنك", "بنك", "بنك زهو", "اوامر البنك", "أوامر البنك"), section=S,
                  description="كل أوامر بنك زهو بشكل مرتب 🏦", order=29)
async def cmd_menu(cx: CommandContext) -> None:
    if await _guard(cx):
        await cx.reply(T.BANK_MENU)

