"""القفل من تيليجرام نفسه (المنع): «لا يُسمح بإرسال الوسائط»."""
from types import SimpleNamespace

from telegram import ChatPermissions

from zhoo.systems import locks
from tests.test_flow import ALI, CREATOR, GROUP, env, say  # noqa: F401


class PermBot:
    """يحفظ صلاحيات المجموعة حتى نتأكد شنو انطفى."""
    def __init__(self, bot):
        self.perms = ChatPermissions.all_permissions()
        self.bot = bot

        async def set_chat_permissions(chat_id, permissions, **kw):
            self.perms = permissions
            bot.calls.append(("chat_perms", permissions.can_send_messages))
            return True

        async def get_chat(chat_id, **kw):
            return SimpleNamespace(permissions=self.perms)
        bot.set_chat_permissions = set_chat_permissions
        bot.get_chat = get_chat


async def _setup(env):
    svc, bot, _ = env
    await svc.groups.upsert(GROUP, "g", None)
    return PermBot(bot)


async def _say(env, user, text):
    env[0].command_limiter._hits.clear()
    return await say(env, user, text)


async def test_lock_photos_is_native_by_default(env):
    pb = await _setup(env)
    out = await _say(env, CREATOR, "قفل الصور")
    assert "منع" in out and "لا يُسمح" in out
    assert pb.perms.can_send_photos is False and pb.perms.can_send_videos is not False
    assert pb.perms.can_send_messages is not False
    await _say(env, CREATOR, "قفل الفيديو")
    assert pb.perms.can_send_videos is False and pb.perms.can_send_video_notes is False
    await _say(env, CREATOR, "فتح الصور")
    assert pb.perms.can_send_photos is True and pb.perms.can_send_videos is False


async def test_delete_mode_keeps_permissions(env):
    pb = await _setup(env)
    await _say(env, CREATOR, "قفل الصور بالمسح")
    assert pb.perms.can_send_photos is not False
    assert await locks.get_mode(env[0], GROUP, "photos") == "delete"


async def test_lock_all_media(env):
    pb = await _setup(env)
    out = await _say(env, CREATOR, "قفل الوسائط")
    assert "لا يُسمح بإرسال الوسائط" in out
    for f in ("can_send_photos", "can_send_videos", "can_send_audios", "can_send_documents",
              "can_send_voice_notes", "can_send_polls", "can_send_other_messages"):
        assert getattr(pb.perms, f) is False, f
    assert pb.perms.can_send_messages is not False
    # الدردشة: قفلها وفتحها ما يرجّع الوسائط
    await _say(env, CREATOR, "قفل الدردشة")
    assert pb.perms.can_send_messages is False
    await _say(env, CREATOR, "فتح الدردشة")
    assert pb.perms.can_send_messages is True and pb.perms.can_send_photos is False
    await _say(env, CREATOR, "فتح الوسائط")
    assert pb.perms.can_send_photos is True and pb.perms.can_send_other_messages is True


async def test_shared_gifs_stickers(env):
    pb = await _setup(env)
    await _say(env, CREATOR, "قفل الملصقات بالمنع")
    await _say(env, CREATOR, "قفل المتحركات بالمنع")
    await _say(env, CREATOR, "فتح المتحركات")
    assert pb.perms.can_send_other_messages is False          # الملصقات بعدها ممنوعة
    await _say(env, CREATOR, "فتح الملصقات")
    assert pb.perms.can_send_other_messages is True


async def test_no_rights_falls_back_to_delete(env, monkeypatch):
    svc = env[0]
    await _setup(env)

    async def no_rights(bot, chat_id):
        return SimpleNamespace(can_restrict_members=False, can_delete_messages=True)
    monkeypatch.setattr(svc.perms, "bot_rights", no_rights)
    out = await _say(env, CREATOR, "قفل الصور")
    assert "بالمسح" in out and await locks.get_mode(svc, GROUP, "photos") == "delete"
