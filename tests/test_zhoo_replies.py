"""إيقاف/تعطيل زهو حتى للمطور، ردود زهو المضافة، «لا تردي عليه»، ورد وحد كل 10 ثواني."""
import re

import pytest

from zhoo.core import texts as T
from zhoo.core.ranks import Rank
from zhoo.data import extras_bank as bank
from zhoo.systems import zhoo_replies as zr
from tests.test_flow import ALI, CREATOR, DEV, GROUP, SARA, env, say  # noqa: F401


@pytest.fixture(autouse=True)
def _reset(_open_chat_gate):
    zr.gate.max_hits = 1
    zr.gate._hits.clear()
    zr._cache.clear()
    yield
    zr.gate._hits.clear()
    zr._cache.clear()


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()


async def _say(env, user, text, **kw):
    env[0].command_limiter._hits.clear()
    return await say(env, user, text, **kw)


# ── ١) الإيقاف والتعطيل يشملن المطور ──
@pytest.mark.parametrize("who", [DEV, CREATOR])
async def test_disable_silences_everyone(env, who):
    await _setup(env)
    assert "تَـعْـطِـيـل" in await _say(env, who, "تعطيل زهو")
    for text in ("زهو", "بوت", "ايدي", "السلام عليكم", "هلا"):
        zr.gate._hits.clear()
        assert await _say(env, who, text) is None, text
        assert await _say(env, ALI, text) is None, text
    assert "تَـفْـعِـيـل" in await _say(env, who, "تفعيل زهو")
    assert await _say(env, who, "ايدي") is not None


@pytest.mark.parametrize("who", [DEV, CREATOR])
async def test_pause_silences_everyone(env, who):
    await _setup(env)
    assert "إِيـقَـاف" in await _say(env, who, "ايقاف زهو")
    for text in ("ايدي", "السلام عليكم", "هلا"):
        assert await _say(env, who, text) is None, text
    assert await _say(env, who, "زهو") == T.BOT_PAUSED_REPLY      # بس تذكير بأمر التشغيل
    assert "تَـشْـغِـيـل" in await _say(env, who, "فتح زهو")


# ── ٢) ردود زهو المضافة ──
async def _add(env, user, cmd, word, *replies):
    await _say(env, user, cmd)
    await _say(env, user, word)
    for r in replies:
        await _say(env, user, r)
    return await _say(env, user, "تم")


async def test_global_reply_dev_only_and_everywhere(env):
    svc, bot, _ = env
    await _setup(env)
    assert await _say(env, CREATOR, "اضف رد زهو") is None              # مخفي عن غير المطور
    out = await _add(env, DEV, "اضف رد زهو", "زهو تحبين الورد", "أحب الجوري 🌹", "الورد كله حلو يا {الاسم}")
    assert "تَـمَّ حِـفْـظ" in out and "<b>2</b>" in out
    got = await _say(env, ALI, "زهو تحبين الورد؟")
    assert got in ("أحب الجوري 🌹", "الورد كله حلو يا U3000003")
    assert await svc.db.fetchval("SELECT COUNT(*) FROM zhoo_replies WHERE scope = 0") == 2   # لكل المجموعات
    assert "انمسحت" in await _say(env, DEV, "مسح رد زهو زهو تحبين الورد")
    zr.gate._hits.clear()
    assert await _say(env, ALI, "زهو تحبين الورد") is None


async def test_group_reply_owner_and_beats_builtin(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    assert "رتبة" in await _say(env, SARA, "اضف رد زهو مجموعة")
    await _add(env, CREATOR, "اضف رد زهو مجموعة", "صباح الخير", "صباح الخير من زهو المجموعة ☀️")
    assert await _say(env, ALI, "صباح الخير") == "صباح الخير من زهو المجموعة ☀️"
    assert "صباح الخير" in await _say(env, CREATOR, "ردود زهو المضافة")
    assert "انمسحت" in await _say(env, CREATOR, "مسح رد زهو مجموعة صباح الخير")
    zr.gate._hits.clear()
    __import__("zhoo.systems.extras", fromlist=["x"])._chat_source_limiter._hits.clear()
    assert await _say(env, ALI, "صباح الخير") in [r.replace("{name}", "U3000003")
                                                  for r in bank.REPLY_GROUPS["morning"][1]]


async def test_reply_rejects_commands_and_bad_words(env):
    await _setup(env)
    await _say(env, DEV, "اضف رد زهو")
    assert "أمر من أوامري" in await _say(env, DEV, "حظر")
    assert "ما تليق" in await _say(env, DEV, "كسمك")
    await _say(env, DEV, "زهو شتسوين")
    assert "ما تليق" in await _say(env, DEV, "يا كلب")
    assert "ولا رد" in await _say(env, DEV, "تم")


# ── ٣) رد وحد كل 10 ثواني ──
async def test_one_chat_reply_per_10_seconds(env):
    await _setup(env)
    assert await _say(env, ALI, "السلام عليكم") is not None
    assert await _say(env, ALI, "هلا") is None
    assert await _say(env, ALI, "زهو") is None                        # حتى النداء
    assert await _say(env, SARA, "هلا") is not None                  # شخص ثاني عادي
    assert "معلومات" in await _say(env, ALI, "ايدي")                   # الأوامر ما تتأثر
    zr.gate._hits.clear()
    assert await _say(env, ALI, "هلا") is not None


# ── ٤) لا تردي عليه ──
async def test_noreply_self_and_others(env):
    svc, bot, _ = env
    await _setup(env)
    assert "بعد ما أرد" in await _say(env, ALI, "لا تردي علي")
    for t in ("السلام عليكم", "زهو"):
        zr.gate._hits.clear()
        assert await _say(env, ALI, t) is None
    assert "معلومات" in await _say(env, ALI, "ايدي")                   # الأوامر تبقى
    assert "على نفسك بس" in await _say(env, ALI, "لا تردي عليه", reply_to=SARA)
    assert "رجعت أرد" in await _say(env, ALI, "ردي علي")
    zr.gate._hits.clear()
    assert await _say(env, ALI, "هلا") is not None
    assert "بعد ما أرد" in await _say(env, CREATOR, "لاتردي عليه", reply_to=SARA)
    zr.gate._hits.clear()
    assert await _say(env, SARA, "هلا") is None
    assert "رجعت أرد" in await _say(env, CREATOR, "ردي عليه", reply_to=SARA)


def test_replies_are_polite():
    banned = ("عيني", "عيوني", "گلبي", "قلبي", "حبيبي", "حبيبتي", "عمري", "روحي", "الغالي", "اشتاق")
    texts = [r for _, rs in bank.REPLY_GROUPS.values() for r in rs] + list(T.ZHOO_REPLIES) + list(T.ZHOO_INSULTED)
    bad = [t for t in texts for b in banned if b in t and "عيني على المجموعة" not in t]
    assert bad == []
