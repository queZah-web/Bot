"""الاقتصاد الافتراضي: زهرات 🌸 (نقاط افتراضية للمتعة، ما تنسحب ولا تمثل فلوس حقيقية).

الكسب: مكافأة يومية بسلسلة أيام، مهام يومية، الفوز بالألعاب، الترقية بالمستوى.
الصرف: متجر ألقاب وإطارات شكلية، لقب مخصص، تحويل بين الأعضاء (بحدود وضريبة 5%).
الحماية: كل حركة ذرية ومسجلة، الرصيد ما ينزل تحت الصفر، وحدود ضد الحسابات الوهمية.
"""
from __future__ import annotations

import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, User
from telegram.error import BadRequest

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import duration, esc, mention
from zhoo.core.ranks import Rank
from zhoo.core.swear import detector
from zhoo.core.targets import TargetError, resolve_target
from zhoo.data.shop import ITEM_MAP, ITEMS, SLOT
from zhoo.repositories.economy import InsufficientFunds
from zhoo.repositories.levels import day_ago, today
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "economy"

DAILY_COOLDOWN = 20 * 3600
STREAK_WINDOW = 48 * 3600
DAILY_BASE, DAILY_STEP, DAILY_MAX_STEPS = 50, 10, 7
TRANSFER_MIN, TRANSFER_MAX, TRANSFER_DAILY = 10, 5000, 5000
TRANSFER_FEE_PCT = 5
TRANSFER_MIN_MESSAGES = 50
ADMIN_RANK = Rank.OWNER
TOGGLE_RANK = Rank.MANAGER
LEVELUP_PER_LEVEL = 10

MISSIONS: dict[str, tuple[int, int]] = {  # المفتاح ← (الهدف، المكافأة)
    "messages": (15, 40),
    "win": (1, 50),
    "thank": (1, 20),
}

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


async def enabled(svc: Services, chat_id: int) -> bool:
    return (await svc.group_settings.get(chat_id, "economy_on")) == "1"


def _amount(cx: CommandContext, lo: int, hi: int) -> int | None:
    raw = (cx.args[0] if cx.args else "").translate(_DIGITS).replace(",", "")
    if not raw.isdigit() or not lo <= int(raw) <= hi:
        return None
    return int(raw)


# ── الكسب (يُستدعى من الأنظمة الثانية) ───────────────
async def earn(svc: Services, chat_id: int, user_id: int, amount: int, kind: str, ref: str | None = None) -> int | None:
    if amount <= 0 or not await enabled(svc, chat_id):
        return None
    return await svc.economy.change(chat_id, user_id, amount, kind, ref)


async def mission(context, svc: Services, chat, user: User, key: str, step: int = 1) -> None:
    if not await enabled(svc, chat.id):
        return
    target, reward = MISSIONS[key]
    if await svc.economy.mission_progress(chat.id, user.id, today(), key, step, target):
        await svc.economy.change(chat.id, user.id, reward, "mission", key)
        from zhoo.systems.protect import send_notice
        await send_notice(context, chat.id, T.MISSION_DONE.format(
            mention=mention(user.id, user.full_name), name=T.MISSION_NAMES[key], reward=reward), ttl=30)


async def on_levelup(svc: Services, chat_id: int, user_id: int, level: int) -> None:
    await earn(svc, chat_id, user_id, level * LEVELUP_PER_LEVEL, "levelup", str(level))


async def prune(svc: Services) -> None:
    await svc.economy.prune_missions(day_ago(3))


# ── العرض ───────────────────────────────────────────
def title_text(wallet) -> str | None:
    item = wallet["title_item"]
    if not item:
        return None
    if item == "custom":
        return wallet["custom_title"]
    return ITEM_MAP[item].name if item in ITEM_MAP else None


def framed(wallet, name_html: str) -> str:
    item = ITEM_MAP.get(wallet["frame_item"] or "")
    return f"{item.left}{name_html}{item.right}" if item else name_html


async def _guard(cx: CommandContext) -> bool:
    if not await enabled(cx.services, cx.chat.id):
        await cx.reply(T.ECONOMY_OFF)
        return False
    return True


async def _wallet(cx: CommandContext, user_id: int, name: str) -> None:
    svc = cx.services
    w = await svc.economy.wallet(cx.chat.id, user_id)
    pos = 1 + await svc.db.fetchval("SELECT COUNT(*) FROM wallets WHERE chat_id = ? AND balance > ?",
                                    (cx.chat.id, w["balance"]), default=0)
    await cx.reply(T.WALLET.format(name=framed(w, mention(user_id, name)), balance=f"{w['balance']:,}",
                                   earned=f"{w['total_earned']:,}", streak=w["streak"], pos=pos))


@registry.command("wallet", ("محفظتي", "رصيدي", "فلوسي", "زهراتي"), section=S,
                  description="رصيدك من الزهرات 🌸", order=1)
async def cmd_wallet(cx: CommandContext) -> None:
    if await _guard(cx):
        await _wallet(cx, cx.user.id, cx.user.full_name)


@registry.command("their_wallet", ("رصيده", "محفظته", "رصيدها"), section=S, args="target", usage="بالرد/اليوزر",
                  description="رصيد عضو ثاني", order=2)
async def cmd_their_wallet(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "رصيده @username")
        return
    await _wallet(cx, target.user_id, target.name)


# ── المكافأة اليومية ────────────────────────────────
@registry.command("daily", ("المكافأة اليومية", "المكافاه اليوميه", "راتب", "يومي", "هديتي"), section=S,
                  description="مكافأة كل يوم، وتكبر إذا ما فوّت ولا يوم 🔥", order=3)
async def cmd_daily(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    svc = cx.services
    w = await svc.economy.wallet(cx.chat.id, cx.user.id)
    now = int(time.time())
    last = w["last_daily"]
    if last and now - last < DAILY_COOLDOWN:
        await cx.reply(T.DAILY_WAIT.format(left=duration(DAILY_COOLDOWN - (now - last))))
        return
    streak = w["streak"] + 1 if last and now - last <= STREAK_WINDOW else 1
    bonus = DAILY_STEP * min(streak - 1, DAILY_MAX_STEPS)
    balance = await svc.economy.change(cx.chat.id, cx.user.id, DAILY_BASE + bonus, "daily", str(streak))
    await svc.economy.set_daily(cx.chat.id, cx.user.id, streak, now)
    await cx.reply(T.DAILY_DONE.format(amount=DAILY_BASE + bonus, streak=streak, balance=f"{balance:,}",
                                       bonus=T.DAILY_BONUS.format(n=bonus) if bonus else ""))


# ── المهام ──────────────────────────────────────────
@registry.command("missions", ("مهامي", "المهام", "مهام اليوم"), section=S,
                  description="مهام اليوم ومكافآتها 🎯", order=4)
async def cmd_missions(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    state = await cx.services.economy.missions_of(cx.chat.id, cx.user.id, today())
    lines = []
    for key, (target, reward) in MISSIONS.items():
        progress, done = state.get(key, (0, False))
        lines.append(T.MISSION_LINE.format(mark="✅" if done else "▫️", name=T.MISSION_NAMES[key],
                                           progress=min(progress, target), target=target, reward=reward))
    await cx.reply(f"{T.MISSIONS_HEADER}\n" + "\n".join(lines) + "\n" + T.MISSIONS_FOOTER)


# ── المتجر والممتلكات ───────────────────────────────
def shop_keyboard(uid: int, owned: set[str]) -> InlineKeyboardMarkup:
    buttons = []
    for item in ITEMS:
        if item.kind == "custom":
            label = T.SHOP_ITEM_BTN.format(name=item.name, price=item.price, coin=T.COIN)
            buttons.append(InlineKeyboardButton(label, callback_data=f"sh:{uid}:c:{item.key}"))
        elif item.key in owned:
            buttons.append(InlineKeyboardButton(T.SHOP_OWNED_BTN.format(name=item.name),
                                                callback_data=f"sh:{uid}:e:{item.key}"))
        else:
            buttons.append(InlineKeyboardButton(T.SHOP_ITEM_BTN.format(name=item.name, price=item.price, coin=T.COIN),
                                                callback_data=f"sh:{uid}:b:{item.key}"))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(T.BTN_CLOSE, callback_data=f"sh:{uid}:x:-")])
    return InlineKeyboardMarkup(rows)


def inventory_keyboard(uid: int, owned: set[str], wallet) -> InlineKeyboardMarkup | None:
    buttons = []
    for item in ITEMS:
        if item.key not in owned:
            continue
        name = wallet["custom_title"] if item.kind == "custom" and wallet["custom_title"] else item.name
        slot_value = wallet["title_item"] if item.kind in ("title", "custom") else wallet["frame_item"]
        mark = "✅ " if slot_value == item.key else ""
        buttons.append(InlineKeyboardButton(f"{mark}{name}", callback_data=f"sh:{uid}:e:{item.key}"))
    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


@registry.command("shop", ("المتجر", "متجر"), section=S, description="متجر الألقاب والإطارات 🛍", order=5)
async def cmd_shop(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    svc = cx.services
    w = await svc.economy.wallet(cx.chat.id, cx.user.id)
    owned = await svc.economy.owned(cx.chat.id, cx.user.id)
    await cx.reply(T.SHOP.format(balance=f"{w['balance']:,}"), reply_markup=shop_keyboard(cx.user.id, owned))


def _inventory_text(w) -> str:
    frame = ITEM_MAP.get(w["frame_item"] or "")
    return T.INVENTORY.format(title=esc(title_text(w) or T.NOTHING), frame=frame.name if frame else T.NOTHING)


@registry.command("inventory", ("ممتلكاتي", "اغراضي"), section=S, description="ألقابك وإطاراتك، تلبسها وتنزعها",
                  order=6)
async def cmd_inventory(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    svc = cx.services
    owned = await svc.economy.owned(cx.chat.id, cx.user.id)
    w = await svc.economy.wallet(cx.chat.id, cx.user.id)
    kb = inventory_keyboard(cx.user.id, owned, w)
    if kb is None:
        await cx.reply(T.INVENTORY_EMPTY)
        return
    await cx.reply(_inventory_text(w), reply_markup=kb)


@registry.command("custom_title", ("لقب مخصص",), section=S, args="text", usage="النص",
                  description="تكتب لقبك الخاص بنفسك (1000 🌸)", order=7)
async def cmd_custom_title(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    text = " ".join(cx.raw_args.split())
    if not 2 <= len(text) <= 20:
        await cx.reply(T.CUSTOM_TITLE_BAD)
        return
    if detector.find(text):
        await cx.reply(T.CUSTOM_TITLE_SWEAR)
        return
    item = ITEM_MAP["custom"]
    try:
        await cx.services.economy.buy(cx.chat.id, cx.user.id, item.key, item.price, SLOT["custom"], custom_text=text)
    except InsufficientFunds as e:
        await cx.reply(T.NO_FUNDS_TEXT.format(price=item.price, balance=e.args[0]))
        return
    await cx.reply(T.CUSTOM_TITLE_DONE.format(title=esc(text), price=item.price))


async def on_shop_button(q, msg: Message, svc: Services, uid_raw: str, action: str, key: str) -> None:
    if not uid_raw.isdigit() or int(uid_raw) != q.from_user.id:
        await q.answer(T.NOT_YOUR_SHOP, show_alert=True)
        return
    chat_id, uid = msg.chat.id, q.from_user.id
    if action == "x":
        try:
            await msg.delete()
        except BadRequest:
            pass
        return
    if action == "c":
        await q.answer(T.CUSTOM_TITLE_BAD.replace(f"{T.BULLET} ", "").replace("<code>", "").replace("</code>", ""),
                       show_alert=True)
        return
    item = ITEM_MAP.get(key)
    if item is None or item.kind == "custom" and action == "b":
        await q.answer()
        return
    owned = await svc.economy.owned(chat_id, uid)
    in_shop = T.SHOP_MARK in (msg.text or "")
    if action == "b" and key not in owned:
        try:
            await svc.economy.buy(chat_id, uid, key, item.price, SLOT[item.kind])
        except InsufficientFunds as e:
            await q.answer(T.NO_FUNDS.format(price=item.price, balance=e.args[0], coin=T.COIN), show_alert=True)
            return
        await q.answer(T.BOUGHT.format(name=item.name))
    elif action in ("e", "b") and key in owned:
        w = await svc.economy.wallet(chat_id, uid)
        slot = "frame_item" if item.kind == "frame" else "title_item"
        if w[slot] == key:
            await svc.economy.equip(chat_id, uid, slot, None)
            await q.answer(T.UNEQUIPPED.format(name=item.name))
        else:
            await svc.economy.equip(chat_id, uid, slot, key)
            await q.answer(T.EQUIPPED.format(name=item.name))
    else:
        await q.answer()
        return
    w = await svc.economy.wallet(chat_id, uid)
    owned = await svc.economy.owned(chat_id, uid)
    try:
        if in_shop:
            await msg.edit_text(T.SHOP.format(balance=f"{w['balance']:,}"), reply_markup=shop_keyboard(uid, owned))
        else:
            await msg.edit_text(_inventory_text(w), reply_markup=inventory_keyboard(uid, owned, w))
    except BadRequest:
        pass


# ── التحويل ─────────────────────────────────────────
@registry.command("transfer", ("تحويل", "حول"), section=S, args="text", usage="بالرد + المبلغ",
                  description="تحوّل زهرات لعضو (ضريبة 5%)", order=8)
async def cmd_transfer(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    reply = cx.message.reply_to_message
    amount = _amount(cx, TRANSFER_MIN, TRANSFER_MAX)
    if reply is None or reply.from_user is None or reply.sender_chat is not None or amount is None:
        await cx.reply(T.TRANSFER_BAD)
        return
    to = reply.from_user
    if to.id == cx.user.id:
        await cx.reply(T.TRANSFER_SELF)
        return
    if to.is_bot:
        await cx.reply(T.TRANSFER_BOT)
        return
    svc = cx.services
    messages = await svc.members.message_count(cx.chat.id, cx.user.id) + svc.tracker.pending_count(cx.chat.id, cx.user.id)
    if messages < TRANSFER_MIN_MESSAGES:
        await cx.reply(T.TRANSFER_NEW.format(n=TRANSFER_MIN_MESSAGES))
        return
    if await svc.economy.sent_since(cx.chat.id, cx.user.id, 86400) + amount > TRANSFER_DAILY:
        await cx.reply(T.TRANSFER_LIMIT.format(n=TRANSFER_DAILY))
        return
    fee = max(1, amount * TRANSFER_FEE_PCT // 100)
    try:
        await svc.economy.transfer(cx.chat.id, cx.user.id, to.id, amount, fee)
    except InsufficientFunds as e:
        await cx.reply(T.NO_FUNDS_TEXT.format(price=amount + fee, balance=e.args[0]))
        return
    await svc.users.upsert(to.id, to.first_name, to.last_name, to.username, False)
    await svc.audit.log("transfer", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=to.id,
                        details={"amount": amount, "fee": fee})
    await cx.reply(T.TRANSFER_DONE.format(from_=mention(cx.user.id, cx.user.full_name),
                                          to=mention(to.id, to.full_name), amount=amount, fee=fee))


# ── السجل والترتيب ──────────────────────────────────
@registry.command("tx_history", ("سجل محفظتي", "حركاتي"), section=S, description="آخر 10 حركات بمحفظتك", order=9)
async def cmd_history(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    rows = await cx.services.economy.history(cx.chat.id, cx.user.id)
    if not rows:
        await cx.reply(f"{T.HISTORY_HEADER}\n{T.HISTORY_EMPTY}")
        return
    lines = [f"{'🟢' if r['amount'] > 0 else '🔴'} <b>{r['amount']:+,}</b> {T.COIN} ⋅ "
             f"{T.TX_KINDS.get(r['kind'], r['kind'])} ⋅ <code>{time.strftime('%m-%d', time.gmtime(r['created_at']))}</code>"
             for r in rows]
    await cx.reply(f"{T.HISTORY_HEADER}\n" + "\n".join(lines))


@registry.command("richest", ("الاغنى", "الأغنى", "توب الفلوس", "توب الزهرات"), section=S,
                  description="أغنى 10 أعضاء", order=10)
async def cmd_richest(cx: CommandContext) -> None:
    if not await _guard(cx):
        return
    rows = await cx.services.economy.richest(cx.chat.id)
    header = T.RICH_HEADER + f"\n{T.LINE}"
    if not rows:
        await cx.reply(f"{header}\n{T.LEADERBOARD_EMPTY}")
        return
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [f"{medals[i]} {mention(r['user_id'], ' '.join(p for p in (r['first_name'], r['last_name']) if p))}"
             f" ⋅ <b>{r['value']:,}</b> {T.COIN}" for i, r in enumerate(rows)]
    await cx.reply(f"{header}\n" + "\n".join(lines))


# ── إدارة الاقتصاد ──────────────────────────────────
async def _admin_change(cx: CommandContext, give: bool) -> None:
    if not await _guard(cx):
        return
    amount = _amount(cx, 1, 100_000)
    reply = cx.message.reply_to_message
    if reply is None or reply.from_user is None or reply.from_user.is_bot or amount is None:
        await cx.reply(T.ADMIN_AMOUNT_BAD)
        return
    to = reply.from_user
    svc = cx.services
    if not give:
        amount = min(amount, (await svc.economy.wallet(cx.chat.id, to.id))["balance"])
    balance = await svc.economy.change(cx.chat.id, to.id, amount if give else -amount,
                                       "admin_give" if give else "admin_take", str(cx.user.id))
    await svc.audit.log("economy_admin", chat_id=cx.chat.id, actor_id=cx.user.id, target_id=to.id,
                        details={"amount": amount if give else -amount})
    template = T.ADMIN_GIVE if give else T.ADMIN_TAKE
    await cx.reply(template.format(amount=amount, mention=mention(to.id, to.full_name), balance=f"{balance:,}"))


async def _give(cx): await _admin_change(cx, True)    # noqa: E704
async def _take(cx): await _admin_change(cx, False)   # noqa: E704


registry.command("eco_give", ("اضافة زهرات", "إضافة زهرات"), section=S, min_rank=ADMIN_RANK, args="text",
                 usage="بالرد + المبلغ", description="يضيف زهرات لعضو", order=20)(_give)
registry.command("eco_take", ("خصم زهرات",), section=S, min_rank=ADMIN_RANK, args="text",
                 usage="بالرد + المبلغ", description="يخصم زهرات من عضو", order=21)(_take)


def _toggle(on: bool):
    async def handler(cx: CommandContext) -> None:
        await cx.services.group_settings.set(cx.chat.id, "economy_on", "1" if on else "0", cx.user.id)
        await cx.reply((T.TOGGLE_ON if on else T.TOGGLE_OFF).format(what="الاقتصاد"))
    return handler


registry.command("economy_on", ("تفعيل الاقتصاد",), section=S, min_rank=TOGGLE_RANK,
                 description="يشغّل الاقتصاد", order=22)(_toggle(True))
registry.command("economy_off", ("تعطيل الاقتصاد",), section=S, min_rank=TOGGLE_RANK,
                 description="يوقف الاقتصاد", order=23)(_toggle(False))
