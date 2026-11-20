"""اختبارات المرحلة 9: الإذاعة، النسخ والاستعادة، التقارير، فحص النظام، والمساعدين."""
import asyncio
import sqlite3
from types import SimpleNamespace

import pytest
from telegram import Chat, Message, Update, User

from zhoo.config import Settings
from zhoo.core.context import Services
from zhoo.database.db import Database
from zhoo.handlers import router
from zhoo.handlers.start import cmd_start
from zhoo.systems import backup, owner
from tests.test_flow import ALI, CREATOR, DEV, GROUP, SARA, FakeBot, _mid, env, say  # noqa: F401

PRIV = Chat(DEV, Chat.PRIVATE)


async def _private(env, user_id, text):
    svc, bot, ctx = env
    bot.sent.clear()
    chat = Chat(user_id, Chat.PRIVATE)
    msg = Message(next(_mid), None, chat, from_user=User(user_id, f"U{user_id}", False), text=text)
    msg.set_bot(bot)
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return bot.sent[-1] if bot.sent else None


def _q(user_id, answers):
    async def answer(text=None, show_alert=False):
        answers.append(text)
    return SimpleNamespace(from_user=SimpleNamespace(id=user_id, full_name="U"), answer=answer)


def _pmsg(edits, chat_id=DEV):
    async def edit_text(text, reply_markup=None):
        edits.append((text, reply_markup))
    return SimpleNamespace(chat=SimpleNamespace(id=chat_id, type=Chat.PRIVATE), edit_text=edit_text)


# ── تتبع /start ──
async def test_start_marks_user_for_broadcast(env):
    svc, bot, ctx = env
    msg = Message(next(_mid), None, Chat(ALI, Chat.PRIVATE), from_user=User(ALI, "A", False), text="/start")
    msg.set_bot(bot)
    await cmd_start(Update(next(_mid), message=msg), ctx)
    assert ALI in await svc.users.started_ids()


# ── الإذاعة ──
async def test_broadcast_full_flow(env):
    svc, bot, ctx = env
    await svc.groups.upsert(GROUP, "g", None)
    await svc.groups.upsert(-100777, "g2", None)
    await svc.users.upsert(ALI, "A", None, None, False)
    await svc.users.upsert(SARA, "S", None, None, False)
    await svc.users.set_started(ALI, True)
    await svc.users.set_started(SARA, True)
    bot.blocked = {SARA, -100777}

    assert "منو تريد" in await _private(env, DEV, "اذاعة")
    answers, edits = [], []
    await owner.on_broadcast_button(_q(DEV, answers), _pmsg(edits), svc, bot, "t", "all")
    assert "دزلي رسالة" in edits[-1][0]
    out = await _private(env, DEV, "مرحبا بالجميع 🌸")
    assert "مُـعَـايَـنَـة" in out and "<b>4</b>" in out
    assert ("copy", DEV, ) == bot.calls[-1][:2]  # المعاينة انرسلت للمطور
    bot.calls.clear()
    await owner.on_broadcast_button(_q(DEV, answers), _pmsg(edits), svc, bot, "go", "-")
    for _ in range(50):
        await asyncio.sleep(0.02)
        if not svc.broadcast_running:
            break
    copies = {c[1] for c in bot.calls if c[0] == "copy"}
    assert copies == {GROUP, ALI}
    assert "خِـلْـصَـت" in bot.sent[-1] and "<b>2</b>" in bot.sent[-1]
    # اللي حظروا البوت ينشالون من القوائم
    assert SARA not in await svc.users.started_ids()
    assert -100777 not in await svc.groups.active_ids()


async def test_broadcast_dev_only(env):
    svc, bot, _ = env
    assert await _private(env, ALI, "اذاعة") is None  # مخفي
    answers = []
    await owner.on_broadcast_button(_q(ALI, answers), _pmsg([], ALI), svc, bot, "t", "all")
    assert "للمطور" in answers[-1]


# ── النسخ والاستعادة ──
@pytest.fixture
async def file_env(tmp_path):
    path = tmp_path / "zhoo.db"
    db = Database(path)
    await db.connect()
    svc = Services.build(Settings(token="1:x", owner_id=DEV, db_path=path, log_dir=tmp_path), db)
    await svc.bot_settings.load()
    yield svc, tmp_path
    await db.close()


async def test_backup_is_consistent_and_verified(file_env):
    svc, tmp = file_env
    await svc.groups.upsert(GROUP, "g", None)
    path, stats = await backup.make_backup(svc, "manual")
    assert path.exists() and stats["groups"] == 1 and stats["version"] >= 10
    assert backup.verify_file(path) is not None
    bad = tmp / "bad.db"
    bad.write_bytes(b"not a database at all")
    assert backup.verify_file(bad) is None


async def test_auto_backup_keeps_last_seven(file_env):
    svc, _ = file_env
    for i in range(9):
        p, _ = await backup.make_backup(svc, "auto")
        p.rename(p.with_name(f"zhoo-2026010{i}-000000-auto.db"))
    await backup.make_backup(svc, "auto")
    assert len(list(backup.backup_dir(svc).glob("*-auto.db"))) == 7


async def test_restore_roundtrip(file_env):
    svc, tmp = file_env
    await svc.groups.upsert(GROUP, "قديمة", None)
    snap, _ = await backup.make_backup(svc, "manual")
    upload = tmp / "upload.db"
    upload.write_bytes(snap.read_bytes())
    # تغييرات بعد النسخة
    await svc.groups.upsert(-100999, "جديدة", None)
    await svc.group_settings.set(GROUP, "welcome_on", "0", 1)
    assert await svc.groups.count_all() == 2
    pre = await backup.restore(svc, upload)
    assert pre.exists()
    assert await svc.groups.count_all() == 1  # رجعت للنسخة
    assert await svc.group_settings.get(GROUP, "welcome_on") == "1"  # الذاكرة المؤقتة انمسحت


async def test_restore_reverts_on_corrupt_file(file_env):
    svc, tmp = file_env
    await svc.groups.upsert(GROUP, "g", None)
    bad = tmp / "bad.db"
    conn = sqlite3.connect(bad)
    conn.execute("CREATE TABLE x (a)")
    conn.commit()
    conn.close()
    with pytest.raises(Exception):
        await backup.restore(svc, bad)
    assert await svc.groups.count_all() == 1  # البيانات الأصلية رجعت


async def test_backup_command_sends_document(env):
    svc, bot, _ = env
    await _private(env, DEV, "نسخة احتياطية")
    assert any(c[0] == "document" and c[1] == DEV for c in bot.calls)


# ── التقارير والفحص ──
async def test_reports_and_export(env):
    svc, bot, _ = env
    await svc.groups.upsert(GROUP, "g", None)
    await say(env, ALI, "مرحبا بالجميع")
    assert "تَـقْـرِيـر زَهـو" in await _private(env, DEV, "تقرير")
    assert "آخر 7 أيام" in await say(env, CREATOR, "تقرير المجموعة")
    assert "يحتاج رتبة" in await say(env, ALI, "تقرير المجموعة")
    out = await say(env, CREATOR, "تصدير الأعضاء")
    assert "بالخاص" in out
    doc = [c for c in bot.calls if c[0] == "document"][-1]
    assert doc[1] == CREATOR and doc[2].endswith(".csv") and doc[3] > 20


async def test_health(env):
    out = await _private(env, DEV, "فحص النظام")
    assert "فَـحْـص الـنِّـظَـام" in out and "✅ سليمة" in out


# ── المساعدين ──
async def test_helpers_limited_access(env):
    svc, bot, ctx = env
    assert await _private(env, ALI, "تقرير") is None
    assert "مساعد" in await _private(env, DEV, "رفع مساعد " + str(ALI))
    assert "تَـقْـرِيـر" in await _private(env, ALI, "تقرير")
    assert "فَـحْـص" in await _private(env, ALI, "فحص النظام")
    assert await _private(env, ALI, "نسخة احتياطية") is None  # النسخ للمطور بس
    assert await _private(env, ALI, "اذاعة") is None
    answers = []
    await owner.on_owner_button(_q(ALI, answers), _pmsg([], ALI), svc, ctx, "backup")
    assert "للمطور" in answers[-1]
    edits = []
    await owner.on_owner_button(_q(ALI, answers), _pmsg(edits, ALI), svc, ctx, "main")
    labels = [b.text for row in edits[-1][1].inline_keyboard for b in row]
    assert "📢 إذاعة" not in labels and "📊 تقرير" in labels
    assert str(ALI) in await _private(env, DEV, "المساعدين")
    assert "انشال" in await _private(env, DEV, "تنزيل مساعد " + str(ALI))
    svc.command_limiter._hits.clear()  # رسائل الاختبار السريعة
    assert await _private(env, ALI, "تقرير") is None
