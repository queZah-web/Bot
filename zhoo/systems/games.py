"""الألعاب: أسرع جواب صح يفوز بنقاط خبرة.

- لعبة وحدة بكل مجموعة بنفس الوقت، ولكل لعبة وقت محدد وبعده ينكشف الجواب.
- الأجوبة تنكتب عادي بالمجموعة، والتحقق يتحمل اختلاف الكتابة (ال، ة/ه، أ/ا، الأرقام الهندية).
- «أسرع كتابة» فيها حروف مخفية بين الحروف، فالنسخ واللصق ما ينحسب.
"""
from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, User

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext, Services
from zhoo.core.fmt import esc, mention
from zhoo.core.normalize import normalize
from zhoo.core.ranks import Rank
from zhoo.core.targets import TargetError, resolve_target
from zhoo.data import game_bank as bank
from zhoo.systems.general import reply_target_error

log = logging.getLogger(__name__)
S = "games"

STOP_RANK = Rank.ADMIN
TOGGLE_RANK = Rank.MANAGER
COOLDOWN = 3
ZWNJ = "‌"
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_PUNCT = re.compile(r"[^\w\s]")

QUIZ_XP = {"easy": 15, "medium": 25, "hard": 40}
QUIZ_SECS = {"easy": 30, "medium": 40, "hard": 50}
MATH_XP = {"easy": 15, "medium": 25, "hard": 35}


@dataclass
class Game:
    kind: str
    keys: set[str]
    display: str
    xp: int
    secs: int
    started_by: int
    token: int = field(default_factory=lambda: random.getrandbits(31))
    started_at: float = field(default_factory=time.monotonic)
    players: frozenset[int] | None = None
    anti_copy: bool = False

    @property
    def expired(self) -> bool:
        return time.monotonic() - self.started_at > self.secs


# ── مطابقة الأجوبة ──────────────────────────────────
def _norm(text: str) -> str:
    text = normalize((text or "").translate(_DIGITS).replace("چ", "ج").replace(ZWNJ, ""))
    return " ".join(_PUNCT.sub("", text).split())


def answer_keys(text: str) -> set[str]:
    """صيغ الجواب: كما هو، وبدون «ال» التعريف، وبدون مسافات."""
    base = _norm(text)
    if not base:
        return set()
    no_al = " ".join(w[2:] if w.startswith("ال") and len(w) > 3 else w for w in base.split())
    return {base, no_al, base.replace(" ", ""), no_al.replace(" ", "")}


def make_keys(answers: list[str]) -> set[str]:
    keys: set[str] = set()
    for a in answers:
        keys |= answer_keys(a)
    return keys


# ── بناء الألعاب ────────────────────────────────────
def _scramble(word: str) -> str:
    letters = list(word)
    for _ in range(20):
        random.shuffle(letters)
        if "".join(letters) != word:
            break
    return " ".join(letters)


def _math(level: str) -> tuple[str, int]:
    if level == "easy":
        a, b = random.randint(10, 60), random.randint(1, 40)
        return (f"{a} + {b}", a + b) if random.random() < 0.5 else (f"{max(a, b)} - {min(a, b)}", abs(a - b))
    if level == "medium":
        a, b = random.randint(3, 15), random.randint(3, 12)
        return f"{a} × {b}", a * b
    a, b, c = random.randint(6, 20), random.randint(4, 12), random.randint(5, 60)
    return f"{a} × {b} + {c}", a * b + c


def daily_riddle(day: date | None = None) -> tuple[str, list[str]]:
    day = day or date.today()
    return bank.RIDDLES[day.toordinal() % len(bank.RIDDLES)]


def build(kind: str, level: str | None, starter: int) -> tuple[Game, str]:
    """يرجع (اللعبة، نص السؤال المنسق)."""
    if kind == "quiz":
        level = level or random.choice(list(bank.QUIZ))
        q, answers = random.choice(bank.QUIZ[level])
        game = Game(kind, make_keys(answers), answers[0], QUIZ_XP[level], QUIZ_SECS[level], starter)
        prompt = T.GAME_PROMPTS["quiz"].format(question=esc(q))
        head = T.GAME_HEADER["quiz"][0].format(level=T.QUIZ_LEVELS[level])
    elif kind == "scramble":
        word = random.choice(bank.WORDS)
        game = Game(kind, make_keys([word]), word, 20, 40, starter)
        prompt = T.GAME_PROMPTS["scramble"].format(question=esc(_scramble(word)))
        head = T.GAME_HEADER["scramble"][0]
    elif kind == "typing":
        phrase = random.choice(bank.PHRASES)
        game = Game(kind, {_norm(phrase)}, phrase, 15, 30, starter, anti_copy=True)
        prompt = T.GAME_PROMPTS["typing"].format(question=esc(ZWNJ.join(phrase)))
        head = T.GAME_HEADER["typing"][0]
    elif kind in ("math", "duel"):
        level = level or ("medium" if kind == "duel" else random.choice(["easy", "medium", "hard"]))
        expr, result = _math(level)
        game = Game(kind, {str(result)}, str(result), 25 if kind == "duel" else MATH_XP[level],
                    30 if kind == "duel" else 35, starter)
        prompt = expr if kind == "duel" else T.GAME_PROMPTS["math"].format(question=expr)
        head = T.GAME_HEADER[kind][0]
    elif kind == "riddle":
        q, answers = random.choice(bank.RIDDLES)
        game = Game(kind, make_keys(answers), answers[0], 30, 60, starter)
        prompt = T.GAME_PROMPTS["riddle"].format(question=esc(q))
        head = T.GAME_HEADER["riddle"][0]
    elif kind == "daily":
        q, answers = daily_riddle()
        game = Game(kind, make_keys(answers), answers[0], 50, 90, starter)
        prompt = T.GAME_PROMPTS["daily"].format(question=esc(q))
        head = T.GAME_HEADER["daily"][0]
    else:
        raise ValueError(kind)
    emoji = T.GAME_HEADER[kind][1]
    return game, f"{T.title(head, emoji)}\n{T.LINE}\n{prompt}"


# ── التشغيل ─────────────────────────────────────────
async def _send(context, svc: Services, chat_id: int, text: str, **kw) -> Message | None:
    from zhoo.systems.protect import send_notice
    return await send_notice(context, chat_id, text, ttl=0, **kw)


async def start(context, svc: Services, chat_id: int, starter: User, kind: str, level: str | None = None,
                players: frozenset[int] | None = None, prompt_override: str | None = None) -> str | None:
    """يبدي لعبة. يرجع نص خطأ إذا ما گدر، أو None إذا بدت."""
    if (await svc.group_settings.get(chat_id, "games_on")) != "1":
        return T.GAMES_OFF
    current = svc.games.get(chat_id)
    if current is not None and not current.expired:
        return T.GAME_RUNNING
    if current is not None:
        await _finish_timeout(context, svc, chat_id, current)
    if time.monotonic() - svc.games.get(("cd", chat_id), 0) < COOLDOWN:
        return T.GAME_COOLDOWN
    if kind == "daily":
        solved = await svc.group_settings.get(chat_id, "daily_riddle")
        if solved.startswith(date.today().isoformat() + ":"):
            uid = int(solved.split(":")[1])
            u = await svc.users.get(uid)
            return T.DAILY_SOLVED.format(mention=mention(uid, u.full_name if u else str(uid)))

    game, text = build(kind, level, starter.id)
    game.players = players
    if prompt_override:
        text = prompt_override.replace("{question}", text.split(f"{T.LINE}\n", 1)[1])
    text += T.GAME_BODY.format(xp=game.xp, secs=game.secs)
    svc.games[chat_id] = game
    if await _send(context, svc, chat_id, text) is None:
        svc.games.pop(chat_id, None)
        return None
    jq = getattr(context, "job_queue", None)
    if jq is not None:
        jq.run_once(_timeout_job, game.secs, data=(chat_id, game.token))
    return None


async def _finish_timeout(context, svc: Services, chat_id: int, game: Game) -> None:
    if svc.games.get(chat_id) is game:
        svc.games.pop(chat_id, None)
        svc.games[("cd", chat_id)] = time.monotonic()
        await _send(context, svc, chat_id, T.GAME_TIMEOUT.format(answer=esc(game.display)))


async def _timeout_job(context) -> None:
    from zhoo.core.context import get_services
    chat_id, token = context.job.data
    svc = get_services(context)
    game = svc.games.get(chat_id)
    if game is not None and game.token == token:
        await _finish_timeout(context, svc, chat_id, game)


async def check_answer(context, svc: Services, msg: Message, chat, user: User) -> bool:
    """يفحص رسالة كجواب للعبة الشغّالة. يرجع True إذا كانت الجواب الصح."""
    game = svc.games.get(chat.id)
    if game is None or not msg.text:
        return False
    if game.expired:
        await _finish_timeout(context, svc, chat.id, game)
        return False
    if game.players is not None and user.id not in game.players:
        return False
    if game.anti_copy and any(ch in msg.text for ch in (ZWNJ, "​", "‍")):
        if svc.notice_limiter.hit(("copy", chat.id, user.id)):
            await msg.reply_text(T.TYPING_COPY)
        return False
    if not answer_keys(msg.text) & game.keys:
        return False

    svc.games.pop(chat.id, None)
    svc.games[("cd", chat.id)] = time.monotonic()
    secs = time.monotonic() - game.started_at
    from zhoo.systems import levels
    if await levels.enabled(svc, chat.id):
        await levels.give_xp(context, svc, chat, user, game.xp)
    else:
        await svc.levels.add_xp(chat.id, user.id, 0)  # نضمن وجود العضو حتى ينحسب الفوز
    await svc.levels.add_win(chat.id, user.id)
    if game.kind == "daily":
        await svc.group_settings.set(chat.id, "daily_riddle", f"{date.today().isoformat()}:{user.id}", user.id)
    await msg.reply_text(T.GAME_WIN.format(mention=mention(user.id, user.full_name),
                                           answer=esc(game.display), secs=f"{secs:.1f}", xp=game.xp))
    return True


# ── الأوامر ─────────────────────────────────────────
async def _cmd_start(cx: CommandContext, kind: str, level: str | None = None) -> None:
    error = await start(cx.context, cx.services, cx.chat.id, cx.user, kind, level)
    if error:
        await cx.reply(error)


def _game_cmd(kind: str, level: str | None = None):
    async def handler(cx: CommandContext) -> None:
        await _cmd_start(cx, kind, level)
    return handler


registry.command("game_quiz", ("سؤال", "سوال"), section=S, description="سؤال ثقافي بمستوى عشوائي",
                 order=1)(_game_cmd("quiz"))
registry.command("game_quiz_easy", ("سؤال سهل", "سوال سهل"), section=S, description="سؤال سهل 🟢",
                 order=2)(_game_cmd("quiz", "easy"))
registry.command("game_quiz_medium", ("سؤال متوسط", "سوال متوسط"), section=S, description="سؤال متوسط 🟡",
                 order=3)(_game_cmd("quiz", "medium"))
registry.command("game_quiz_hard", ("سؤال صعب", "سوال صعب"), section=S, description="سؤال صعب 🔴",
                 order=4)(_game_cmd("quiz", "hard"))
registry.command("game_scramble", ("رتب", "رتب الحروف"), section=S, description="رتب الحروف وكوّن الكلمة",
                 order=5)(_game_cmd("scramble"))
registry.command("game_typing", ("اسرع", "أسرع", "اسرع كتابه"), section=S,
                 description="أول واحد يكتب العبارة يفوز", order=6)(_game_cmd("typing"))
registry.command("game_math", ("رياضيات", "حساب"), section=S, description="مسألة حساب سريعة",
                 order=7)(_game_cmd("math"))
registry.command("game_riddle", ("لغز",), section=S, description="لغز وأول واحد يحله يفوز",
                 order=8)(_game_cmd("riddle"))
registry.command("game_daily", ("لغز اليوم",), section=S, description="لغز واحد باليوم بمكافأة كبيرة 🌟",
                 order=9)(_game_cmd("daily"))


@registry.command("game_duel", ("تحدي",), section=S, args="target", usage="بالرد/اليوزر",
                  description="تحدي بينك وبين عضو: أول واحد يحل المسألة يفوز", order=10)
async def cmd_duel(cx: CommandContext) -> None:
    try:
        target = await resolve_target(cx)
    except TargetError as e:
        await reply_target_error(cx, e, "تحدي @username")
        return
    if target.user_id == cx.user.id:
        await cx.reply(T.DUEL_SELF)
        return
    if target.is_bot:
        await cx.reply(T.DUEL_BOT)
        return
    a, b = mention(cx.user.id, cx.user.full_name), mention(target.user_id, target.name)
    head = T.title(T.GAME_HEADER["duel"][0], T.GAME_HEADER["duel"][1])
    override = f"{head}\n{T.LINE}\n" + T.GAME_PROMPTS["duel"].format(a=a, b=b, question="{question}")
    error = await start(cx.context, cx.services, cx.chat.id, cx.user, "duel",
                        players=frozenset({cx.user.id, target.user_id}), prompt_override=override)
    if error:
        await cx.reply(error)


@registry.command("game_stop", ("ايقاف اللعبه", "إيقاف اللعبة", "وقف اللعبه"), section=S,
                  description="يوقف اللعبة الشغّالة (اللي بداها أو الأدمن)", order=11)
async def cmd_stop(cx: CommandContext) -> None:
    game = cx.services.games.get(cx.chat.id)
    if game is None:
        await cx.reply(T.GAME_NONE)
        return
    if game.started_by != cx.user.id and cx.rank < STOP_RANK:
        await cx.reply(T.GAME_STOP_DENIED)
        return
    cx.services.games.pop(cx.chat.id, None)
    await cx.reply(T.GAME_STOPPED.format(answer=esc(game.display)))


# ── قائمة الألعاب بالأزرار ──────────────────────────
def menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(label, callback_data=f"gm:{kind}") for kind, label in T.BTN_GAMES.items()]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


@registry.command("games_menu", ("الالعاب", "الألعاب", "العاب"), section=S,
                  description="قائمة الألعاب بالأزرار", order=0)
async def cmd_menu(cx: CommandContext) -> None:
    if (await cx.services.group_settings.get(cx.chat.id, "games_on")) != "1":
        await cx.reply(T.GAMES_OFF)
        return
    await cx.reply(T.GAMES_MENU, reply_markup=menu_keyboard())


async def on_menu_button(q, msg: Message, svc: Services, context, kind: str) -> None:
    if kind not in T.BTN_GAMES:
        await q.answer()
        return
    error = await start(context, svc, msg.chat.id, q.from_user, kind)
    if error:
        await q.answer(re.sub(r"<[^>]+>", "", error).replace(f"{T.BULLET} ", ""), show_alert=True)
    else:
        await q.answer("🎮")


async def _board_wins(cx: CommandContext) -> None:
    from zhoo.systems import levels
    await levels.send_board(cx, "wins")


registry.command("board_wins", ("ترتيب المسابقات", "توب المسابقات"), section=S,
                 description="أكثر 10 فازوا بالألعاب", order=12)(_board_wins)


def _toggle(on: bool):
    async def handler(cx: CommandContext) -> None:
        await cx.services.group_settings.set(cx.chat.id, "games_on", "1" if on else "0", cx.user.id)
        if not on:
            cx.services.games.pop(cx.chat.id, None)
        await cx.reply((T.TOGGLE_ON if on else T.TOGGLE_OFF).format(what="الألعاب"))
    return handler


registry.command("games_on", ("تفعيل الالعاب", "تفعيل الألعاب"), section=S, min_rank=TOGGLE_RANK,
                 description="يشغّل الألعاب", order=20)(_toggle(True))
registry.command("games_off", ("تعطيل الالعاب", "تعطيل الألعاب"), section=S, min_rank=TOGGLE_RANK,
                 description="يوقف الألعاب", order=21)(_toggle(False))
