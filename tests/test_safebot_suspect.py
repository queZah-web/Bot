"""فلتر الرسائل الطالعة، العقوبة الفورية، المميز المشكوك فيه، وقاموس المطور العام."""
import asyncio

from telegram import Chat, Message, PhotoSize, Sticker, Update, User

from zhoo.core import safebot
from zhoo.core.ranks import Rank
from zhoo.core.swear import detector
from zhoo.handlers import router
from zhoo.systems import suspect, swear
from tests.test_flow import ALI, CREATOR, DEV, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()


# ── ١) ولا سب يطلع من زهو (حتى لو جا من نص عضو) ──
class _Base:
    def __init__(self):
        self.out = []

    async def send_message(self, chat_id, text, **kw):
        self.out.append(text)

    async def edit_message_text(self, text, **kw):
        self.out.append(text)

    async def answer_callback_query(self, qid, text=None, **kw):
        self.out.append(text)

    async def send_photo(self, chat_id, photo, caption=None, **kw):
        self.out.append(caption)

    async def edit_message_caption(self, chat_id=None, message_id=None, inline_message_id=None, caption=None, **kw):
        self.out.append(caption)


class _Safe(safebot.SafeOutputMixin, _Base):
    pass


async def test_safe_output_masks_everything():
    b = _Safe()
    await b.send_message(1, '<b>ترحيب</b> <a href="tg://user?id=5">كسمك</a> يا حلو')
    await b.send_message(1, text="هلا انعل ابوك")
    await b.edit_message_text("ابن الكلب هنا", chat_id=1, message_id=2)
    await b.answer_callback_query("q", "يا حمار")
    await b.send_photo(1, "f", caption="kosomak")
    await b.edit_message_caption(chat_id=1, message_id=2, caption="شرموطه")
    assert all(detector.scan(t.replace("<b>", " ").replace("</b>", " ")) is None for t in b.out), b.out
    assert '<a href="tg://user?id=5">••••</a>' in b.out[0] and "<b>ترحيب</b>" in b.out[0]
    assert "يا حلو" in b.out[0]


async def test_safe_bot_is_used_by_app():
    from zhoo.app import build_application
    from zhoo.config import Settings
    app = build_application(Settings(token="123456:" + "A" * 35, owner_id=1, db_path=":memory:", log_dir=None))
    assert isinstance(app.bot, safebot.SafeBot)


# ── ٢) المسح والكتم بنفس اللحظة ──
async def test_delete_and_mute_run_together(env):
    svc, bot, _ = env
    await _setup(env)
    order = []
    real_delete, real_restrict = bot.delete_message, bot.restrict_chat_member

    async def slow_delete(*a, **k):
        order.append("delete-start")
        await asyncio.sleep(0.05)
        order.append("delete-end")
        return await real_delete(*a, **k)

    async def restrict(*a, **k):
        order.append("mute")
        return await real_restrict(*a, **k)
    bot.delete_message, bot.restrict_chat_member = slow_delete, restrict
    await say(env, CREATOR, "قفل السب بالكتم")
    await say(env, ALI, "كسمك")
    assert order.index("mute") < order.index("delete-end")      # الكتم ما ينتظر المسح
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


# ── ٣) المميز المشكوك فيه ──
async def _send(env, user_id, **kw):
    svc, bot, ctx = env
    msg = Message(next(_mid), None, CHAT, from_user=User(user_id, f"U{user_id}", False), **kw)
    msg.set_bot(bot)
    bot.calls.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return msg.message_id


async def test_suspect_vip_media_deleted_after_delay(env, monkeypatch):
    svc, bot, _ = env
    await _setup(env)
    monkeypatch.setattr(suspect, "DELAY", 0.05)
    out = await say(env, CREATOR, "رفع مميز م", reply_to=SARA)
    assert "تم رفع" in out and "مميز م" in out and "مشكوك" not in out and len(bot.sent) == 1
    assert await svc.members.get_rank(GROUP, SARA) == Rank.VIP and await suspect.is_suspect(svc, GROUP, SARA)
    await say(env, CREATOR, "قفل الصور")
    mid = await _send(env, SARA, photo=[PhotoSize("f", "u", 1, 1)])
    assert ("delete", mid) not in bot.calls                           # مميز: ما تنمسح فوراً
    await asyncio.sleep(0.1)
    assert ("delete", mid) in bot.calls                               # تنمسح بعد المهلة
    mid = await _send(env, SARA, sticker=Sticker("s", "u", 1, 1, False, False, "regular"))
    await asyncio.sleep(0.1)
    assert ("delete", mid) in bot.calls
    mid = await _send(env, SARA, text="كلام عادي")
    await asyncio.sleep(0.1)
    assert ("delete", mid) not in bot.calls                           # الكتابة تبقى
    assert "U4000004" in await say(env, CREATOR, "المشكوك فيهم")
    svc.command_limiter._hits.clear()
    assert "انشال الشك" in await say(env, CREATOR, "تنزيل مشكوك", reply_to=SARA)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.VIP
    await say(env, CREATOR, "رفع مميز م", reply_to=SARA)
    await say(env, CREATOR, "تنزيل", reply_to=SARA)                  # التنزيل الكامل يشيل الشك
    assert not await suspect.is_suspect(svc, GROUP, SARA)
    assert "يحتاج رتبة" in await say(env, ALI, "رفع مميز م", reply_to=SARA)


# ── ٤) قاموس المطور العام ──
async def test_developer_global_words(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    assert await say(env, CREATOR, "اضف كلمة سب جديدة بطيخ عفن") is None          # غير المطور: مخفي
    out = await say(env, DEV, "اضف كلمة سب جديدة بطيخ عفن")
    assert "تَـمَّـت الإِضَـافَـة" in out and "بطيخ" not in out
    bot.calls.clear()
    await say(env, ALI, "انت بطيخ عفن")
    assert bot.calls and bot.calls[0][0] == "delete"
    assert "انشالت" in await say(env, DEV, "ازل كلمة سب قديمة بطيخ عفن")
    # إيقاف كلمة من القاموس الأساسي (بكل المجموعات)
    assert "توقفت" in await say(env, DEV, "ازل كلمة سب قديمة يا حمار")
    bot.calls.clear()
    await say(env, ALI, "يا حمار")
    assert not [c for c in bot.calls if c[0] == "delete"]
    assert "رجعت" in await say(env, DEV, "اضف كلمة سب جديدة يا حمار")
    bot.calls.clear()
    await say(env, ALI, "يا حمار")
    assert bot.calls and bot.calls[0][0] == "delete"
    assert "سليم" in await say(env, DEV, "اضف كلمة سب جديدة قواد")


async def test_developer_words_from_private_chat(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, DEV, "اضف كلمة سب جديدة شديد طماطة خايسة", chat_type=Chat.PRIVATE)
    assert "تَـمَّـت الإِضَـافَـة" in out
    assert (await swear.scan(svc, GROUP, "هاي طماطة خايسة")) is not None
    assert await say(env, ALI, "اضف كلمة سب جديدة شي", chat_type=Chat.PRIVATE) is None   # مخفي عن غيره
