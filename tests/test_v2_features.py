"""اختبارات: الأقفال v2 (الأوضاع والأقفال الجديدة والثغرات)، الميزات، والأوامر الإضافية."""
import asyncio
from types import SimpleNamespace

import pytest
from telegram import Chat, Message, MessageEntity, PhotoSize, Update, User

from zhoo.core import guards
from zhoo.core.commands import registry
from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.systems import extras, features, locks, protect
from tests.test_flow import ALI, CREATOR, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)
    await say(env, ALI, "هلا")


async def _send(env, user_id, **kw):
    svc, bot, ctx = env
    msg = Message(next(_mid), None, CHAT, from_user=User(user_id, f"U{user_id}", False), **kw)
    msg.set_bot(bot)
    bot.calls.clear()
    bot.sent.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return bot.calls


async def _edit(env, user_id, **kw):
    svc, bot, ctx = env
    msg = Message(next(_mid), None, CHAT, from_user=User(user_id, f"U{user_id}", False), **kw)
    msg.set_bot(bot)
    bot.calls.clear()
    await locks.on_edited(Update(next(_mid), edited_message=msg), ctx)
    return bot.calls


# ── المحلل والكاشفات ──
def test_parse_lock():
    assert locks.parse_lock("الصور")[0].key == "photos" and locks.parse_lock("الصور")[1] is None
    assert locks.parse_lock("الصور بالتقييد")[1] == "restrict"
    assert locks.parse_lock("الإيرانية بالطرد") == (locks.LOCK_MAP["persian"], "kick")
    assert locks.parse_lock("تعديل الميديا")[0].key == "edit_media"
    assert locks.parse_lock("الباب") is None
    assert registry.parse("قفل الباب وراك") is None  # جملة عادية ما تنحسب أمر


def test_detectors():
    assert guards.is_persian("سلام خوبی؟ این خیلی خوبه")
    assert not guards.is_persian("شلونك گاع، چا شنو صار؟")
    assert not guards.is_persian("سڵاو چۆنی")  # كردي
    assert guards.is_userbot_command(".ايدي") and not guards.is_userbot_command("...هههه")
    assert guards.is_long("ا" * 900) and not guards.is_long("هلا")
    porn = Message(1, None, CHAT, text="شوف https://xvideos.com/x",
                   entities=[MessageEntity(MessageEntity.URL, 4, 21)])
    assert guards.has_porn(porn) and not guards.has_porn(Message(1, None, CHAT, text="صباح الخير"))


# ── الأوضاع ──
async def test_lock_restrict_mode(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "قفل الصور بالتقييد")
    assert "تقييد" in out
    calls = await _send(env, ALI, photo=[PhotoSize("f", "u", 1, 1)])
    assert calls[0][0] == "delete" and any(c[0] == "restrict" for c in calls)
    assert await svc.punishments.is_active(GROUP, ALI, "restrict")
    assert "فك التقييد" in str(bot.last_kw.get("reply_markup"))


async def test_lock_warn_and_kick_modes(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل الملصقات بالتحذير")
    from telegram import Sticker
    await _send(env, ALI, sticker=Sticker("s", "u", 1, 1, False, False, "regular"))
    assert await svc.punishments.warning_count(GROUP, ALI) == 1
    await say(env, CREATOR, "قفل الصور بالطرد")
    calls = await _send(env, ALI, photo=[PhotoSize("f", "u", 1, 1)])
    assert [c[0] for c in calls[:3]] == ["delete", "ban", "unban"]


async def test_mode_not_allowed(env):
    await _setup(env)
    assert "ما يقبل" in await say(env, CREATOR, "قفل الدخول بالتحذير")


async def test_new_content_locks(env):
    svc, bot, _ = env
    await _setup(env)
    for cmd in ("قفل الإيرانية", "قفل جمثون", "قفل المعرفات", "قفل الكلايش", "قفل الإباحي"):
        await say(env, CREATOR, cmd)
        svc.command_limiter._hits.clear()
    for text, ents in (("سلام خوبی؟ این خیلی خوبه", []), (".ايدي", []), ("كلم @someone", None),
                       ("ا" * 900, []), ("فلم سكس", [])):
        if ents is None:
            ents = [MessageEntity(MessageEntity.MENTION, 4, 8)]
        svc.strikes.reset((GROUP, ALI))
        calls = await _send(env, ALI, text=text, entities=ents)
        assert calls and calls[0][0] == "delete", text


async def test_text_lock_and_vip_exempt(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل الكتابة")
    assert (await _send(env, ALI, text="مرحبا"))[0][0] == "delete"
    await svc.members.set_rank(GROUP, SARA, Rank.VIP, CREATOR)
    assert await _send(env, SARA, text="مرحبا") == []


# ── ثغرة التعديل ──
async def test_edit_bypass_is_closed(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل الروابط")
    calls = await _edit(env, ALI, text="عدلتها t.me/spam")
    assert calls and calls[0][0] == "delete"


async def test_edit_and_edit_media_locks(env):
    await _setup(env)
    assert await _edit(env, ALI, text="تعديل عادي") == []
    await say(env, CREATOR, "قفل تعديل الميديا")
    assert (await _edit(env, ALI, photo=[PhotoSize("f", "u", 1, 1)]))[0][0] == "delete"
    assert await _edit(env, ALI, text="نص معدل") == []
    await say(env, CREATOR, "قفل التعديل")
    assert (await _edit(env, ALI, text="نص معدل"))[0][0] == "delete"


# ── الدخول والبوتات ──
async def test_join_lock_kicks_newcomers(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, CREATOR, "قفل الدخول")
    newbie = User(5550111, "New", False)
    msg = Message(next(_mid), None, CHAT, from_user=newbie, new_chat_members=[newbie])
    msg.set_bot(bot)
    bot.calls.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert [c[0] for c in bot.calls[:2]] == ["ban", "unban"]


async def test_bots_lock_kicks_adder(env):
    svc, bot, ctx = env
    await _setup(env)
    await say(env, CREATOR, "قفل البوتات بالطرد")
    intruder = User(6660111, "SpamBot", True)
    msg = Message(next(_mid), None, CHAT, from_user=User(ALI, "A", False), new_chat_members=[intruder])
    msg.set_bot(bot)
    bot.calls.clear()
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    kicked = [c[1] for c in bot.calls if c[0] == "ban"]
    assert intruder.id in kicked and ALI in kicked


# ── لوحة الأقفال ──
async def test_lock_panel_pages_and_cycle(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "الأقفال")
    assert "الوسائط" in out
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append((text, reply_markup))

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text, reply_markup=None)
    q = SimpleNamespace(from_user=SimpleNamespace(id=CREATOR), answer=answer)
    await locks.on_panel_button(q, msg, svc, bot, str(CREATOR), "p", "content")
    assert "المحتوى" in edits[-1][0]
    for expected in ("delete", "warn", "mute", "restrict", "kick", None):
        await locks.on_panel_button(q, msg, svc, bot, str(CREATOR), "t", "persian")
        assert await locks.get_mode(svc, GROUP, "persian") == expected


# ── الميزات ──
async def test_feature_commands_exist():
    import zhoo.app  # noqa: F401
    for key in features.COMMAND_FEATURE:
        assert registry.get(key) is not None, key


async def test_feature_toggle_blocks_members_not_owner(env):
    await _setup(env)
    assert "تعطيل" in await say(env, CREATOR, "تعطيل الايدي")
    assert "معطّل" in await say(env, ALI, "ايدي")
    assert str(CREATOR) in await say(env, CREATOR, "ايدي")  # المالك يتجاوز
    assert "تفعيل" in await say(env, CREATOR, "تفعيل الايدي")
    assert str(ALI) in await say(env, ALI, "ايدي")
    assert "من قبل" in await say(env, CREATOR, "تفعيل الايدي")


async def test_feature_panel_and_aliases(env):
    svc = env[0]
    await _setup(env)
    assert "الـمِـيـزَات" in await say(env, CREATOR, "الميزات")
    await say(env, CREATOR, "تفعيل التحقق")
    assert (await protect.guards_state(svc, GROUP))["captcha"] is True
    await say(env, CREATOR, "تعطيل الانذار")
    assert not await features.enabled(svc, GROUP, "warn")


async def test_protection_toggle(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "تعطيل الحماية")
    for i in range(protect.FLOOD_LIMIT + 1):
        await say(env, ALI, f"رسالة {i}")
    assert not await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_quote_mode(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "تعطيل الاقتباس")
    await say(env, ALI, "رتبتي")
    assert bot.last_kw.get("reply_parameters") is None


# ── الأوامر الإضافية ──
async def test_whoadded(env):
    svc, bot, ctx = env
    await _setup(env)
    newbie = User(5550222, "New", False)
    msg = Message(next(_mid), None, CHAT, from_user=User(SARA, "S", False), new_chat_members=[newbie])
    msg.set_bot(bot)
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)
    assert "ضافه" in await say(env, 5550222, "ضافني")
    assert "ما أعرف" in await say(env, ALI, "ضافني")


async def test_kickme(env):
    svc, bot, _ = env
    await _setup(env)
    assert "متأكد" in await say(env, ALI, "اطردني")
    assert "من الإدارة" in await say(env, CREATOR, "اطردني")
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append(text)

    async def edit_text(text, reply_markup=None):
        edits.append(text)

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text)
    await extras.on_kickme_button(SimpleNamespace(from_user=SimpleNamespace(id=SARA, full_name="S"), answer=answer),
                                  msg, svc, bot, str(ALI), "y")
    assert "لصاحب الطلب" in answers[-1]
    bot.calls.clear()
    await extras.on_kickme_button(SimpleNamespace(from_user=SimpleNamespace(id=ALI, full_name="A"), answer=answer),
                                  msg, svc, bot, str(ALI), "y")
    assert [c[0] for c in bot.calls[:2]] == ["ban", "unban"] and "طلّعت" in edits[-1]


async def test_mention_all(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, SARA, "هلا")
    extras.MENTION_DELAY = 0
    await say(env, CREATOR, "منشن تعالوا للمسابقة")
    for _ in range(50):
        await asyncio.sleep(0.01)
        if GROUP not in svc.mention_tasks:
            break
    joined = " ".join(bot.sent)
    assert "تعالوا للمسابقة" in joined and str(ALI) in joined and "خلص النداء" in joined


async def test_fun_and_kt(env):
    await _setup(env)
    out1 = await say(env, ALI, "نسبة الحب", reply_to=SARA)
    out2 = await say(env, SARA, "نسبة الحب", reply_to=ALI)
    assert "%" in out1 and out1.split("<b>")[1] == out2.split("<b>")[1]  # نفس النسبة للطرفين
    assert "الذكاء" in await say(env, ALI, "نسبة الذكاء")
    assert "حظ" in await say(env, ALI, "حظي اليوم")
    assert "زهو تختار" in await say(env, ALI, "زهو اختاري شاي او قهوة")
    assert "كَـت" in await say(env, ALI, "كت")


def test_safe_calc():
    assert extras.safe_calc("(5 + 3) × 2") == 16
    assert extras.safe_calc("١٠ ÷ ٤") == 2.5
    assert extras.safe_calc("__import__('os')") is None
    assert extras.safe_calc("9 ** 9999") is None
    assert extras.safe_calc("1/0") is None


async def test_service_commands(env):
    await _setup(env)
    assert "ببغداد" in await say(env, ALI, "الوقت")
    assert "اليوم" in await say(env, ALI, "التاريخ")
    assert "<b>16</b>" in await say(env, ALI, "احسب (5 + 3) × 2")
    await say(env, CREATOR, "تعطيل الخدمية")
    assert "معطّل" in await say(env, ALI, "الوقت")


async def test_source_replies_and_toggle(env):
    await _setup(env)
    assert "وعليكم السلام" in await say(env, ALI, "السلام عليكم")
    assert await say(env, SARA, "السلام عليكم") is None  # مرة بالدقيقة حتى ما يصير سبام
    await say(env, CREATOR, "تعطيل ردود زهو")
    extras._source_limiter._hits.clear()
    assert await say(env, ALI, "صباح الخير") is None


async def test_azkar(env):
    svc, bot, ctx = env
    await _setup(env)
    assert "معطّل" in await say(env, ALI, "ذكر")  # الأذكار معطّلة افتراضياً
    await say(env, CREATOR, "تفعيل الأذكار")
    assert "ذِكْـر" in await say(env, ALI, "ذكر")
    bot.sent.clear()
    await extras.azkar_job(ctx)
    assert bot.sent and "ذِكْـر" in bot.sent[-1]
