"""الرتب الجديدة، لوحة الصلاحيات، التنزيل الكامل، المسح والمنع والبوتات، وتغيير معلومات المجموعة."""
from types import SimpleNamespace

from telegram import Chat, ChatMemberAdministrator, Document, Message, PhotoSize, Sticker, Update, User
from telegram.constants import ChatMemberStatus

from zhoo.core import texts as T
from zhoo.core.ranks import Rank
from zhoo.handlers import router
from zhoo.systems import cleanup, ranks
from tests.test_flow import ALI, BOT_ID, CREATOR, DEV, GROUP, SARA, _mid, env, say  # noqa: F401

CHAT = Chat(GROUP, Chat.SUPERGROUP, title="g")


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()


def _bot_can_promote(env):
    svc, bot, _ = env
    bot.admins[BOT_ID] = ChatMemberAdministrator(
        User(BOT_ID, "Zhoo", True), False, False, True, True, True, True, True, True, True, False, False, False)
    bot.promotions = []

    async def promote_chat_member(chat_id, user_id, **kw):
        bot.promotions.append((user_id, kw.get("can_restrict_members")))
        return True
    bot.promote_chat_member = promote_chat_member
    svc.perms.invalidate(GROUP)


def _make_tg_admin(env, user_id):
    svc, bot, _ = env
    bot.admins[user_id] = SimpleNamespace(user=User(user_id, f"U{user_id}", False),
                                          status=ChatMemberStatus.ADMINISTRATOR, is_anonymous=False)
    svc.perms.invalidate(GROUP)


class _Q:
    def __init__(self, uid):
        self.from_user = SimpleNamespace(id=uid)
        self.answers = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append(text)


def _msg():
    async def edit_reply_markup(reply_markup=None):
        return True

    async def edit_text(text, **kw):
        return True
    return SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_reply_markup=edit_reply_markup, edit_text=edit_text)


async def _send(env, user_id, **kw):
    svc, bot, ctx = env
    msg = Message(next(_mid), None, CHAT, from_user=User(user_id, f"U{user_id}", False), **kw)
    msg.set_bot(bot)
    bot.calls.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    return [c[0] for c in bot.calls]


# ── ١) الرتب الجديدة ──
async def test_new_rank_order_and_names(env):
    svc = env[0]
    await _setup(env)
    assert "مالك أساسي" in await say(env, CREATOR, "رفع مالك اساسي", reply_to=SARA)
    assert await svc.members.get_rank(GROUP, SARA) == Rank.PRIMARY_OWNER
    assert "منشئ" in await say(env, SARA, "رفع منشئ", reply_to=ALI)        # المالك الأساسي يرفع منشئ
    assert await svc.members.get_rank(GROUP, ALI) == Rank.GENERAL_MANAGER
    svc.command_limiter._hits.clear()
    assert "يحتاج رتبة" in await say(env, ALI, "رفع مالك اساسي", reply_to=SARA)
    assert "U4000004" in await say(env, ALI, "المالكين الأساسيين")
    assert "U3000003" in await say(env, ALI, "المنشئين")
    assert Rank.OWNER < Rank.PRIMARY_OWNER < Rank.CREATOR


# ── ٢) لوحة الصلاحيات ──
async def test_promotion_shows_permissions_panel(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "رفع مدير", reply_to=SARA)
    assert "تكدر تعدل صلاحياته" in out
    kb = bot.last_kw["reply_markup"].inline_keyboard
    datas = [b.callback_data for row in kb for b in row]
    assert f"pm:{SARA}:ban" in datas and f"pm:{SARA}:files" in datas and f"pm:{SARA}:r" in datas
    ban_btn = next(b for row in kb for b in row if b.callback_data == f"pm:{SARA}:ban")
    assert ban_btn.text.startswith("✅")                                   # المدير يحظر افتراضياً


async def test_revoke_ban_from_manager(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "رفع مدير", reply_to=SARA)
    q = _Q(CREATOR)
    await ranks.on_perm_button(q, _msg(), svc, bot, str(SARA), "ban")
    assert "الحظر" in q.answers[-1] and q.answers[-1].startswith("▫️")
    out = await say(env, SARA, "حظر", reply_to=ALI)
    assert "مسحوبة منك" in out and ("ban", ALI, None) not in bot.calls
    assert "تَـمَّ الـكَـتْـم" in await say(env, SARA, "كتم", reply_to=ALI)     # باقي صلاحياته شغّالة
    await ranks.on_perm_button(q, _msg(), svc, bot, str(SARA), "r")         # رجوع حسب الرتبة
    svc.command_limiter._hits.clear()
    assert "تَـمَّ الـحَـظْـر" in await say(env, SARA, "حظر", reply_to=ALI)


async def test_grant_files_to_vip_and_editor_rules(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "رفع مميز", reply_to=SARA)
    await say(env, CREATOR, "قفل الملفات")
    assert (await _send(env, SARA, document=Document("d", "du")))[0] == "delete"
    q = _Q(CREATOR)
    await ranks.on_perm_button(q, _msg(), svc, bot, str(SARA), "files")
    assert "delete" not in await _send(env, SARA, document=Document("d", "du"))   # صار يكدر
    # عضو ما يكدر يعدل
    qa = _Q(ALI)
    await ranks.on_perm_button(qa, _msg(), svc, bot, str(SARA), "ban")
    assert qa.answers[-1] == T.PERM_NOT_ALLOWED
    # أدمن ما يكدر ينطي صلاحية الحظر (لأن ما عنده)
    await svc.members.set_rank(GROUP, ALI, Rank.ADMIN, CREATOR)
    await ranks.on_perm_button(qa, _msg(), svc, bot, str(SARA), "ban")
    assert qa.answers[-1] == T.PERM_YOU_LACK
    out = await say(env, SARA, "صلاحياتي")
    assert "الملفات والصوتيات" in out.split("ما تكدر")[0]


# ── ٣) التنزيل الكامل ──
async def test_demote_strips_everything_including_telegram_admin(env):
    svc, bot, _ = env
    await _setup(env)
    _bot_can_promote(env)
    out = await say(env, CREATOR, "رفع مشرف", reply_to=SARA)
    assert "مشرف بتيليجرام" in out and (SARA, True) in bot.promotions
    _make_tg_admin(env, SARA)
    await ranks.on_perm_button(_Q(CREATOR), _msg(), svc, bot, str(SARA), "ban")   # صلاحية مخصصة

    async def promote_and_forget(chat_id, user_id, **kw):
        bot.promotions.append((user_id, kw.get("can_restrict_members")))
        bot.admins.pop(user_id, None)
        return True
    bot.promote_chat_member = promote_and_forget
    out = await say(env, CREATOR, "تنزيل", reply_to=SARA)
    assert "انسحبت كل صلاحياته" in out and "إشرافه بتيليجرام" in out
    assert (SARA, False) in bot.promotions
    assert await svc.members.get_rank(GROUP, SARA) == Rank.MEMBER
    assert await svc.member_perms.get(GROUP, SARA) == (frozenset(), frozenset())


async def test_supervisor_without_promote_right(env):
    await _setup(env)
    out = await say(env, CREATOR, "رفع مشرف", reply_to=SARA)
    assert "إضافة مشرفين" in out


# ── ٤) المسح ──
async def test_clear_rank_lists_and_all(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    await svc.members.set_rank(GROUP, ALI, Rank.VIP, CREATOR)
    assert "نزلت <b>1</b>" in await say(env, CREATOR, "مسح المدراء")
    assert await svc.members.get_rank(GROUP, SARA) == Rank.MEMBER
    assert "ماكو" in await say(env, CREATOR, "مسح المدراء")
    out = await say(env, CREATOR, "مسح الكل")
    assert "متأكد" in out
    await cleanup.on_clear_button(_Q(ALI), _msg(), svc, bot, str(CREATOR), "y")       # مو صاحب الطلب
    assert await svc.members.get_rank(GROUP, ALI) == Rank.VIP
    await cleanup.on_clear_button(_Q(CREATOR), _msg(), svc, bot, str(CREATOR), "y")
    assert await svc.members.get_rank(GROUP, ALI) == Rank.MEMBER


async def test_clear_banned_and_purge(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "حظر", reply_to=ALI)
    out = await say(env, CREATOR, "مسح المحظورين")
    assert "<b>1</b>" in out and ("unban", ALI) in bot.calls
    deleted = []

    async def delete_messages(chat_id, ids, **kw):
        deleted.append(list(ids))
        return True
    bot.delete_messages = delete_messages
    await say(env, CREATOR, "مسح 5")
    assert len(deleted[-1]) == 6                                   # 5 + رسالة الأمر
    await say(env, CREATOR, "مسح", reply_to=ALI)
    assert len(deleted[-1]) == 2
    assert await say(env, ALI, "مسح شي غلط") is None              # مو أمر


# ── ٥) المنع ──
async def test_filters(env):
    svc, bot, ctx = env
    await _setup(env)
    stk = Sticker("s", "uniq1", 1, 1, False, False, "regular", emoji="😂")
    reply = Message(next(_mid), None, CHAT, from_user=User(ALI, "A", False), sticker=stk)
    msg = Message(next(_mid), None, CHAT, from_user=User(CREATOR, "C", False), text="منع", reply_to_message=reply)
    msg.set_bot(bot)
    reply.set_bot(bot)
    bot.sent.clear()
    await router.on_message(Update(next(_mid), message=msg), ctx)
    assert "تَـمَّ الـمَـنْـع" in bot.sent[-1]
    assert (await _send(env, ALI, sticker=stk))[0] == "delete"
    assert "delete" not in await _send(env, ALI, sticker=Sticker("s2", "other", 1, 1, False, False, "regular"))
    await say(env, CREATOR, "منع كلمة خايبة")
    assert (await _send(env, ALI, text="هاي كلمة خايبة والله"))[0] == "delete"
    assert "delete" not in await _send(env, ALI, text="كلمة حلوة")
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    assert "delete" not in await _send(env, SARA, sticker=stk)            # المشرف مستثنى
    out = await say(env, CREATOR, "قائمة المنع")
    assert "ملصقات" in out and "كلمة خايبة" in out
    assert "رجع" in await say(env, CREATOR, "الغاء منع كلمة خايبة")
    assert "انمسحت" in await say(env, CREATOR, "مسح قائمة المنع")
    assert "delete" not in await _send(env, ALI, sticker=stk)


# ── ٦) البوتات والمحذوفين ورفع القيود ──
async def test_bots_deleted_and_lift_all(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.db.execute("INSERT OR REPLACE INTO users (user_id, first_name, is_bot, first_seen, last_seen) "
                         "VALUES (777, 'SpamBot', 1, 0, 0)")
    await svc.members.set_added_by(GROUP, 777, 0)
    assert "SpamBot" in await say(env, CREATOR, "كشف البوتات")
    await say(env, CREATOR, "طرد البوتات")
    assert ("ban", 777, None) in bot.calls

    await svc.db.execute("INSERT OR REPLACE INTO users (user_id, first_name, is_bot, first_seen, last_seen) "
                         "VALUES (888, '', 0, 0, 0)")
    await svc.members.set_added_by(GROUP, 888, 0)

    async def get_chat_member(chat_id, user_id, **kw):
        name = "" if user_id == 888 else "Someone"
        return SimpleNamespace(status=ChatMemberStatus.MEMBER, user=User(user_id, name, False))
    bot.get_chat_member = get_chat_member
    bot.calls.clear()
    await say(env, CREATOR, "طرد المحذوفين")
    assert ("ban", 888, None) in bot.calls and ("ban", 777, None) not in bot.calls

    await say(env, CREATOR, "كتم", reply_to=ALI)
    out = await say(env, CREATOR, "رفع القيود", reply_to=ALI)
    assert "رَفْـع الـقُـيُـود" in out
    assert not await svc.punishments.is_active(GROUP, ALI, "mute")


# ── ٧) صورة واسم وبايو المجموعة ──
async def test_change_title_bio_photo(env):
    svc, bot, _ = env
    await _setup(env)
    done = {}

    async def set_chat_title(chat_id, title, **kw):
        done["title"] = title

    async def set_chat_description(chat_id, description=None, **kw):
        done["bio"] = description

    async def set_chat_photo(chat_id, photo, **kw):
        done["photo"] = photo

    async def get_file(file_id, **kw):
        async def download_as_bytearray():
            return bytearray(b"img")
        return SimpleNamespace(download_as_bytearray=download_as_bytearray)
    bot.set_chat_title, bot.set_chat_description = set_chat_title, set_chat_description
    bot.set_chat_photo, bot.get_file = set_chat_photo, get_file

    assert "تَـغَـيَّـر اسْـم" in await say(env, CREATOR, "تغيير اسم المجموعه عائلة زهو")
    assert done["title"] == "عائلة زهو"
    assert "اكتب البايو" in await say(env, CREATOR, "تغيير بايو المجموعه")
    assert "تَـغَـيَّـر بَـايُـو" in await say(env, CREATOR, "هنا نتسولف بكل احترام 🤍")
    assert done["bio"] == "هنا نتسولف بكل احترام 🤍"
    assert "ارسل الصورة" in await say(env, CREATOR, "تغيير صورة المجموعه")
    assert "أنتظر صورة" in await say(env, CREATOR, "هاي مو صورة")
    await _send(env, CREATOR, photo=[PhotoSize("f", "u", 10, 10)])
    assert done["photo"] == b"img"
    assert "يحتاج رتبة" in await say(env, ALI, "تغيير اسم المجموعه شي")


# ── ٨) المتفاعلين والكشف ──
async def test_top_active_list(env):
    svc, bot, _ = env
    await _setup(env)
    for _ in range(5):
        await say(env, ALI, "رسالة")
    for _ in range(2):
        await say(env, SARA, "رسالة")
    out = await say(env, SARA, "المتفاعلين")
    assert "الـمُـتَـفَـاعِـلِـيـن" in out and "🥇" in out and "▰" in out and "رسالة ⋅" in out
    assert out.index("U3000003") < out.index("U4000004")          # علي أول
    assert "ترتيبك: <b>#2</b>" in out
    assert "بعدك ما كتبت" in await say(env, CREATOR, "المتفاعلين") or "ترتيبك" in bot.sent[-1]


async def test_inspect_report(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, ALI, "هلا")
    await say(env, CREATOR, "قفل السب بالمسح")
    await say(env, ALI, "كسمك")
    await say(env, ALI, "يا حمار")
    await say(env, CREATOR, "تحذير", reply_to=ALI)
    await say(env, CREATOR, "كتم", reply_to=ALI)
    svc.command_limiter._hits.clear()
    out = await say(env, CREATOR, "كشف", reply_to=ALI)
    assert "كَـشْـف عُـضْـو" in out and f"<code>{ALI}</code>" in out
    assert "السب: <b>2</b> مرة (🟢 1 ⋅ 🔴 1)" in out
    assert "التحذيرات: <b>1/3</b>" in out and "كتم 1" in out and "الحالية: كتم" in out
    assert "حساب شخصي" in out
    assert "يحتاج رتبة" in await say(env, SARA, "كشف", reply_to=ALI)
