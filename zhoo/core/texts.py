"""كل نصوص زهو في مكان واحد حتى يسهل تعديلها.

شخصية زهو: بنت راقية، مهذبة، هادئة وواثقة 🤍
- كلام مرتب ومحترم، بلهجة عراقية ناعمة وخفيفة.
- العناوين المهمة مزخرفة بالتشكيل والتطويل (مثل: تَـمَّ الكَـتْـم).
- أسماء الأوامر والأقسام بالفصحى.
"""
from __future__ import annotations

LINE = "─── ⋆⋅🤍⋅⋆ ───"
BULLET = "◈"
FLOWER = "✿"

BOT_NAME = "زَهـو"
BOT_NAME_EN = "ZHOO"


def title(text: str, emoji: str = "") -> str:
    """عنوان مزخرف موحد لكل الرسائل."""
    return f"{FLOWER} <b>{text}</b> {emoji}".rstrip()


# ── عام ───────────────────────────────────────────
START_PRIVATE = (
    title("أهلاً وسهلاً {name}", "🤍") + "\n"
    f"{LINE}\n"
    f"{BULLET} أنا <b>{BOT_NAME} | {BOT_NAME_EN}</b> 🎀\n"
    f"{BULLET} مُساعِدتكم لإدارة وحِمايَة المجموعات بكل أناقة وأمان 🛡\n"
    f"{LINE}\n"
    f"{BULLET} أضفني لمجموعتك، وارفعني <b>مشرفة</b> بكامل الصلاحيات\n"
    f"{BULLET} وبعدها اكتب <code>الاوامر</code> داخل المجموعة 🌸"
)

START_GROUP = f"{BULLET} أهلاً بك 🤍 أنا زهو، اكتب <code>الاوامر</code> وراح أعرض لك كل شي بترتيب ✨"

ABOUT = (
    title(f"عن {BOT_NAME}", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} الإصدار: <code>{{version}}</code>\n"
    f"{BULLET} المجموعات: <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} أعمل منذ: <b>{{uptime}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} كل عملية إدارية تُسجَّل بأمان، والصلاحيات دقيقة ومنظمة 🔐"
)

ADDED_TO_GROUP = (
    title("أهلاً بكم، أنا زهو", "🤍") + "\n"
    f"{LINE}\n"
    f"{BULLET} سعيدة جداً بانضمامي إلى <b>{{title}}</b> 🌸\n"
    f"{BULLET} حتى أقدر أخدمكم صح، ارفعوني <b>مشرفة</b> مع صلاحيات:\n"
    "    ▫️ حذف الرسائل\n"
    "    ▫️ حظر المستخدمين\n"
    "    ▫️ دعوة المستخدمين وتثبيت الرسائل\n"
    f"{LINE}\n"
    f"{BULLET} بعدها اكتبوا <code>الاوامر</code> ✨"
)

PROMOTED_BOT = f"{BULLET} شكراً على الثقة 🤍 صرت جاهزة أخدمكم بكامل صلاحياتي ✨"

ZHOO_REPLIES = (
    "نعم؟ أنا هنا 🤍",
    "زهو بالخدمة دائماً 🎀",
    "تفضّل، شلون أقدر أساعدك؟ 🌸",
    "حاضرة ✨",
    "موجودة، اطمئن 🛡",
    "يا هلا، أسمعك 🤍",
)

# ── الأخطاء والرفض ──────────────────────────────────
NO_PERMISSION = f"{BULLET} عذراً، هذا الأمر يحتاج رتبة <b>{{rank}}</b> أو أعلى 🔐"
GROUP_ONLY = f"{BULLET} هذا الأمر يعمل داخل المجموعات فقط 🌸"
PRIVATE_ONLY = f"{BULLET} هذا الأمر يعمل في الخاص فقط 🔒"
MAINTENANCE = f"{BULLET} زهو حالياً في وضع الصيانة 🛠 أرجع لكم قريباً إن شاء الله 🤍"
ANON_ADMIN = f"{BULLET} حضرتك مشرف مخفي 🥷 أوقف خيار «البقاء مجهولاً» حتى أتعرف على رتبتك"
SLOW_DOWN = "على مهلك شوي 🌸"
GENERIC_ERROR = f"{BULLET} صار خلل بسيط، ممكن تعيد المحاولة؟ 🤍"

NEED_TARGET = (
    f"{BULLET} حدّد الشخص من فضلك: بالرد على رسالته، أو بكتابة يوزره أو الايدي 🌸\n"
    f"{BULLET} مثال: <code>{{example}}</code>"
)
TARGET_NOT_FOUND = f"{BULLET} ما لقيت هذا الشخص 🤍 تأكد من اليوزر أو الايدي"
TARGET_IS_CHANNEL = f"{BULLET} هذه رسالة قناة وليست شخصاً 📢"

# ── الرتب ──────────────────────────────────────────
RANK_SELF = f"{BULLET} ما يصير تغيّر رتبتك بنفسك 🌸"
RANK_BOT = f"{BULLET} البوتات ما تُرفع ولا تُنزَّل 🤖"
RANK_PROTECTED = f"{BULLET} {{mention}} رتبته محمية ({{rank}}) ولا يمكن تغييرها 🛡"
RANK_TARGET_HIGHER = f"{BULLET} عذراً، رتبة {{mention}} ({{rank}}) أعلى منك أو تساويك 🤍"
RANK_CANT_GRANT = f"{BULLET} ما تقدر ترفع لرتبة <b>{{rank}}</b>، لازم تكون رتبتك أعلى منها 🔐"
RANK_SAME = f"{BULLET} {{mention}} رتبته <b>{{rank}}</b> من قبل ✨"
RANK_BELOW_FLOOR = (
    f"{BULLET} {{mention}} مشرف في تيليجرام، فرتبته لا تنزل عن <b>{{rank}}</b>\n"
    f"{BULLET} يمكنك إزالة إشرافه من إعدادات تيليجرام أولاً"
)
RANK_NOT_THAT = f"{BULLET} {{mention}} ليس <b>{{rank}}</b> أصلاً 🌸"

RANK_PROMOTED = (
    title("تَـمَّ الـرَّفْـع بِـنَـجَـاح", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    f"{BULLET} بواسطة: {{actor}}"
)
RANK_DEMOTED = (
    title("تَـمَّ الـتَّـنْـزِيـل بِـنَـجَـاح", "🤍") + "\n"
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} كان: {{old}} ← أصبح: {{rank}}\n"
    f"{BULLET} بواسطة: {{actor}}"
)

STAFF_HEADER = title("طاقم إدارة {title}", "👑") + f"\n{LINE}"
STAFF_EMPTY = f"{BULLET} لا يوجد أحد بهذه الرتبة حالياً 🌸"
RANK_LIST_HEADER = title("{plural}", "✨") + f"\n{LINE}"

# ── معلومات ────────────────────────────────────────
ID_TEXT = (
    title("معلومات {name}", "🌸") + "\n"
    f"{LINE}\n"
    f"{BULLET} الايدي: <code>{{user_id}}</code>\n"
    f"{BULLET} اليوزر: {{username}}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    "{extra}"
)
MY_RANK = f"{BULLET} رتبتك هنا: {{rank}} 🤍"
THEIR_RANK = f"{BULLET} رتبة {{mention}}: {{rank}}"
ACTIVITY = f"{BULLET} رسائل {{mention}} في المجموعة: <b>{{count}}</b> 💌\n{BULLET} التفاعل: {{level}}"
TOP_ACTIVE_HEADER = title("الأكثر تفاعلاً", "🔥") + f"\n{LINE}"
NO_ACTIVITY = f"{BULLET} لا يوجد تفاعل مسجل حتى الآن 🌸"

# ── القوائم ────────────────────────────────────────
HELP_MAIN = (
    title(f"قائمة أوامر {BOT_NAME}", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} رتبتك: {{rank}}\n"
    f"{BULLET} اختر القسم الذي تريده 🌸"
)
HELP_NOT_YOURS = "هذه القائمة ليست لك 🤍 اكتب «الاوامر» لتظهر لك قائمتك الخاصة"
HELP_SOON = (
    f"{BULLET} هذا القسم قادم في المرحلة <b>{{phase}}</b> 🔜\n"
    f"{BULLET} الأوامر المخطط لها:\n{{planned}}"
)
HELP_LOCKED_HINT = f"\n{LINE}\n🔒 أوامر تحتاج رتبة أعلى: <b>{{count}}</b>"
HELP_USAGE_HINT = f"\n{LINE}\n{BULLET} تُكتب الأوامر بدون / ، والاستهداف بالرد أو اليوزر أو الايدي"
HELP_DURATION_HINT = (
    f"\n{BULLET} المدة اختيارية بعد الشخص: <code>10د</code> دقائق، <code>2س</code> ساعات، "
    f"<code>3ي</code> أيام، <code>1ا</code> أسابيع\n"
    f"{BULLET} مثال: <code>كتم @user 30د سبام</code>"
)

# ── العقوبات ───────────────────────────────────────
PUNISH_TITLES = {
    "ban": ("تَـمَّ الـحَـظْـر", "🚫"),
    "kick": ("تَـمَّ الـطَّـرْد", "👋"),
    "mute": ("تَـمَّ الـكَـتْـم", "🔇"),
    "restrict": ("تَـمَّ الـتَّـقْـيِـيـد", "⛓"),
    "warn": ("تَـمَّ الـتَّـحْـذِيـر", "⚠️"),
    "unban": ("تَـمَّ رَفْـعُ الـحَـظْـر", "🕊"),
    "unmute": ("تَـمَّ فَـكُّ الـكَـتْـم", "🔊"),
    "unrestrict": ("تَـمَّ فَـكُّ الـتَّـقْـيِـيـد", "✨"),
    "unwarn": ("تَـمَّ مَـسْـحُ الـتَّـحْـذِيـرَات", "🤍"),
}
PUNISH_BODY = (
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    "{extra}"
    f"{BULLET} بواسطة: {{actor}}"
)
PUNISH_DURATION = f"{BULLET} المدة: <b>{{duration}}</b>\n"
PUNISH_FOREVER = f"{BULLET} المدة: <b>دائمة</b>\n"
PUNISH_REASON = f"{BULLET} السبب: <i>{{reason}}</i>\n"
WARN_COUNT = f"{BULLET} التحذيرات: <b>{{count}}/{{limit}}</b>\n"
WARN_LIMIT_REACHED = (
    "\n" + title("وصل للحد الأقصى من التحذيرات", "⛔") + "\n"
    f"{BULLET} العقوبة التلقائية: <b>{{action}}</b>"
)

PUNISH_SELF = f"{BULLET} ما يصير تعاقب نفسك 🌸"
PUNISH_BOT_SELF = f"{BULLET} ما أقدر أعاقب نفسي 🤍"
PUNISH_PROTECTED = f"{BULLET} {{mention}} محمي ({{rank}}) ولا يمكن معاقبته 🛡"
PUNISH_HIGHER = f"{BULLET} عذراً، رتبة {{mention}} ({{rank}}) أعلى منك أو تساويك، فلا يمكنك معاقبته 🤍"
PUNISH_TG_ADMIN = f"{BULLET} {{mention}} مشرف في تيليجرام، وتيليجرام لا يسمح لي بمعاقبة المشرفين 🌸"
PUNISH_OTHER_BOT = f"{BULLET} {{mention}} بوت، يمكن طرده أو حظره فقط 🤖"
BOT_NOT_ADMIN = f"{BULLET} لازم ترفعوني <b>مشرفة</b> أولاً حتى أقدر أنفذ هذا 🤍"
BOT_MISSING_RIGHT = f"{BULLET} أحتاج صلاحية «<b>{{right}}</b>» حتى أقدر أنفذ هذا 🔐"
PUNISH_FAILED = f"{BULLET} ما قدرت أنفذ العقوبة 🤍 تأكد من صلاحياتي وجرب مرة ثانية"
NOT_PUNISHED = f"{BULLET} {{mention}} غير {{state}} أصلاً 🌸"
NO_WARNINGS = f"{BULLET} {{mention}} ليس عليه أي تحذير ✨"
WARNINGS_OF = f"{BULLET} تحذيرات {{mention}}: <b>{{count}}/{{limit}}</b>"
BAD_DURATION = f"{BULLET} المدة غير صحيحة 🌸 أمثلة: <code>10د</code> ، <code>2س</code> ، <code>3ي</code>"

PUNISHED_LIST_HEADER = title("{name}", "📋") + f"\n{LINE}"
PUNISHED_LIST_EMPTY = f"{BULLET} القائمة فارغة، الجميع بخير 🤍"
PUNISH_LOG_HEADER = title("سجل العقوبات", "📜") + f"\n{LINE}"
PUNISH_LOG_EMPTY = f"{BULLET} لا توجد عقوبات مسجلة 🌸"

WARN_SETTINGS_SET = f"{BULLET} تم الحفظ ✨ الحد الأقصى: <b>{{limit}}</b> تحذيرات ، والعقوبة: <b>{{action}}</b>"
WARN_SETTINGS_BAD_LIMIT = f"{BULLET} اكتب رقماً بين 2 و 10 من فضلك 🌸 مثال: <code>عدد التحذيرات 3</code>"
WARN_SETTINGS_BAD_ACTION = f"{BULLET} اختر عقوبة من: <code>كتم</code> ، <code>طرد</code> ، <code>حظر</code> 🌸"

BTN_UNDO_BAN = "🕊 رفع الحظر"
BTN_UNDO_MUTE = "🔊 فك الكتم"
BTN_UNDO_RESTRICT = "✨ فك التقييد"
BTN_UNDO_WARN = "🤍 مسح التحذيرات"
UNDO_DONE = "تم التراجع بنجاح ✨"
UNDO_NOT_ALLOWED = "عذراً، رتبتك لا تسمح بالتراجع عن هذه العقوبة 🔐"
UNDO_FOOTER = f"\n{LINE}\n{BULLET} تراجع بواسطة: {{actor}} ✨"

# ── الحماية ────────────────────────────────────────
GUARD_LABELS = {
    "flood": ("مكافحة الإغراق", "🌊", "إرسال رسائل كثيرة بسرعة"),
    "repeat": ("الرسائل المكررة", "🔁", "تكرار نفس الرسالة"),
    "links": ("الروابط", "🔗", "إرسال روابط غير مسموحة"),
    "forward": ("التوجيه", "↪️", "توجيه رسائل من قنوات أو أشخاص"),
    "mentions": ("المنشن الجماعي", "📣", "منشن لعدد كبير من الأعضاء"),
    "bots": ("البوتات الدخيلة", "🤖", "إضافة بوت بدون صلاحية"),
    "captcha": ("تحقق الأعضاء الجدد", "🧩", "التحقق من العضو الجديد"),
}
GUARD_LEVELS = {"light": "🌿 خفيف", "medium": "⚖️ متوسط", "strict": "🔥 صارم"}

GUARD_PANEL = (
    title("إعدادات الحماية", "🛡") + "\n"
    f"{LINE}\n"
    f"{BULLET} المستوى الحالي: <b>{{level}}</b>\n"
    f"{BULLET} اضغط على أي خيار لتفعيله أو إيقافه ✨\n"
    f"{LINE}\n"
    "{rows}\n"
    f"{LINE}\n"
    f"{BULLET} المميزون فما فوق مُستثنَون من الحماية 🤍"
)
GUARD_CUSTOM = "✏️ مخصص"
GUARD_NEED_MANAGER = "تعديل الحماية يحتاج رتبة مدير أو أعلى 🔐"
GUARD_LEVEL_SET = f"{BULLET} تم ضبط مستوى الحماية على <b>{{level}}</b> ✨"
GUARD_LEVEL_BAD = f"{BULLET} اختر مستوى من: <code>خفيف</code> ، <code>متوسط</code> ، <code>صارم</code> 🌸"
GUARD_NO_DELETE_RIGHT = f"{BULLET} تنبيه: أحتاج صلاحية «<b>حذف الرسائل</b>» حتى تعمل الحماية 🔐"

GUARD_NOTICE = f"{BULLET} {{mention}} عذراً، {{what}} غير مسموح هنا 🌸 <i>({{strike}}/{{max}})</i>"
GUARD_MUTED = (
    title("تَـمَّ الـكَـتْـم تِـلْـقَـائِـيًّـا", "🛡") + "\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} السبب: {{why}}\n"
    f"{BULLET} المدة: <b>{{duration}}</b>"
)
GUARD_WHY = {
    "flood": "الإغراق بالرسائل",
    "repeat": "تكرار نفس الرسالة",
    "links": "إرسال الروابط",
    "forward": "التوجيه",
    "mentions": "المنشن الجماعي",
}
GUARD_WHAT = {
    "repeat": "تكرار نفس الرسالة",
    "links": "إرسال الروابط",
    "forward": "التوجيه",
    "mentions": "المنشن الجماعي",
}
GUARD_BOT_KICKED = f"{BULLET} تم طرد البوت {{bot}} 🤖 لأن إضافة البوتات تحتاج رتبة أدمن أو أعلى"

WHITELIST_ADDED = f"{BULLET} تم السماح بروابط <code>{{domain}}</code> ✨"
WHITELIST_REMOVED = f"{BULLET} تم منع روابط <code>{{domain}}</code> 🌸"
WHITELIST_BAD = f"{BULLET} اكتب النطاق بشكل صحيح من فضلك 🌸 مثال: <code>سماح رابط youtube.com</code>"
WHITELIST_NOT_FOUND = f"{BULLET} النطاق <code>{{domain}}</code> غير موجود بالقائمة"
WHITELIST_HEADER = title("الروابط المسموحة", "🔗") + f"\n{LINE}"
WHITELIST_EMPTY = f"{BULLET} لا توجد روابط مسموحة حالياً (رابط المجموعة نفسها مسموح دائماً) 🌸"
GUARD_LOG_HEADER = title("سجل الحماية", "📜") + f"\n{LINE}"
GUARD_LOG_EMPTY = f"{BULLET} لا توجد مخالفات مسجلة، المجموعة هادئة 🤍"

CAPTCHA_TEXT = (
    title("أهلاً بك {mention}", "🌸") + "\n"
    f"{LINE}\n"
    f"{BULLET} للتأكد أنك لست روبوتاً، اضغط الزر بالأسفل\n"
    f"{BULLET} لديك <b>{{minutes}} دقائق</b> 🤍"
)
CAPTCHA_BUTTON = "🤍 أنا لست روبوتاً"
CAPTCHA_NOT_YOURS = "هذا الزر مخصص للعضو الجديد فقط 🌸"
CAPTCHA_DONE = "تم التحقق بنجاح، أهلاً بك 🤍"
CAPTCHA_EXPIRED = "انتهت صلاحية هذا التحقق 🌸"

# ── المالك ─────────────────────────────────────────
OWNER_PANEL = (
    title("مركز المالك", "👑") + "\n"
    f"{LINE}\n"
    f"{BULLET} المجموعات الفعّالة: <b>{{active}}</b> من <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} وقت التشغيل: <b>{{uptime}}</b>\n"
    f"{BULLET} الإصدار: <code>{{version}}</code>\n"
    f"{BULLET} وضع الصيانة: {{maintenance}}\n"
    f"{BULLET} الأخطاء منذ التشغيل: <b>{{errors}}</b>"
)
OWNER_ONLY = "هذا القسم خاص بمطور زهو فقط 🔐"
MAINTENANCE_ON = f"{BULLET} تم تفعيل وضع الصيانة 🛠"
MAINTENANCE_OFF = f"{BULLET} تم إيقاف وضع الصيانة، عدنا للعمل ✨"
AUDIT_HEADER = title("آخر العمليات", "📋") + f"\n{LINE}"
AUDIT_EMPTY = f"{BULLET} لا توجد عمليات مسجلة حتى الآن 🌸"
GROUPS_HEADER = title("آخر المجموعات", "🌸") + f"\n{LINE}"
GROUPS_EMPTY = f"{BULLET} لا توجد مجموعات حتى الآن"
NEW_GROUP_NOTICE = title("انضممت لمجموعة جديدة", "🎀") + f"\n{LINE}\n{BULLET} {{title}}\n{BULLET} <code>{{chat_id}}</code>\n{BULLET} بواسطة: {{by}}"
LEFT_GROUP_NOTICE = title("غادرت مجموعة", "🤍") + f"\n{BULLET} {{title}}\n{BULLET} <code>{{chat_id}}</code>"
ERROR_NOTICE = "⚠️ <b>خطأ</b>\n<code>{error}</code>\n" + f"{BULLET} المكان: {{where}}"

# ── الأزرار ────────────────────────────────────────
BTN_COMMANDS = "📜 الأوامر"
BTN_ADD = "🎀 أضفني لمجموعتك"
BTN_ABOUT = "🤍 عن زهو"
BTN_OWNER = "👑 مركز المالك"
BTN_BACK = "↩️ رجوع"
BTN_CLOSE = "✖️ إغلاق"
BTN_REFRESH = "🔄 تحديث"
BTN_HOME = "🏠 الرئيسية"
BTN_AUDIT = "📋 آخر العمليات"
BTN_GROUPS = "🌸 المجموعات"
BTN_MAINT_ON = "🛠 تفعيل الصيانة"
BTN_MAINT_OFF = "✅ إيقاف الصيانة"
