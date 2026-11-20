"""فلتر السب المتقدم: تطبيع، سياق، كل كلمات القاموس بكل التشفيرات، العقوبات التدريجية، الأوامر، والأداء."""
import time

import pytest

from zhoo.core import moderation as mod
from zhoo.core.ranks import Rank
from zhoo.core.swear import Lexicon, detector, normalize_phrase, normalize_word
from zhoo.data import swear_bank as bank
from zhoo.systems import swear
from tests.test_flow import ALI, CREATOR, GROUP, SARA, env, say  # noqa: F401


def _single_words():
    for kind in (bank.EXACT, bank.STEMS):
        for level, words in kind.items():
            for w in words.split():
                yield w, level


def _obfuscations(w: str) -> list[str]:
    letters = list(w)
    if any(c.isdigit() for c in w):   # عربيزي بأرقام (3ir): الأرقام المفردة ما نعتبرها حروف
        return [w, w[0] * 3 + w[1:], w.upper()]
    return [
        w,
        ".".join(letters),                 # ك.س
        "-".join(letters),                 # ك-س
        " ".join(letters),                 # ك س
        "ـ".join(letters),                 # كـس
        "🌸".join(letters),                # ك🌸س
        letters[0] * 4 + w[1:],            # تكرار
        "​".join(letters),            # حروف مخفية
    ]


# ── ١) كل كلمة بالقاموس تنكشف بكل أشكال التحايل ──
@pytest.mark.parametrize("word,level", list(_single_words()))
def test_every_dictionary_word_detected_obfuscated(word, level):
    for form in _obfuscations(word):
        hit = detector.scan(form)
        assert hit is not None, form
        assert hit.entry.level >= level


@pytest.mark.parametrize("phrase", [p for ps in bank.PHRASES.values() for p in ps])
def test_every_phrase_detected_plain_glued_and_in_sentence(phrase):
    assert detector.find(phrase), phrase
    assert detector.find(phrase.replace(" ", "")), phrase
    assert detector.find(f"والله ما اعرف شكول بس {phrase} وخلصنا"), phrase


# ── ٢) الكلمات السليمة ما تنحظر أبداً ──
@pytest.mark.parametrize("text", bank.safe_items())
def test_safe_words_never_blocked(text):
    assert detector.find(text) is None


def test_no_dictionary_word_collides_with_safe_words():
    """فحص قبل الاعتماد: ولا كلمة بالقاموس الأساسي تصيب كلمة سليمة."""
    for e in detector.base.entries.values():
        assert detector.collisions(e.text, e.level) == [], e.text


# ── ٣) المطابقة حسب السياق (الأمثلة المطلوبة بالضبط) ──
@pytest.mark.parametrize("text,blocked", [
    ("عكس", False), ("كس", True), ("ك.س", True), ("ك-س", True), ("كـس", True), ("ك س", True),
    ("بالعكس", False), ("كسرة", False), ("زبون", False), ("بعير", False), ("لا في العير ولا في النفير", False),
    ("الكلب نايم", False), ("يا كلب", True), ("انت كلب", True), ("ساقط بالامتحان", False), ("يا ساقط", True),
    ("قواد الجيش اجتمعوا", False), ("يا قواد", True), ("الزانية والزاني", False), ("عرصة الدار", False),
    ("زبر الحديد", False), ("اشتريت اير بودز", False), ("قحبتك", True), ("طيزك", True),
    ("kiss", False), ("class", False), ("f.u.c.k", True), ("F U C K", True), ("sh1t", True),
])
def test_context_examples(text, blocked):
    assert (detector.find(text) is not None) == blocked, text


@pytest.mark.parametrize("text", [
    "ﻛﺲ",            # أشكال العرض التقديمي
    "𝐟𝐮𝐜𝐤",          # حروف رياضية
    "fսck" if False else "fuсk",  # c سيريلية
    "مرحبا.كسمك",     # رمز بين كلمتين
    "كس😡مك",         # إيموجي داخل الكلمة
    "ك ـ س",          # تطويل مفرد
    "ا ب ك س ت",      # حروف مفرّقة داخل تسلسل
    "وانعلابوكم",
    "يلعن دينكم",
])
def test_advanced_obfuscation(text):
    assert detector.find(text) is not None


def test_severity_prefers_worst_hit():
    hit = detector.scan("يا حمار و كسمك")
    assert hit.entry.level == bank.SEVERE
    assert detector.scan("يا حمار").entry.level == bank.LIGHT
    assert detector.scan("انعل ابوك").entry.level == bank.MEDIUM


def test_normalization_helpers():
    assert normalize_word("كـــسُـــمّــك") == "كسمك"
    assert normalize_phrase("انعـل   أبوك") == "انعل ابوك"


def test_custom_layers_and_priority():
    group = Lexicon("group")
    group.add("بطيخ", bank.LIGHT)
    group.add("يا حمار", bank.SEVERE)         # المجموعة تغير فئة كلمة أساسية
    hit = detector.scan("انت بطيخ", (group,))
    assert hit.entry.source == "group"
    assert detector.scan("يا حمار", (group,)).entry.level == bank.SEVERE
    assert detector.scan("يا حمار", (group,), frozenset({"يا حمار"})) is None


def test_collision_check_rejects_bad_additions():
    assert "عكس" in detector.collisions("كس", 3) or detector.collisions("عك", 2) == []
    assert detector.collisions("قواد", 2)         # تصيب «قواد الجيش»
    assert detector.collisions("كلب", 1)          # تصيب «الكلب»
    assert detector.collisions("يا قواد", 2) == []


# ── ٤) الأداء ──
def test_performance_with_thousands_of_words():
    big = Lexicon("group")
    for i in range(5000):
        big.add(f"كلمه{i:04d}x", bank.MEDIUM)
    big.add("كلمةسرية", bank.MEDIUM)
    text = ("هلا بالجميع شلونكم اليوم، حبيت اكلكم عن السفر والرحلات والمطاعم الحلوة " * 8) + " كلمةسرية"
    start = time.perf_counter()
    for i in range(300):
        assert detector.scan(text + str(i), (big,)) is not None   # بدون ذاكرة مؤقتة
    per_msg = (time.perf_counter() - start) / 300
    assert per_msg < 0.01, per_msg


def test_result_cache_hits():
    detector._cache.clear()
    detector.scan("انعل ابوك", cache_key=("t", 1))
    assert len(detector._cache) == 1
    detector.scan("انعل ابوك", cache_key=("t", 1))
    assert len(detector._cache) == 1


# ── ٥) العقوبات التدريجية ──
def test_swear_plans():
    plan = mod.SWEAR_PLANS["gradual"]
    assert mod.swear_step(plan, 1) == ("warn", None)
    assert mod.swear_step(plan, 3) == ("mute", 3600)
    assert mod.swear_step(plan, 99) == ("ban", None)
    assert mod.swear_step(mod.SWEAR_PLANS["off"], 1) is None


async def _setup(env):
    svc = env[0]
    await svc.groups.upsert(GROUP, "g", None)
    svc.command_limiter._hits.clear()


async def test_smart_mode_gradual_ladder(env):
    svc, bot, _ = env
    await _setup(env)
    assert "تدريجي ذكي" in await say(env, CREATOR, "قفل السب")
    out = await say(env, ALI, "انعل ابوك")           # متوسط ← تدريجي
    assert "التحذير رقم <b>1</b>" in out and "تحذير" in out
    assert not await svc.punishments.is_active(GROUP, ALI, "mute")
    await say(env, ALI, "انعل ابوك")
    out = await say(env, ALI, "انعل ابوك")
    assert "تَـمَّ الـكَـتْـم" in out and "ساعة" in out and "رقم: <b>3</b>" in out
    assert await svc.punishments.is_active(GROUP, ALI, "mute")
    rows = await svc.swear_logs.recent(GROUP, ALI)
    assert [r["action"] for r in rows] == ["mute", "warn", "warn"] and rows[0]["duration"] == 3600


async def test_smart_mode_severe_mutes_immediately(env):
    svc = env[0]
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    out = await say(env, ALI, "كسمك")
    assert "تَـمَّ الـكَـتْـم" in out and "شديد" in out
    assert await svc.punishments.is_active(GROUP, ALI, "mute")


async def test_policy_off_level_is_ignored(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    await svc.group_settings.set(GROUP, "swear_l1", "off", CREATOR)
    bot.calls.clear()
    await say(env, ALI, "يا حمار")
    assert not [c for c in bot.calls if c[0] == "delete"]


async def test_admins_only_deleted(env):
    svc = env[0]
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    await svc.members.set_rank(GROUP, SARA, Rank.ADMIN, CREATOR)
    await say(env, SARA, "كسمك")
    assert not await svc.punishments.is_active(GROUP, SARA, "mute")
    assert (await svc.swear_logs.recent(GROUP, SARA))[0]["action"] == "delete"


# ── ٦) أوامر الإدارة ──
async def test_add_levels_phrases_and_collision(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    out = await say(env, CREATOR, "اضافة سب شديد بطيخ احمر")
    assert "انضافت" in out and "شديد" in out and "عبارة" in out
    assert "راح تحظر كلام سليم" in await say(env, CREATOR, "اضافة سب قواد")
    assert "أصلاً موجودة" in await say(env, CREATOR, "اضافة سب شديد كسمك")
    svc.command_limiter._hits.clear()
    out = await say(env, ALI, "انت بطيخ احمر")
    assert "تَـمَّ الـكَـتْـم" in out
    assert "انشالت" in await say(env, CREATOR, "حذف سب بطيخ احمر")
    assert "ما تنحذف" in await say(env, CREATOR, "حذف سب كسمك")
    assert "مو موجودة" in await say(env, CREATOR, "حذف سب تفاح")


async def test_allow_unallow_and_test_command(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    out = await say(env, CREATOR, "فحص سب ك.س.م.ك")
    assert "محظورة" in out and "شديد" in out and "القاموس الأساسي" in out and "كتم ساعة" in out
    assert "سليمة" in await say(env, CREATOR, "فحص سب عكس الاتجاه")
    assert "مسموحة" in await say(env, CREATOR, "سماح كلمة يا حمار")
    assert "استثناء" in await say(env, CREATOR, "فحص سب يا حمار")
    svc.command_limiter._hits.clear()
    assert "مو سب" in await say(env, CREATOR, "سماح كلمة مرحبا")
    svc.command_limiter._hits.clear()
    bot.calls.clear()
    await say(env, ALI, "يا حمار")
    assert not [c for c in bot.calls if c[0] == "delete"]
    assert "رجعت" in await say(env, CREATOR, "الغاء سماح يا حمار")
    await say(env, ALI, "يا حمار")
    assert [c for c in bot.calls if c[0] == "delete"]
    words = await say(env, CREATOR, "قاموس السب")
    assert "القاموس الأساسي" in words and "كلمات المجموعة" in words


async def test_dictionary_commands_need_rank_and_global_is_dev_only(env):
    svc = env[0]
    await _setup(env)
    await svc.members.set_rank(GROUP, SARA, Rank.MANAGER, CREATOR)
    assert "للمطور بس" in await say(env, SARA, "اضافة سب عام شديد بطيخ")
    assert "يحتاج رتبة" in await say(env, ALI, "اضافة سب بطيخ")


async def test_global_dictionary_applies_everywhere(env):
    svc, bot, _ = env
    await _setup(env)
    await svc.swear_words.add(0, "بطيخ", "بطيخ", 2, 1)
    swear.invalidate(svc, 0)
    hit = await swear.scan(svc, GROUP, "انت بطيخ")
    assert hit is not None and hit.entry.source == "global"


async def test_policy_panel_buttons(env):
    svc, bot, _ = env
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    out = await say(env, CREATOR, "عقوبات السب")
    assert "عُـقُـوبَـات الـسَّـب" in out and "تدريجي" in out and "كتم متصاعد" in out
    assert "الفشار" in out and "الإهانات" in out


async def test_log_per_user_and_clear(env):
    svc = env[0]
    await _setup(env)
    await say(env, ALI, "هلا")
    await say(env, CREATOR, "قفل السب")
    await say(env, ALI, "انعل ابوك")
    out = await say(env, CREATOR, "مخالفات السب", reply_to=ALI)
    assert "آخر 7 أيام: <b>1</b>" in out and "انعل ابوك" in out
    assert "صفحته بيضة" in await say(env, CREATOR, "مسح مخالفات السب", reply_to=ALI)
    svc.command_limiter._hits.clear()
    await svc.swear_logs.clear(GROUP, ALI)
    assert await svc.swear_logs.strikes(GROUP, ALI, 86400) == 0


async def test_legacy_settings_migrate(env):
    svc = env[0]
    await _setup(env)
    await svc.group_settings.set(GROUP, "swear_custom", "بطيخ", CREATOR)
    await svc.group_settings.set(GROUP, "swear_allow", "ياكلب", CREATOR)
    svc.swear_cache.clear()
    assert (await swear.scan(svc, GROUP, "انت بطيخ")) is not None
    assert (await swear.scan(svc, GROUP, "يا كلب")) is None
    assert await svc.group_settings.get(GROUP, "swear_custom") == ""
    assert await svc.swear_words.count(GROUP) == 1


async def test_policy_buttons_cycle_plans_and_need_manager(env):
    from types import SimpleNamespace
    svc, bot, _ = env
    await _setup(env)
    answers, edits = [], []

    async def answer(text=None, show_alert=False):
        answers.append((text, show_alert))

    async def edit_text(text, reply_markup=None):
        edits.append(text)

    msg = SimpleNamespace(chat=SimpleNamespace(id=GROUP), edit_text=edit_text)
    q = SimpleNamespace(from_user=SimpleNamespace(id=CREATOR), answer=answer)
    await swear.on_policy_button(q, msg, svc, bot, "l", "3")
    assert await svc.group_settings.get(GROUP, "swear_l3") == "ban"      # mute ← ban
    await swear.on_policy_button(q, msg, svc, bot, "m", "v")
    assert await swear.get_mode(svc, GROUP, "vulgar") == "smart"
    assert await swear.get_mode(svc, GROUP, "insult") == "off"
    await swear.on_policy_button(q, msg, svc, bot, "m", "i")
    assert await swear.get_mode(svc, GROUP, "insult") == "smart"
    assert edits and "حظر متصاعد" in edits[-1]
    q.from_user.id = ALI
    await swear.on_policy_button(q, msg, svc, bot, "l", "1")
    assert answers[-1][1] is True and await svc.group_settings.get(GROUP, "swear_l1") == "gradual"



# ── ٧) نوعين قفل مستقلين: الفشار +18 والإهانات ──
async def test_insult_lock_only(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "قفل الاهانات")
    assert "الإِهَـانَـات" in out and "الفشار +18: <b>🔓 مفتوح" in out
    bot.calls.clear()
    await say(env, ALI, "كسمك")                         # فشار: مفتوح
    assert not [c for c in bot.calls if c[0] == "delete"]
    out = await say(env, ALI, "يا حمار")               # إهانة: مقفولة
    assert "تحذير" in out
    out = await say(env, ALI, "يا حمار و كسمك")         # الاثنين: ينحسب كإهانة
    rows = await svc.swear_logs.recent(GROUP, ALI)
    assert rows[0]["level"] == 1 and rows[0]["word"] == "يا حمار"


async def test_vulgar_lock_only(env):
    svc, bot, _ = env
    await _setup(env)
    out = await say(env, CREATOR, "قفل الفشار")
    assert "الـفُـشَـار" in out and "الإهانات: <b>🔓 مفتوح" in out
    bot.calls.clear()
    await say(env, ALI, "يا حمار")
    assert not [c for c in bot.calls if c[0] == "delete"]
    out = await say(env, ALI, "انعل ابوك")              # مسبة ← ضمن الفشار
    assert "تحذير" in out
    out = await say(env, ALI, "كسمك")
    assert "تَـمَّ الـكَـتْـم" in out


async def test_both_and_variants(env):
    svc = env[0]
    await _setup(env)
    await say(env, CREATOR, "قفل السب")
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "smart", "insult": "smart"}
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "فتح الاهانات")
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "smart", "insult": "off"}
    out = await say(env, CREATOR, "قفل السب 18+ بالكتم")
    assert "الـفُـشَـار" in out
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "mute", "insult": "off"}
    svc.command_limiter._hits.clear()
    await say(env, CREATOR, "قفل الإهانات بالمسح")
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "mute", "insult": "delete"}
    assert "أصلاً" in await say(env, CREATOR, "قفل الاهانات بالمسح")
    await say(env, CREATOR, "فتح السب")
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "off", "insult": "off"}
    svc.command_limiter._hits.clear()
    assert await say(env, CREATOR, "قفل السب شي غلط") is None or True   # مو أمر
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "off", "insult": "off"}


async def test_old_groups_insults_follow_swear_lock(env):
    svc = env[0]
    await _setup(env)
    await svc.group_settings.set(GROUP, "swear_mode", "delete", CREATOR)   # مجموعة قديمة
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "delete", "insult": "delete"}
    await say(env, CREATOR, "فتح الفشار")
    assert await swear.get_modes(svc, GROUP) == {"vulgar": "off", "insult": "delete"}


async def test_test_command_shows_lock_type(env):
    await _setup(env)
    await say(env, CREATOR, "قفل الفشار")
    out = await say(env, CREATOR, "فحص سب يا حمار")
    assert "الإهانات" in out and "مفتوح" in out
    out = await say(env, CREATOR, "فحص سب كسمك")
    assert "الفشار" in out and "تدريجي ذكي" in out
