"""كل نصوص البوت في مكان واحد حتى يسهل تعديلها.

الردود اليومية باللهجة العراقية، وأسماء الأوامر والأقسام بالفصحى.
"""
from __future__ import annotations

LINE = "┄┄┄┄┄┄┄┄┄┄┄┄"
BULLET = "⌯"

BOT_NAME = "زهـو"
BOT_NAME_EN = "ZHOO"

# ── عام ───────────────────────────────────────────
START_PRIVATE = (
    "✦ <b>هلا بيك {name}</b> 💜\n"
    f"{LINE}\n"
    f"{BULLET} آني <b>{BOT_NAME} | {BOT_NAME_EN}</b>\n"
    f"{BULLET} بوت إدارة وحماية للمجموعات، سريع ومرتب وأمين 🛡\n"
    f"{LINE}\n"
    f"{BULLET} ضيفني لمجموعتك وارفعني مشرف بكل الصلاحيات\n"
    f"{BULLET} وبعدها اكتب <code>الاوامر</code> بالمجموعة 👇"
)

START_GROUP = f"{BULLET} هلا بيك، آني زهو 💜 اكتب <code>الاوامر</code> حتى تشوف كل شي"

ABOUT = (
    f"✦ <b>عن {BOT_NAME}</b>\n"
    f"{LINE}\n"
    f"{BULLET} الإصدار: <code>{{version}}</code>\n"
    f"{BULLET} المجموعات: <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} يشتغل من: <b>{{uptime}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} مبني بأمان: كل عملية إدارية تنسجل، والصلاحيات مركزية 🔐"
)

ADDED_TO_GROUP = (
    "✦ <b>هلا بيكم بزهو</b> 💜\n"
    f"{LINE}\n"
    f"{BULLET} شكراً لإضافتي لـ <b>{{title}}</b>\n"
    f"{BULLET} حتى أشتغل صح، ارفعوني <b>مشرف</b> وانطوني صلاحيات:\n"
    "   ▫️ حذف الرسائل\n"
    "   ▫️ حظر المستخدمين\n"
    "   ▫️ دعوة المستخدمين وتثبيت الرسائل\n"
    f"{LINE}\n"
    f"{BULLET} بعدها اكتبوا <code>الاوامر</code> 👇"
)

ZHOO_REPLIES = (
    "عيون زهو 💜",
    "هلا بيك، شتريد؟ 😄",
    "آني هنا، لا تخاف 🛡",
    "اسمك على لساني 😌",
    "تفضل حبيبي 💜",
    "صاحي ومنتبه 👀",
)

# ── الأخطاء والرفض ──────────────────────────────────
NO_PERMISSION = f"{BULLET} هذا الأمر يحتاج رتبة <b>{{rank}}</b> أو أعلى 🔐"
GROUP_ONLY = f"{BULLET} هذا الأمر يشتغل بالمجموعات بس 👥"
PRIVATE_ONLY = f"{BULLET} هذا الأمر يشتغل بالخاص وياي بس 🔒"
MAINTENANCE = f"{BULLET} زهو هسه بالصيانة 🛠 ارجعلي بعد شوية"
ANON_ADMIN = f"{BULLET} انت مشرف مخفي 🥷 طفي خيار «البقاء مجهولاً» حتى أعرف رتبتك"
SLOW_DOWN = "على كيفك شوية 😅"
GENERIC_ERROR = f"{BULLET} صار خلل بسيط، جرب مرة ثانية 🙏"

NEED_TARGET = (
    f"{BULLET} حدد الشخص: رد على رسالته، أو اكتب يوزره أو ايديه وية الأمر 👀\n"
    f"{BULLET} مثال: <code>{{example}}</code>"
)
TARGET_NOT_FOUND = f"{BULLET} ما لگيت هذا الشخص 🤷‍♂️ تأكد من اليوزر أو الايدي"
TARGET_IS_CHANNEL = f"{BULLET} هذي رسالة قناة مو شخص 📢"

# ── الرتب ──────────────────────────────────────────
RANK_SELF = f"{BULLET} ما تكدر تغير رتبتك بنفسك 😄"
RANK_BOT = f"{BULLET} ما يصير ترفع أو تنزل بوت 🤖"
RANK_PROTECTED = f"{BULLET} {{mention}} رتبته محمية ({{rank}}) وما تتغير 🛡"
RANK_TARGET_HIGHER = f"{BULLET} ما تكدر، رتبة {{mention}} ({{rank}}) أعلى منك أو تساويك ⛔"
RANK_CANT_GRANT = f"{BULLET} ما تكدر ترفع لرتبة <b>{{rank}}</b>، لازم رتبتك تكون أعلى منها 🔐"
RANK_SAME = f"{BULLET} {{mention}} هو أصلاً <b>{{rank}}</b> ✅"
RANK_BELOW_FLOOR = (
    f"{BULLET} {{mention}} مشرف بتيليجرام، فرتبته ما تنزل عن <b>{{rank}}</b>\n"
    f"{BULLET} نزّله من إشراف تيليجرام أولاً"
)
RANK_NOT_THAT = f"{BULLET} {{mention}} مو <b>{{rank}}</b> أصلاً 🙃"

RANK_PROMOTED = (
    "✦ <b>تَمَّ الرَّفْعُ بِنَجَاح</b>\n"
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    f"{BULLET} بواسطة: {{actor}}"
)
RANK_DEMOTED = (
    "✦ <b>تَمَّ التَّنْزِيلُ بِنَجَاح</b>\n"
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} كان: {{old}} ← صار: {{rank}}\n"
    f"{BULLET} بواسطة: {{actor}}"
)

STAFF_HEADER = f"✦ <b>طاقم إدارة {{title}}</b>\n{LINE}"
STAFF_EMPTY = f"{BULLET} ماكو أحد مرفوع بهذي الرتبة لحد هسه"
RANK_LIST_HEADER = f"✦ <b>{{plural}}</b>\n{LINE}"

# ── معلومات ────────────────────────────────────────
ID_TEXT = (
    "✦ <b>معلومات {name}</b>\n"
    f"{LINE}\n"
    f"{BULLET} الايدي: <code>{{user_id}}</code>\n"
    f"{BULLET} اليوزر: {{username}}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    "{extra}"
)
MY_RANK = f"{BULLET} رتبتك هنا: {{rank}}"
THEIR_RANK = f"{BULLET} رتبة {{mention}}: {{rank}}"
ACTIVITY = f"{BULLET} رسائل {{mention}} بهذي المجموعة: <b>{{count}}</b> ✉️\n{BULLET} التفاعل: {{level}}"
TOP_ACTIVE_HEADER = f"✦ <b>أكثر المتفاعلين</b> 🔥\n{LINE}"

# ── القوائم ────────────────────────────────────────
HELP_MAIN = (
    f"✦ <b>قائمة أوامر {BOT_NAME}</b>\n"
    f"{LINE}\n"
    f"{BULLET} رتبتك: {{rank}}\n"
    f"{BULLET} اختار القسم اللي تريده 👇"
)
HELP_NOT_YOURS = "هذي القائمة مو إلك، اكتب «الاوامر» حتى تطلعلك قائمتك 😉"
HELP_SOON = (
    f"{BULLET} هذا القسم جاي بالمرحلة <b>{{phase}}</b> 🔜\n"
    f"{BULLET} الأوامر المخطط لها:\n{{planned}}"
)
HELP_LOCKED_HINT = f"\n{LINE}\n🔒 أوامر تحتاج رتبة أعلى من رتبتك: <b>{{count}}</b>"
HELP_USAGE_HINT = f"\n{LINE}\n{BULLET} الأوامر تنكتب بدون / ، والاستهداف: بالرد أو اليوزر أو الايدي"

# ── المالك ─────────────────────────────────────────
OWNER_PANEL = (
    "✦ <b>مركز المالك</b> 👑\n"
    f"{LINE}\n"
    f"{BULLET} المجموعات الفعالة: <b>{{active}}</b> من <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} وقت التشغيل: <b>{{uptime}}</b>\n"
    f"{BULLET} الإصدار: <code>{{version}}</code>\n"
    f"{BULLET} وضع الصيانة: {{maintenance}}\n"
    f"{BULLET} أخطاء منذ التشغيل: <b>{{errors}}</b>"
)
OWNER_ONLY = "هذا مخصص لمطور البوت بس 🔐"
MAINTENANCE_ON = f"{BULLET} تم تفعيل وضع الصيانة 🛠"
MAINTENANCE_OFF = f"{BULLET} تم إيقاف وضع الصيانة ✅"
AUDIT_HEADER = f"✦ <b>آخر العمليات</b> 📋\n{LINE}"
AUDIT_EMPTY = f"{BULLET} ماكو عمليات مسجلة لحد هسه"
GROUPS_HEADER = f"✦ <b>آخر المجموعات</b> 👥\n{LINE}"
NEW_GROUP_NOTICE = f"✦ <b>انضفت لمجموعة جديدة</b> ➕\n{LINE}\n⌯ {{title}}\n⌯ <code>{{chat_id}}</code>\n⌯ بواسطة: {{by}}"
LEFT_GROUP_NOTICE = "✦ <b>طلعت من مجموعة</b> ➖\n⌯ {title}\n⌯ <code>{chat_id}</code>"
ERROR_NOTICE = "⚠️ <b>خطأ</b>\n<code>{error}</code>\n⌯ المكان: {where}"

# ── الأزرار ────────────────────────────────────────
BTN_COMMANDS = "📜 الأوامر"
BTN_ADD = "➕ ضيفني لمجموعتك"
BTN_ABOUT = "ℹ️ عن زهو"
BTN_OWNER = "👑 مركز المالك"
BTN_BACK = "🔙 رجوع"
BTN_CLOSE = "✖️ إغلاق"
BTN_REFRESH = "🔄 تحديث"
BTN_HOME = "🏠 الرئيسية"
BTN_AUDIT = "📋 آخر العمليات"
BTN_GROUPS = "👥 المجموعات"
BTN_MAINT_ON = "🛠 تفعيل الصيانة"
BTN_MAINT_OFF = "✅ إيقاف الصيانة"
