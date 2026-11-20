"""ولا كلمة بذيئة تطلع من زهو، قاموس الإهانات (مذكر/مؤنث + بالرد)، والإساءة لزهو، ومراقبة «ش» المخفية."""
import re


import pytest
from telegram import Chat, ChatMemberUpdated, Update, User
from telegram import ChatMemberBanned, ChatMemberMember

from zhoo.core import texts as T
from zhoo.core.ranks import Rank
from zhoo.core.swear import detector
from zhoo.data import swear_bank as bank
from zhoo.handlers import membership
from zhoo.systems import watchdog
from tests.test_flow import ALI, BOT_ID, CREATOR, DEV, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()


def _plain(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def _clean_output(texts) -> list[str]:
    """كل رسالة طلعت من زهو وبيها كلام مسيء (لازم تكون فاضية)."""
    return [t for t in texts if t and detector.scan(_plain(t)) is not None]


# ── ١) ولا كلمة بذيئة من زهو ──
def test_static_texts_have_no_bad_words():
    bad = []
    for name in dir(T):
        value = getattr(T, name)
        items = value if isinstance(value, (tuple, list)) else value.values() if isinstance(value, dict) else [value]
        for v in items:
            if isinstance(v, str) and detector.scan(_plain(re.sub(r"\{[^}]*\}", " ", v))):
                bad.append(name)
    assert bad == []


async def test_bot_never_echoes_bad_words(env):
    svc, bot, _ = env
    await _setup(env)
    out = []

    async def run(user, text, **kw):
        svc.command_limiter._hits.clear()
        bot.sent.clear()
        await say(env, user, text, **kw)
        out.extend(bot.sent)

    await run(CREATOR, "قفل السب بالمسح")
    await run(ALI, "هلا كسمك يا حلو")
    await run(ALI, "انعل ابوك")
    await run(CREATOR, "السب المحذوف")
    await run(CREATOR, "فحص سب ك.س.م.ك")
    await run(CREATOR, "فحص سب")
    await run(CREATOR, "اضافة سب شديد بطيخ عفن")
    await run(CREATOR, "قاموس السب")
    await run(CREATOR, "سماح كلمة يا حمار")
    await run(CREATOR, "منع كلمة قحبه")
    await run(CREATOR, "قائمة المنع")
    assert out and _clean_output(out) == []
    assert any("ك•••" in t for t in out)                     # الكلمة مغطاة
    assert "ك.ل.ب" in T.SWEAR_TEST_NEED and "ك.س" not in T.SWEAR_TEST_NEED


# ── ٢) قاموس الإهانات ──
@pytest.mark.parametrize("text", [
    "يا كلب", "يا كلبه", "انت قذر", "انتي قذره", "يا لعين", "يا لعينه", "يا قندره", "انتي هايشه",
    "ابن القندرة", "ابن القندره", "بنت القندره", "ابن الكلب", "ابن الچبة", "اجب عليك", "يا قذر",
    "يا ابن الكلب", "زهو زباله", "تفو عليج", "يا غبيه", "انت مخبل", "يا ملعون",
])
def test_insults_detected_as_light(text):
    hit = detector.scan(text)
    assert hit is not None and hit.entry.level == bank.LIGHT, text


@pytest.mark.parametrize("text", [
    "الشيطان اللعين", "اشتريت قندره جديدة", "الكلب نايم بالبيت", "حليب البقرة", "السطل مليان",
    "انجبت طفلة حلوة", "جبة صوف", "ثور هائج بالفلم",
])
def test_insult_words_alone_are_fine(text):
    assert detector.find(text) is None


@pytest.mark.parametrize("text,hit", [
    ("قذر", True), ("هايشه", True), ("يا حمار وسخ", True), ("الكلب", True), ("قندره", True),
    ("الكلب نايم", False), ("شكراً", False), ("انت حلو", False),
])
def test_reply_insults(text, hit):
    assert (detector.reply_insult(text) is not None) == hit


async def test_reply_with_bare_insult_is_punished(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, CREATOR, "قفل الاهانات بالمسح")
    bot.calls.clear()
    await say(env, ALI, "قذر", reply_to=SARA)
    assert bot.calls and bot.calls[0][0] == "delete"
    bot.calls.clear()
    await say(env, ALI, "قذر")                                 # بدون رد: كلمة عادية
    assert not [c for c in bot.calls if c[0] == "delete"]


async def test_insulting_zhoo_gets_a_reply(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل الاهانات بالمسح")
    bot.sent.clear()
    await say(env, ALI, "هايشه", reply_to=BOT_ID)
    assert any("احترام" in (t or "") or "الأدب" in (t or "") or "الكلام الحلو" in (t or "") for t in bot.sent)


# ── ٣) مراقبة «ش» ──
async def test_watch_is_hidden_and_toggles(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.OWNER, CREATOR)
    assert await say(env, ALI, "ش", reply_to=SARA) is None        # عضو: ولا رد
    assert await say(env, SARA, "ش", reply_to=ALI) is None        # مالك: ولا رد
    assert "تم التفعيل" in await say(env, CREATOR, "ش", reply_to=SARA)
    assert "تم الإيقاف" in await say(env, CREATOR, "ش", reply_to=SARA)
    assert "تم التفعيل" in await say(env, DEV, "ش", reply_to=SARA)
    assert "ش" not in [c.display_name for c in __import__("zhoo.core.commands", fromlist=["registry"])
                       .registry.by_section("ranks")]


async def test_watch_triggers_after_three_bans(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.OWNER, CREATOR)
    await say(env, CREATOR, "ش", reply_to=SARA)
    for victim in (5001, 5002):
        svc.command_limiter._hits.clear()
        await say(env, SARA, "حظر", reply_to=victim)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.OWNER
    svc.command_limiter._hits.clear()
    bot.sent.clear()
    await say(env, SARA, "طرد", reply_to=5003)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.MEMBER
    alert = next(t for t in bot.sent if "تَـنْـبِـيـه أَمْـنِـي" in (t or ""))
    assert f"tg://user?id={CREATOR}" in alert and "<b>3</b>" in alert
    # بس صاحب المجموعة يرجّعه
    await svc.members.set_rank(GROUP, ALI, Rank.PRIMARY_OWNER, CREATOR)
    svc.command_limiter._hits.clear()
    assert "موقوفة للتحقيق" in await say(env, ALI, "رفع مالك", reply_to=SARA)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.MEMBER
    assert "مالك" in await say(env, CREATOR, "رفع مالك", reply_to=SARA)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.OWNER
    assert not await watchdog.is_locked(svc, GROUP, SARA)


async def test_watch_counts_telegram_native_bans(env):
    svc, bot, ctx = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    await say(env, CREATOR, "ش", reply_to=SARA)
    actor = User(SARA, "S", False)
    for victim in (6001, 6002, 6003):
        u = User(victim, "V", False)
        cmu = ChatMemberUpdated(CHAT, actor, __import__("datetime").datetime.now(),
                                ChatMemberMember(u), ChatMemberBanned(u, __import__("datetime").datetime.now()))
        await membership.on_chat_member(Update(next(_mid), chat_member=cmu), ctx)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.MEMBER
    assert await watchdog.is_locked(svc, GROUP, SARA)


async def test_unwatched_admin_is_not_touched(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.OWNER, CREATOR)
    for victim in (7001, 7002, 7003, 7004):
        svc.command_limiter._hits.clear()
        await say(env, SARA, "حظر", reply_to=victim)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.OWNER


