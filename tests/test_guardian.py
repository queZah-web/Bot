"""صد الهجوم، الوضع الليلي، انتهاء التحذيرات، قناة السجل، «قصدك؟»، ورسالة التشغيل."""
from types import SimpleNamespace

from telegram import Chat, Message, Update, User

from zhoo.core.ranks import Rank
from zhoo.database.db import now
from zhoo.systems import guardian, locks, logchannel, protect, suggest
from tests.test_flow import ALI, CREATOR, DEV, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    guardian._joins.clear()


async def _join(env, uid, adder=None):
    svc, bot, ctx = env
    member = User(uid, f"N{uid}", False)
    msg = Message(next(_mid), None, CHAT, from_user=adder or member, new_chat_members=[member])
    msg.set_bot(bot)
    await protect.on_new_members(Update(next(_mid), message=msg), ctx)


def _kicked(bot):
    return {c[1] for c in bot.calls if c[0] == "ban"}


# ── صد الهجوم ──
async def test_raid_kicks_wave_and_locks_join(env):
    svc, bot, _ = env
    await _setup(env)
    for i in range(guardian.RAID_JOINS - 1):
        await _join(env, 70000 + i)
    assert not _kicked(bot)                                   # أقل من الحد: عادي
    bot.sent.clear()
    await _join(env, 70100)                                   # الموجة تكتمل
    assert len(_kicked(bot)) == guardian.RAID_JOINS
    assert any("صَـد هُـجُـوم" in (t or "") for t in bot.sent)
    assert await guardian.raid_left(svc, GROUP) > 0
    bot.calls.clear()
    await _join(env, 70200)                                   # وقت القفل: ينطرد فوراً
    assert 70200 in _kicked(bot)
    svc.command_limiter._hits.clear()
    assert "انفتح" in await say(env, CREATOR, "انهاء الهجوم")
    bot.calls.clear()
    await _join(env, 70300)
    assert not _kicked(bot)


async def test_raid_ignores_admin_adds_and_toggle(env):
    svc, bot, _ = env
    await _setup(env)
    for i in range(guardian.RAID_JOINS + 3):                  # المالك يضيفهم
        await _join(env, 71000 + i, adder=User(CREATOR, "C", False))
    assert not _kicked(bot)
    await say(env, CREATOR, "تعطيل صد الهجوم")
    for i in range(guardian.RAID_JOINS + 3):
        await _join(env, 72000 + i)
    assert not _kicked(bot)


# ── الوضع الليلي ──
def test_window():
    assert guardian.in_window(3, 2, 8) and not guardian.in_window(8, 2, 8)
    assert guardian.in_window(23, 22, 6) and guardian.in_window(1, 22, 6) and not guardian.in_window(12, 22, 6)


async def test_night_locks_and_unlocks(env):
    svc, bot, _ = env
    await _setup(env)
    assert "2 ص" in await say(env, CREATOR, "تفعيل الوضع الليلي 2 8")
    assert await guardian.night_tick(bot, svc, GROUP, 3) == "start"
    assert await locks.is_locked(svc, GROUP, "chat")
    assert await guardian.night_tick(bot, svc, GROUP, 4) is None
    assert await guardian.night_tick(bot, svc, GROUP, 8) == "end"
    assert not await locks.is_locked(svc, GROUP, "chat")


async def test_night_respects_manual_lock(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "تفعيل الوضع الليلي 2 8")
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "قفل الدردشة")
    assert await guardian.night_tick(bot, svc, GROUP, 3) is None
    assert await guardian.night_tick(bot, svc, GROUP, 9) is None
    assert await locks.is_locked(svc, GROUP, "chat")           # قفل الإدارة يبقى


async def test_night_bad_hours(env):
    await _setup(env)
    assert "ساعتين" in await say(env, CREATOR, "تفعيل الوضع الليلي 5 5")


# ── انتهاء التحذيرات ──
async def test_warnings_expire(env):
    svc = env[0]
    await _setup(env)
    await svc.punishments.add_warning(GROUP, ALI, CREATOR, None)
    await svc.db.execute("UPDATE warnings SET created_at = ?", (now() - 8 * 86400,))
    await guardian.expire_warnings(svc)
    assert await svc.punishments.warning_count(GROUP, ALI) == 1       # بدون مدة: تبقى
    assert "7" in await say(env, CREATOR, "مدة التحذيرات 7")
    await guardian.expire_warnings(svc)
    assert await svc.punishments.warning_count(GROUP, ALI) == 0
    svc.command_limiter._hits.clear()
    assert "365" in await say(env, CREATOR, "مدة التحذيرات 999")


# ── قناة السجل ──
async def test_log_channel_receives_actions(env):
    svc, bot, _ = env
    await _setup(env)
    svc.audit.listeners.append(lambda *a: logchannel.on_audit(bot, svc, *a))
    assert "ضيف زهو" in await say(env, CREATOR, "تعيين قناة السجل")
    svc.command_limiter._hits.clear()
    assert "تَـمَّ تَـعْـيِـيـن" in await say(env, CREATOR, "تعيين قناة السجل -100777")
    bot.dm.clear()
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "كتم", reply_to=ALI)
    await svc.audit.drain()
    logs = [t for cid, t in bot.dm if cid == -100777]
    assert logs and "🔇 كتم" in logs[-1] and f"tg://user?id={ALI}" in logs[-1]
    # المسح العادي ما ينرسل (حتى ما تزدحم القناة)
    bot.dm.clear()
    await svc.audit.log("guard_lock_photos", chat_id=GROUP, actor_id=bot.id, target_id=ALI)
    await svc.audit.drain()
    assert not [t for cid, t in bot.dm if cid == -100777]
    svc.command_limiter._hits.clear()
    assert "توقف" in await say(env, CREATOR, "حذف قناة السجل")


def test_log_labels():
    assert logchannel.label("ban", {}) == "🚫 حظر"
    assert "سب" in logchannel.label("swear_mute", {})
    assert logchannel.label("swear_delete", {}) is None
    assert logchannel.label("guard_lock_photos", {}) is None


# ── قصدك؟ ──
def test_suggestion_words():
    assert suggest.suggestion("حضر") == "حظر"
    assert suggest.suggestion("حظر") is None
    assert suggest.suggestion("السلام عليكم يا جماعة الخير") is None


async def test_suggest_only_for_staff_with_target(env):
    svc, bot, _ = env
    await _setup(env)
    suggest._limiter._hits.clear()
    assert await say(env, ALI, "حضر", reply_to=SARA) is None          # عضو: لا
    assert await say(env, CREATOR, "حضر") is None                     # بدون هدف: لا
    assert "قصدك <code>حظر</code>" in await say(env, CREATOR, "حضر", reply_to=SARA)


# ── رسالة التشغيل ──
async def test_started_message_warns_on_empty_db(env):
    from zhoo import app as app_mod
    svc, bot, _ = env
    fake = SimpleNamespace(bot=bot)
    bot.dm.clear()
    await app_mod._notify_started(fake, svc)
    assert any("فارغة" in t for _, t in bot.dm)
    await svc.groups.upsert(GROUP, "g", None)
    bot.dm.clear()
    await app_mod._notify_started(fake, svc)
    assert bot.dm and not any("فارغة" in t for _, t in bot.dm)
