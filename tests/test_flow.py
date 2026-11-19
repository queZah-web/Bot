"""محاكاة رسائل حقيقية تمر عبر الموجّه الكامل (بدون اتصال بتيليجرام)."""
from types import SimpleNamespace

import pytest
from telegram import Chat, Message, MessageEntity, Update, User
from telegram.constants import ChatMemberStatus

from zhoo.config import Settings
from zhoo.core.context import Services
from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.keyboards.menus import SECTIONS, help_main_keyboard, section_text, start_keyboard
from zhoo.core.commands import registry
import zhoo.app  # noqa: F401  (يسجل كل الأوامر)

DEV, CREATOR, ALI, SARA, BOT_ID = 1000001, 2000002, 3000003, 4000004, 9000009
GROUP = -1001234567890


class FakeBot:
    def __init__(self):
        self.sent: list[str] = []
        self.id = BOT_ID
        self.username = "ZhooTestBot"
        self.defaults = None
        self.admins = {
            CREATOR: SimpleNamespace(user=User(CREATOR, "Creator", False), status=ChatMemberStatus.OWNER,
                                     is_anonymous=False),
            BOT_ID: SimpleNamespace(user=User(BOT_ID, "Zhoo", True), status=ChatMemberStatus.ADMINISTRATOR,
                                    is_anonymous=False),
        }

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(text)
        return SimpleNamespace(message_id=1)

    async def send_photo(self, chat_id, photo, caption=None, **kw):
        self.sent.append(caption)

    async def get_chat_administrators(self, chat_id, **kw):
        return list(self.admins.values())

    async def get_user_profile_photos(self, user_id, **kw):
        return SimpleNamespace(total_count=0, photos=[])

    async def get_chat_member(self, chat_id, user_id, **kw):
        raise __import__("telegram").error.BadRequest("not found")


@pytest.fixture
async def env(db):
    settings = Settings(token="1:x", owner_id=DEV, db_path=":memory:", log_dir=None)
    svc = Services.build(settings, db)
    await svc.bot_settings.load()
    bot = FakeBot()
    ctx = SimpleNamespace(application=SimpleNamespace(bot_data={"services": svc}), bot=bot)
    return svc, bot, ctx


_mid = iter(range(1, 10**6))


def make_update(bot, user_id, text, *, reply_to=None, chat_type=Chat.SUPERGROUP, name=None):
    chat = Chat(GROUP if chat_type != Chat.PRIVATE else user_id, chat_type, title="مجموعة الاختبار")
    user = User(user_id, name or f"U{user_id}", False, username=f"user{user_id}")
    reply = None
    if reply_to is not None:
        reply = Message(next(_mid), None, chat, from_user=User(reply_to, f"U{reply_to}", False), text="hi")
    msg = Message(next(_mid), None, chat, from_user=user, text=text, reply_to_message=reply)
    msg.set_bot(bot)
    if reply:
        reply.set_bot(bot)
    return Update(next(_mid), message=msg)


async def say(env, user_id, text, **kw):
    svc, bot, ctx = env
    bot.sent.clear()
    await router.on_message(make_update(bot, user_id, text, **kw), ctx)
    return bot.sent[-1] if bot.sent else None


async def test_id_command(env):
    out = await say(env, ALI, "ايدي")
    assert str(ALI) in out and "عضو" in out


async def test_member_cannot_promote(env):
    out = await say(env, ALI, "رفع مدير", reply_to=SARA)
    assert "يحتاج رتبة" in out


async def test_creator_promotes_and_hierarchy(env):
    svc = env[0]
    await say(env, SARA, "هلا")  # حتى ينحفظ يوزرها
    out = await say(env, CREATOR, "رفع مالك", reply_to=ALI)
    assert "تَمَّ الرَّفْعُ" in out
    assert await svc.members.get_rank(GROUP, ALI) == Rank.OWNER

    # المالك يرفع مدير باليوزر
    out = await say(env, ALI, f"رفع مدير @user{SARA}")
    assert "تَمَّ الرَّفْعُ" in out
    # المدير ما يكدر ينزل المالك
    out = await say(env, SARA, "تنزيل", reply_to=ALI)
    assert "أعلى منك" in out
    # المدير ما يرفع مدير
    out = await say(env, SARA, "رفع مدير", reply_to=5000005)
    assert "يحتاج رتبة" in out
    # ما أحد يغير رتبة المنشئ
    out = await say(env, ALI, "تنزيل", reply_to=CREATOR)
    assert "أعلى منك" in out or "محمية" in out
    # تنزيل مدير
    out = await say(env, ALI, "تنزيل مدير", reply_to=SARA)
    assert "تَمَّ التَّنْزِيلُ" in out
    assert await svc.members.get_rank(GROUP, SARA) == Rank.MEMBER
    # كل شي انسجل
    assert len(await svc.audit.recent(50)) >= 4


async def test_self_promote_blocked(env):
    out = await say(env, CREATOR, "رفع مميز", reply_to=CREATOR)
    assert "بنفسك" in out


async def test_developer_is_top_everywhere(env):
    out = await say(env, DEV, "رفع مالك", reply_to=ALI)
    assert "تَمَّ الرَّفْعُ" in out


async def test_maintenance_blocks_others(env):
    svc = env[0]
    await svc.bot_settings.set("maintenance", "1")
    assert "الصيانة" in (await say(env, ALI, "ايدي"))
    assert str(DEV) in (await say(env, DEV, "ايدي"))


async def test_dev_commands_hidden(env):
    assert await say(env, ALI, "سجل العمليات") is None


async def test_sentence_ignored(env):
    assert await say(env, ALI, "زهو شلونك اليوم") is None


async def test_help_menu_and_staff(env):
    out = await say(env, ALI, "الاوامر")
    assert "قائمة أوامر" in out
    out = await say(env, ALI, "قائمة الإدارة")
    assert "Creator" in out


async def test_rate_limit(env):
    outs = [await say(env, ALI, "رتبتي") for _ in range(7)]
    assert any(o and "على كيفك" in o for o in outs)


def test_keyboards_fit_limits():
    uid = 9_999_999_999
    for rank in Rank:
        kb = help_main_keyboard(uid, rank)
        for row in kb.inline_keyboard:
            for b in row:
                assert b.callback_data is None or len(b.callback_data.encode()) <= 64
    for sec in SECTIONS:
        for private in (True, False):
            assert len(section_text(sec, registry, Rank.DEVELOPER, private=private)) < 4096
    start_keyboard("ZhooBot", True)


async def test_all_screens_render(env):
    from html.parser import HTMLParser

    from zhoo.core import texts as T
    from zhoo.handlers import views

    svc = env[0]
    await svc.groups.upsert(GROUP, "مجموعة <تجربة>", "testgrp")
    await svc.audit.log("rank_change", chat_id=GROUP, actor_id=1, target_id=2)
    screens = [
        await views.about_text(svc), await views.owner_panel_text(svc),
        await views.audit_text(svc), await views.groups_text(svc),
        T.START_PRIVATE.format(name="x"), T.ADDED_TO_GROUP.format(title="x"),
        T.NEW_GROUP_NOTICE.format(title="x", chat_id=1, by="y"),
        T.LEFT_GROUP_NOTICE.format(title="x", chat_id=1), T.ERROR_NOTICE.format(error="e", where="w"),
    ]

    class Checker(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack = []

        def handle_starttag(self, tag, attrs):
            self.stack.append(tag)

        def handle_endtag(self, tag):
            assert self.stack and self.stack.pop() == tag

    for s in screens:
        c = Checker()
        c.feed(s)
        assert not c.stack, s
    assert "&lt;تجربة&gt;" in screens[3]
