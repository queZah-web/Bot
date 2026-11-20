"""اختبارات: التقييد الجديد، قفل الرياكت، اختصارات الأوامر، الردود والردود المميزة."""
from types import SimpleNamespace

from telegram import (Chat, Message, MessageReactionUpdated, ReactionTypeEmoji, Sticker, Update, User)

from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.systems import locks
from tests.test_flow import ALI, CREATOR, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    await env[0].groups.upsert(GROUP, "g", None)


# ── التقييد والكتم ──
async def test_restrict_is_view_only_and_mute_allows_reactions(env):
    bot = env[1]
    await say(env, CREATOR, "تقييد", reply_to=ALI)
    restrict = [c for c in bot.calls if c[0] == "restrict"][-1]
    assert restrict[2] is False
    from zhoo.core import moderation as mod
    assert mod._restrict_permissions().can_react_to_messages is False
    assert mod._restrict_permissions().can_invite_users is False
    assert mod._mute_permissions().can_react_to_messages is True
    assert mod._mute_permissions().can_send_messages is False


async def test_unlock_aliases(env):
    await say(env, CREATOR, "تقييد", reply_to=ALI)
    assert "فَـكُّ الـتَّـقْـيِـيـد" in await say(env, CREATOR, "فتح التقييد", reply_to=ALI)
    await say(env, CREATOR, "كتم", reply_to=ALI)
    assert "فَـكُّ الـكَـتْـم" in await say(env, CREATOR, "فتح الكتم", reply_to=ALI)


# ── قفل الرياكت ──
def _reaction(user_id):
    return Update(next(_mid), message_reaction=MessageReactionUpdated(
        CHAT, 55, None, (), (ReactionTypeEmoji("❤"),), user=User(user_id, "U", False)))


async def test_reaction_lock(env):
    svc, bot, ctx = env
    await _setup(env)
    assert "تَـمَّ الـقَـفْـل" in await say(env, CREATOR, "قفل الرياكت")
    bot.calls.clear()
    await locks.on_reaction(_reaction(ALI), ctx)
    assert ("unreact", 55, ALI) in bot.calls
    await svc.members.set_rank(GROUP, SARA, Rank.VIP, CREATOR)
    bot.calls.clear()
    await locks.on_reaction(_reaction(SARA), ctx)
    assert bot.calls == []
    await say(env, CREATOR, "فتح الرياكت")
    await locks.on_reaction(_reaction(ALI), ctx)
    assert bot.calls == []


# ── اختصارات الأوامر ──
async def test_alias_flow_and_usage(env):
    svc = env[0]
    await _setup(env)
    assert "الأمر القديم" in await say(env, CREATOR, "اضف امر")
    assert "مو أمر" in await say(env, CREATOR, "شي غريب")
    assert "الأمر الجديد" in await say(env, CREATOR, "تقييد")
    assert "أمر من أوامري" in await say(env, CREATOR, "كتم")  # يتعارض مع أمر موجود
    assert "تـق" in (await say(env, CREATOR, "تق")).replace("<code>تق</code>", "تـق")
    # الاختصار يشتغل ويحترم الرتبة
    out = await say(env, CREATOR, "تق", reply_to=ALI)
    assert "تَـمَّ الـتَّـقْـيِـيـد" in out
    assert "يحتاج رتبة" in await say(env, SARA, "تق", reply_to=ALI)
    assert "تق" in await say(env, CREATOR, "الاوامر المضافة")
    assert "انحذف" in await say(env, CREATOR, "حذف امر تق")
    assert await say(env, CREATOR, "تق", reply_to=ALI) is None


async def test_alias_cancel(env):
    await _setup(env)
    await say(env, CREATOR, "اضف امر")
    assert "الإلغاء" in await say(env, CREATOR, "الغاء")
    assert env[0].conversations.get(GROUP, CREATOR) is None


async def test_alias_needs_manager(env):
    assert "يحتاج رتبة" in await say(env, ALI, "اضف امر")


# ── الردود ──
async def test_normal_reply_multi_items(env):
    svc, bot, ctx = env
    await _setup(env)
    assert "ارسل الكلمة" in await say(env, CREATOR, "اضف رد")
    assert "ارسل الرد" in await say(env, CREATOR, "صباح الخير")
    assert "باقي <b>9</b>" in await say(env, CREATOR, "صباح النور {الاسم} 🌸")
    # ملصق كرد ثاني
    sticker = Sticker("STK1", "u", 10, 10, False, False, "regular")
    msg = Message(next(_mid), None, CHAT, from_user=User(CREATOR, "C", False), sticker=sticker)
    msg.set_bot(bot)
    bot.sent.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    assert "باقي <b>8</b>" in bot.sent[-1]
    out = await say(env, CREATOR, "تم")
    assert "تَـمَّ حِـفْـظ الـرَّد" in out and "<b>2</b>" in out
    # التشغيل: الرسالة كلها هي الكلمة
    for _ in range(4):
        out = await say(env, ALI, "صباح الخير")
        assert "صباح النور" in out or "[sticker:STK1]" in out
    # الرد العادي ما ينرسل إذا الكلمة بنص جملة
    assert await say(env, SARA, "قلت صباح الخير للكل") is None
    assert "صباح الخير" in await say(env, CREATOR, "الردود")


async def test_special_reply_inside_long_text(env):
    await _setup(env)
    await say(env, CREATOR, "اضف رد مميز")
    await say(env, CREATOR, "زهراء")
    await say(env, CREATOR, "عيونها 🤍")
    assert "رد مميز" in await say(env, CREATOR, "تم")
    out = await say(env, ALI, "اليوم شفت صديقتي زهراء بالسوق وسلمت عليها")
    assert "عيونها" in out
    assert "زهراء" in await say(env, CREATOR, "الردود المميزة")


async def test_discard_and_delete(env):
    svc = env[0]
    await _setup(env)
    await say(env, CREATOR, "اضف رد")
    await say(env, CREATOR, "هلو")
    await say(env, CREATOR, "هلا بيك")
    assert "ما انحفظ" in await say(env, CREATOR, "حذف")
    assert await say(env, ALI, "هلو") is None

    await say(env, CREATOR, "اضف رد")
    await say(env, CREATOR, "هلو")
    await say(env, CREATOR, "هلا بيك")
    await say(env, CREATOR, "تم")
    assert "اختار الرد" in await say(env, CREATOR, "حذف رد")
    assert "انحذف" in await say(env, CREATOR, "هلو")
    assert await say(env, ALI, "هلو") is None


async def test_reply_word_cannot_be_command(env):
    await _setup(env)
    await say(env, CREATOR, "اضف رد")
    assert "أمر من أوامري" in await say(env, CREATOR, "ايدي")


async def test_only_starter_answers_conversation(env):
    await _setup(env)
    await say(env, CREATOR, "اضف رد")
    await say(env, ALI, "كلام ثاني")  # رسالة شخص ثاني ما تأثر
    assert "ارسل الرد" in await say(env, CREATOR, "مرحبا")


async def test_ten_items_autosave(env):
    await _setup(env)
    await say(env, CREATOR, "اضف رد")
    await say(env, CREATOR, "عشرة")
    out = None
    for i in range(10):
        out = await say(env, CREATOR, f"رد رقم {i}")
    assert "تَـمَّ حِـفْـظ الـرَّد" in out and "<b>10</b>" in out
