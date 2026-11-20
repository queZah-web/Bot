"""كل نصوص زهو في مكان واحد حتى يسهل تعديلها.

شخصية زهو: بنت عراقية راقية، مهذبة، هادئة وواثقة 🤍
- الردود والكلام: لهجة عراقية خالصة + فصحى (بدون أي لهجة ثانية).
- الأوامر، أسماء الأقسام، الأزرار، والخيارات: فصحى.
- العناوين المهمة مزخرفة بالتشكيل والتطويل (مثل: تَـمَّ الـكَـتْـم).
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
    title("هلا بيك {name}", "🤍") + "\n"
    f"{LINE}\n"
    f"{BULLET} آني <b>{BOT_NAME} | {BOT_NAME_EN}</b> 🎀\n"
    f"{BULLET} أساعدكم بإدارة وحماية مجموعاتكم بكل ذوق وأمان 🛡\n"
    f"{LINE}\n"
    f"{BULLET} ضيفني لمجموعتك، وارفعني <b>مشرفة</b> بكل الصلاحيات\n"
    f"{BULLET} وبعدها اكتب <code>الاوامر</code> بالمجموعة 🌸"
)

START_GROUP = f"{BULLET} هلا بيك 🤍 آني زهو، اكتب <code>الاوامر</code> وأطلعلك كلشي مرتب ✨"

ABOUT = (
    title(f"عن {BOT_NAME}", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} الإصدار: <code>{{version}}</code>\n"
    f"{BULLET} المجموعات: <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} شغّالة من: <b>{{uptime}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} كل عملية إدارية تنحفظ بأمان، والصلاحيات مضبوطة ومرتبة 🔐"
)

ADDED_TO_GROUP = (
    title("هلا بيكم، آني زهو", "🤍") + "\n"
    f"{LINE}\n"
    f"{BULLET} فرحانة هوايه بوجودي ويا <b>{{title}}</b> 🌸\n"
    f"{BULLET} حتى أگدر أخدمكم صح، ارفعوني <b>مشرفة</b> وانطوني هاي الصلاحيات:\n"
    "    ▫️ حذف الرسائل\n"
    "    ▫️ حظر المستخدمين\n"
    "    ▫️ دعوة المستخدمين وتثبيت الرسائل\n"
    f"{LINE}\n"
    f"{BULLET} وبعدها اكتبوا <code>الاوامر</code> ✨"
)

PROMOTED_BOT = f"{BULLET} تسلمون على الثقة 🤍 هسه صرت جاهزة أخدمكم بكل صلاحياتي ✨"

ZHOO_REPLIES = (
    "عيوني، آني هنا 🤍",
    "زهو بالخدمة دايماً 🎀",
    "تفضّل، شلون أگدر أساعدك؟ 🌸",
    "حاضرة ✨",
    "موجودة، لا تشيل هم 🛡",
    "هلا بيك، أسمعك 🤍",
)

STALE = "هاي القائمة قديمة، اطلب وحدة جديدة 🌸"
NO_COMMANDS_FOR_RANK = f"{BULLET} ماكو أوامر متاحة لرتبتك بهذا القسم 🌸"
NONE_VALUE = "ماكو"

# ── الأخطاء والرفض ──────────────────────────────────
NO_PERMISSION = f"{BULLET} اعذرني، هذا الأمر يحتاج رتبة <b>{{rank}}</b> أو أعلى 🔐"
GROUP_ONLY = f"{BULLET} هذا الأمر يشتغل بالمجموعات بس 🌸"
PRIVATE_ONLY = f"{BULLET} هذا الأمر يشتغل بالخاص بس 🔒"
MAINTENANCE = f"{BULLET} زهو هسه بالصيانة 🛠 راجعتلكم قريب إن شاء الله 🤍"
ANON_ADMIN = f"{BULLET} انت مشرف مخفي 🥷 طفّي خيار «البقاء مجهولاً» حتى أعرف رتبتك"
SLOW_DOWN = "على مهلك شوية 🌸"
GENERIC_ERROR = f"{BULLET} صار خلل بسيط، ممكن تعيدها مرة ثانية؟ 🤍"

NEED_TARGET = (
    f"{BULLET} حدّدلي الشخص رجاءً: رد على رسالته، أو اكتب يوزره أو الايدي مالته 🌸\n"
    f"{BULLET} مثال: <code>{{example}}</code>"
)
TARGET_NOT_FOUND = f"{BULLET} ما لگيت هذا الشخص 🤍 تأكد من اليوزر أو الايدي"
TARGET_IS_CHANNEL = f"{BULLET} هاي رسالة قناة، مو شخص 📢"

# ── الرتب ──────────────────────────────────────────
RANK_SELF = f"{BULLET} ما يصير تغيّر رتبتك بنفسك 🌸"
RANK_BOT = f"{BULLET} البوتات ما تنرفع ولا تنزل 🤖"
RANK_PROTECTED = f"{BULLET} {{mention}} رتبته محمية ({{rank}}) وما تتغير 🛡"
RANK_TARGET_HIGHER = f"{BULLET} اعذرني، رتبة {{mention}} ({{rank}}) أعلى منك أو بقدّك 🤍"
RANK_CANT_GRANT = f"{BULLET} ما تگدر ترفع لرتبة <b>{{rank}}</b>، لازم رتبتك تكون أعلى منها 🔐"
RANK_SAME = f"{BULLET} {{mention}} هو أصلاً <b>{{rank}}</b> ✨"
RANK_BELOW_FLOOR = (
    f"{BULLET} {{mention}} مشرف بتيليجرام، فرتبته ما تنزل عن <b>{{rank}}</b>\n"
    f"{BULLET} نزّله من إشراف تيليجرام أول"
)
RANK_NOT_THAT = f"{BULLET} {{mention}} مو <b>{{rank}}</b> أصلاً 🌸"

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
    f"{BULLET} كان: {{old}} ← صار: {{rank}}\n"
    f"{BULLET} بواسطة: {{actor}}"
)

STAFF_HEADER = title("طاقم إدارة {title}", "👑") + f"\n{LINE}"
STAFF_EMPTY = f"{BULLET} ماكو أحد بهاي الرتبة هسه 🌸"
STAFF_MORE = "… و {n} غيرهم"
TG_ADMINS_LABEL = "🔰 مشرفين تيليجرام"
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
ACTIVITY = f"{BULLET} رسائل {{mention}} بالمجموعة: <b>{{count}}</b> 💌\n{BULLET} التفاعل: {{level}}"
TOP_ACTIVE_HEADER = title("الأكثر تفاعلاً", "🔥") + f"\n{LINE}"
NO_ACTIVITY = f"{BULLET} ماكو تفاعل مسجل لحد هسه 🌸"

# ── القوائم ────────────────────────────────────────
HELP_MAIN = (
    title(f"قائمة أوامر {BOT_NAME}", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} رتبتك: {{rank}}\n"
    f"{BULLET} اختار القسم اللي تريده 🌸"
)
HELP_NOT_YOURS = "هاي القائمة مو إلك 🤍 اكتب «الاوامر» حتى تطلعلك قائمتك"
HELP_SOON = (
    f"{BULLET} هذا القسم جاي بالمرحلة <b>{{phase}}</b> 🔜\n"
    f"{BULLET} الأوامر المخطط إلها:\n{{planned}}"
)
HELP_LOCKED_HINT = f"\n{LINE}\n🔒 أوامر تحتاج رتبة أعلى: <b>{{count}}</b>"
HELP_USAGE_HINT = f"\n{LINE}\n{BULLET} الأوامر تنكتب بدون / ، والاستهداف بالرد أو اليوزر أو الايدي"
HELP_DURATION_HINT = (
    f"\n{BULLET} المدة اختيارية بعد الشخص: <code>10د</code> دقايق، <code>2س</code> ساعات، "
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
WARN_AUTO_REASON = "تجاوز حد التحذيرات"

PUNISH_SELF = f"{BULLET} ما يصير تعاقب نفسك 🌸"
PUNISH_BOT_SELF = f"{BULLET} ما أگدر أعاقب نفسي 🤍"
PUNISH_PROTECTED = f"{BULLET} {{mention}} محمي ({{rank}}) وما تنطبق عليه عقوبة 🛡"
PUNISH_HIGHER = f"{BULLET} اعذرني، رتبة {{mention}} ({{rank}}) أعلى منك أو بقدّك، فما تگدر تعاقبه 🤍"
PUNISH_TG_ADMIN = f"{BULLET} {{mention}} مشرف بتيليجرام، وتيليجرام ما يسمحلي أعاقب المشرفين 🌸"
PUNISH_OTHER_BOT = f"{BULLET} {{mention}} بوت، يا ينطرد يا ينحظر بس 🤖"
BOT_NOT_ADMIN = f"{BULLET} لازم ترفعوني <b>مشرفة</b> أول حتى أگدر أسويها 🤍"
BOT_MISSING_RIGHT = f"{BULLET} أحتاج صلاحية «<b>{{right}}</b>» حتى أگدر أسويها 🔐"
RIGHT_RESTRICT = "حظر المستخدمين"
PUNISH_FAILED = f"{BULLET} ما گدرت أنفذ العقوبة 🤍 تأكد من صلاحياتي وجرب مرة ثانية"
NOT_PUNISHED = f"{BULLET} {{mention}} مو {{state}} أصلاً 🌸"
NO_WARNINGS = f"{BULLET} {{mention}} ما عليه ولا تحذير ✨"
WARNINGS_OF = f"{BULLET} تحذيرات {{mention}}: <b>{{count}}/{{limit}}</b>"
BAD_DURATION = f"{BULLET} المدة مو صحيحة 🌸 أمثلة: <code>10د</code> ، <code>2س</code> ، <code>3ي</code>"

PUNISHED_LIST_HEADER = title("{name}", "📋") + f"\n{LINE}"
PUNISHED_LIST_EMPTY = f"{BULLET} القائمة فارغة، والكل بخير 🤍"
PUNISH_LOG_HEADER = title("سجل العقوبات", "📜") + f"\n{LINE}"
PUNISH_LOG_EMPTY = f"{BULLET} ماكو عقوبات مسجلة 🌸"
PUNISH_LOG_FOOTER = "<i>🟢 فعّالة ⋅ ⚪ منتهية ⋅ الوقت UTC</i>"

WARN_SETTINGS_SET = f"{BULLET} انحفظت ✨ الحد الأقصى: <b>{{limit}}</b> تحذيرات ، والعقوبة: <b>{{action}}</b>"
WARN_SETTINGS_BAD_LIMIT = f"{BULLET} اكتب رقم بين 2 و 10 رجاءً 🌸 مثال: <code>عدد التحذيرات 3</code>"
WARN_SETTINGS_BAD_ACTION = f"{BULLET} اختار عقوبة من: <code>كتم</code> ، <code>طرد</code> ، <code>حظر</code> 🌸"

BTN_UNDO_BAN = "🕊 رفع الحظر"
BTN_UNDO_MUTE = "🔊 فك الكتم"
BTN_UNDO_RESTRICT = "✨ فك التقييد"
BTN_UNDO_WARN = "🤍 مسح التحذيرات"
UNDO_DONE = "تم التراجع ✨"
UNDO_NOT_ALLOWED = "اعذرني، رتبتك ما تسمح تتراجع عن هاي العقوبة 🔐"
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
    f"{BULLET} اضغط على أي خيار حتى تشغّله أو تطفيه ✨\n"
    f"{LINE}\n"
    "{rows}\n"
    f"{LINE}\n"
    f"{BULLET} المميزين وفوگ ما تشملهم الحماية 🤍"
)
GUARD_CUSTOM = "✏️ مخصص"
GUARD_NEED_MANAGER = "تعديل الحماية يحتاج رتبة مدير أو أعلى 🔐"
GUARD_LEVEL_SET = f"{BULLET} ضبطت مستوى الحماية على <b>{{level}}</b> ✨"
GUARD_LEVEL_BAD = f"{BULLET} اختار مستوى من: <code>خفيف</code> ، <code>متوسط</code> ، <code>صارم</code> 🌸"
GUARD_NO_DELETE_RIGHT = f"{BULLET} تنبيه: أحتاج صلاحية «<b>حذف الرسائل</b>» حتى تشتغل الحماية 🔐"

GUARD_NOTICE = f"{BULLET} {{mention}} عيني، {{what}} ممنوع هنا 🌸 <i>({{strike}}/{{max}})</i>"
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
GUARD_BOT_KICKED = f"{BULLET} طردت البوت {{bot}} 🤖 لأن إضافة البوتات تحتاج رتبة أدمن أو أعلى"

WHITELIST_ADDED = f"{BULLET} تم السماح بروابط <code>{{domain}}</code> ✨"
WHITELIST_REMOVED = f"{BULLET} تم منع روابط <code>{{domain}}</code> 🌸"
WHITELIST_BAD = f"{BULLET} اكتب النطاق صح رجاءً 🌸 مثال: <code>سماح رابط youtube.com</code>"
WHITELIST_NOT_FOUND = f"{BULLET} النطاق <code>{{domain}}</code> مو موجود بالقائمة"
WHITELIST_HEADER = title("الروابط المسموحة", "🔗") + f"\n{LINE}"
WHITELIST_EMPTY = f"{BULLET} ماكو روابط مسموحة هسه (رابط المجموعة نفسها مسموح دايماً) 🌸"
GUARD_LOG_HEADER = title("سجل الحماية", "📜") + f"\n{LINE}"
GUARD_LOG_EMPTY = f"{BULLET} ماكو مخالفات مسجلة، المجموعة هادئة 🤍"

CAPTCHA_TEXT = (
    title("هلا بيك {mention}", "🌸") + "\n"
    f"{LINE}\n"
    f"{BULLET} حتى أتأكد إنك مو روبوت، اضغط الزر الجوه 👇\n"
    f"{BULLET} عندك <b>{{minutes}} دقايق</b> 🤍"
)
CAPTCHA_BUTTON = "🤍 أنا لست روبوتاً"
CAPTCHA_NOT_YOURS = "هذا الزر مخصص للعضو الجديد بس 🌸"
CAPTCHA_DONE = "تم التحقق، هلا بيك 🤍"
CAPTCHA_EXPIRED = "هذا التحقق خلص وقته 🌸"

# ── السب ───────────────────────────────────────────
SWEAR_MODES = {
    "off": "🔓 مفتوح",
    "delete": "🗑 مسح",
    "mute": "🤐 مسح + كتم",
    "ban": "🚫 مسح + حظر",
}
SWEAR_LABEL = "🤬 السب"
SWEAR_REASON = "السب والكلام المسيء"
SWEAR_NOTICE = f"{BULLET} {{mention}} عيب عيني، هالكلام ما ينگال هنا 🤍 رسالتك انمسحت"
SWEAR_PUNISHED = (
    title("{head}", "{emoji}") + "\n"
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} السبب: السب والكلام المسيء\n"
    f"{BULLET} المدة: <b>دائمة</b>"
)
SWEAR_MODE_SET = title("تَـمَّ قَـفْـل الـسَّـب", "🤬") + f"\n{BULLET} الوضع: <b>{{mode}}</b>\n{BULLET} بواسطة: {{actor}}"
SWEAR_MODE_OFF = title("تَـمَّ فَـتْـح الـسَّـب", "🔓") + f"\n{BULLET} بواسطة: {{actor}}"
SWEAR_MODE_SAME = f"{BULLET} السب أصلاً على وضع <b>{{mode}}</b> ✨"
SWEAR_LOG_HEADER = title("الـسَّـب الـمَـحْـذُوف", "🗑") + f"\n{LINE}"
SWEAR_LOG_EMPTY = f"{BULLET} ماكو سب محذوف، المجموعة محترمة 🤍"
SWEAR_LOG_ITEM = (
    "▫️ {mention} ⋅ {action}\n"
    f"    {BULLET} الكلمة: <tg-spoiler>{{word}}</tg-spoiler>\n"
    f"    {BULLET} الرسالة: <i>{{text}}</i>\n"
    "    ⏱ <code>{when}</code>"
)
SWEAR_LOG_FOOTER = "<i>اضغط على الكلمة المخفية حتى تشوفها ⋅ الوقت UTC</i>"
SWEAR_LOG_CLEARED = f"{BULLET} انمسح سجل السب ✨"
SWEAR_ACTIONS = {"delete": "🗑 مسح", "mute": "🤐 كتم", "ban": "🚫 حظر"}
SWEAR_WORD_ADDED = f"{BULLET} انضافت <tg-spoiler>{{word}}</tg-spoiler> لقاموس السب ✨"
SWEAR_WORD_REMOVED = f"{BULLET} انشالت <tg-spoiler>{{word}}</tg-spoiler> من القاموس الخاص 🌸"
SWEAR_WORD_ALLOWED = f"{BULLET} صارت <code>{{word}}</code> مسموحة بهاي المجموعة ✨"
SWEAR_WORD_BAD = f"{BULLET} اكتب الكلمة بعد الأمر رجاءً 🌸 (من 2 لـ 40 حرف)"
SWEAR_WORD_NOT_FOUND = f"{BULLET} هاي الكلمة مو موجودة بالقاموس الخاص 🌸"
SWEAR_WORDS_HEADER = title("قاموس السب الخاص", "📖") + f"\n{LINE}"
SWEAR_WORDS_EMPTY = f"{BULLET} ماكو كلمات مضافة، القاموس الأساسي شغّال 🤍"
SWEAR_ALLOWED_LABEL = f"{BULLET} كلمات مسموحة:"
SWEAR_NEED_DELETE = f"{BULLET} تنبيه: أحتاج صلاحية «<b>حذف الرسائل</b>» حتى يشتغل قفل السب 🔐"

# ── المحادثات بخطوات ────────────────────────────────
CONV_CANCEL_HINT = f"{BULLET} للإلغاء اكتب: <code>الغاء</code>"
CONV_CANCELLED = f"{BULLET} تم الإلغاء 🌸"

# ── اختصارات الأوامر ────────────────────────────────
ALIAS_ASK_OLD = (
    f"{BULLET} تمام 🌸 اكتبلي الأمر القديم\n"
    f"{BULLET} مثلاً: <code>تقييد</code>\n" + CONV_CANCEL_HINT
)
ALIAS_NOT_COMMAND = f"{BULLET} هذا مو أمر من أوامري 🤍 اكتب اسم الأمر بالضبط، مثلاً: <code>تقييد</code>"
ALIAS_ASK_NEW = (
    f"{BULLET} حلو ✨ الأمر القديم: <b>{{old}}</b>\n"
    f"{BULLET} هسه اكتب الأمر الجديد (الاختصار)\n"
    f"{BULLET} مثلاً: <code>تق</code>"
)
ALIAS_BAD = f"{BULLET} الاختصار لازم يكون من كلمة لـ 3 كلمات، وأقل من 25 حرف 🌸 جرب مرة ثانية"
ALIAS_CONFLICT = f"{BULLET} «<b>{{alias}}</b>» هو أصلاً أمر من أوامري، اختار غيره 🌸"
ALIAS_EXISTS = f"{BULLET} الاختصار «<b>{{alias}}</b>» موجود من قبل ويشير لـ «<b>{{old}}</b>» 🌸 اختار غيره"
ALIAS_ADDED = (
    title("تَـمَّ إِضَـافَـة الأَمْـر", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} <code>{{alias}}</code> ← <code>{{old}}</code>\n"
    f"{BULLET} هسه تگدر تستخدم الاختصار، وصلاحياته نفس الأمر الأصلي ✨"
)
ALIAS_ASK_DELETE = f"{BULLET} اكتبلي الاختصار اللي تريد تحذفه 🌸\n" + CONV_CANCEL_HINT
ALIAS_DELETED = f"{BULLET} انحذف الاختصار <code>{{alias}}</code> ✨"
ALIAS_NOT_FOUND = f"{BULLET} ماكو اختصار بهذا الاسم 🌸"
ALIASES_HEADER = title("الأوامر المضافة", "⚡") + f"\n{LINE}"
ALIASES_EMPTY = f"{BULLET} ماكو أوامر مضافة لحد هسه 🌸\n{BULLET} تگدر تضيف بأمر <code>اضف امر</code>"
ALIASES_CLEARED = f"{BULLET} انمسحت كل الأوامر المضافة ✨"
ALIASES_LIMIT = f"{BULLET} وصلت للحد الأقصى ({{n}} اختصار) 🌸 احذف واحد أول"

# ── الردود ─────────────────────────────────────────
REPLY_KINDS = {False: "رد عادي 💬", True: "رد مميز ✨"}
REPLY_ASK_WORD = f"{BULLET} ارسل الكلمة اللي تريد أضيفلها رد 🌸\n" + CONV_CANCEL_HINT
REPLY_ASK_WORD_SPECIAL = (
    f"{BULLET} ارسل الكلمة للرد المميز 🌸\n"
    f"{BULLET} الرد المميز ينرسل حتى لو الكلمة جت بنص كليشة ✨\n" + CONV_CANCEL_HINT
)
REPLY_WORD_BAD = f"{BULLET} الكلمة لازم تكون نص، من كلمة لـ 5 كلمات، وأقل من 50 حرف 🌸 جرب مرة ثانية"
REPLY_WORD_IS_COMMAND = f"{BULLET} «<b>{{word}}</b>» أمر من أوامري، ما يصير يكون رد 🌸 اختار كلمة ثانية"
REPLY_EXISTS = f"{BULLET} الرد «<b>{{word}}</b>» موجود من قبل 🌸 احذفه أول إذا تريد تغيره"
REPLY_ASK_CONTENT = (
    f"{BULLET} تمام ✨ الكلمة: <b>{{word}}</b>\n"
    f"{BULLET} هسه ارسل الرد: نص، يوزر، رابط، صورة، ملصق، متحركة، فيديو، بصمة، صوت، ملف، "
    "أو رسالة محوّلة 🌸"
)
REPLY_ITEM_ADDED = (
    f"{BULLET} تم إضافة الرد ✅ باقي <b>{{left}}</b>\n"
    f"{BULLET} ارسل رد ثاني، أو ارسل <code>تم</code> حتى أحفظ\n"
    f"{BULLET} أو اكتب <code>حذف</code> حتى ينمسح الرد مباشرة وما ينحفظ"
)
REPLY_UNSUPPORTED = f"{BULLET} هذا النوع ما أگدر أحفظه 🌸 جرب نص، صورة، ملصق، فيديو أو ملف"
REPLY_NO_ITEMS = f"{BULLET} بعدك ما ارسلت ولا رد 🌸 ارسل رد، أو اكتب <code>حذف</code>"
REPLY_DISCARDED = f"{BULLET} انمسح الرد وما انحفظ 🌸"
REPLY_SAVED = (
    title("تَـمَّ حِـفْـظ الـرَّد", "🎀") + "\n"
    f"{LINE}\n"
    f"{BULLET} النوع: {{kind}}\n"
    f"{BULLET} الكلمة: <b>{{word}}</b>\n"
    f"{BULLET} عدد الردود: <b>{{count}}</b>"
)
REPLIES_HEADER = {False: title("الردود", "💬") + f"\n{LINE}", True: title("الردود المميزة", "✨") + f"\n{LINE}"}
REPLIES_EMPTY = f"{BULLET} ماكو ردود لحد هسه 🌸\n{BULLET} تگدر تضيف بأمر <code>{{cmd}}</code>"
REPLY_LINE = "▫️ <b>{word}</b> ⋅ {n} رد"
REPLIES_FOOTER = f"{LINE}\n{BULLET} العدد: <b>{{n}}</b>"
REPLY_ASK_DELETE = f"{BULLET} اختار الرد: اكتبلي اسم الرد اللي تريد تحذفه 🌸\n" + CONV_CANCEL_HINT
REPLY_DELETED = f"{BULLET} انحذف الرد <b>{{word}}</b> ✨"
REPLY_NOT_FOUND = f"{BULLET} ماكو رد بهذا الاسم 🌸 تأكد منه بأمر <code>{{cmd}}</code>"
REPLIES_CLEARED = f"{BULLET} انمسحت كل {{kind}} ✨"
REPLIES_LIMIT = f"{BULLET} وصلت للحد الأقصى ({{n}} رد) 🌸 احذف واحد أول"

# ── القفل والفتح ───────────────────────────────────
LOCK_PANEL = (
    title("الأقفال", "🔒") + "\n"
    f"{LINE}\n"
    f"{BULLET} 🔒 مقفول ⋅ 🔓 مفتوح\n"
    f"{BULLET} اضغط على أي نوع حتى تقفله أو تفتحه ✨\n"
    f"{BULLET} زر السب يتنقل بين: مفتوح ← مسح ← كتم ← حظر\n"
    f"{LINE}\n"
    f"{BULLET} المميزين وفوگ ما تشملهم الأقفال (عدا السب) 🤍"
)
LOCKED = title("تَـمَّ الـقَـفْـل", "🔒") + f"\n{BULLET} {{what}}\n{BULLET} بواسطة: {{actor}}"
UNLOCKED = title("تَـمَّ الـفَـتْـح", "🔓") + f"\n{BULLET} {{what}}\n{BULLET} بواسطة: {{actor}}"
ALL_TYPES = "✨ جميع الأنواع"
ALREADY_LOCKED = f"{BULLET} {{what}} مقفولة من قبل 🔒"
ALREADY_UNLOCKED = f"{BULLET} {{what}} مفتوحة من قبل 🔓"
LOCK_NOTICE = f"{BULLET} {{mention}} عيني، <b>{{what}}</b> مقفولة هسه بالمجموعة 🔒"
LOCK_NEED_RIGHTS = f"{BULLET} أحتاج صلاحية «<b>حذف الرسائل</b>» حتى تشتغل الأقفال 🔐"
LOCK_CHAT_NEED_RIGHTS = f"{BULLET} أحتاج صلاحية «<b>حظر المستخدمين</b>» حتى أقفل الدردشة 🔐"
LOCK_NEED_RANK = "تعديل الأقفال يحتاج رتبة أدمن أو أعلى 🔐"
REACTION_NOTICE = f"{BULLET} {{mention}} عيني، الرياكت مقفول بالمجموعة 🌸 شلت تفاعلك"
HELP_LOCK_TYPES = (
    f"\n{BULLET} الأنواع: الصور، الفيديو، المتحركات، الملصقات، البصمات، الصوتيات، الملفات، "
    "الجهات، المواقع، الاستفتاءات، الإشعارات، الرياكت، الروابط، التوجيه، الدردشة\n"
    f"{BULLET} مثال: <code>قفل الصور</code> ، <code>فتح الملصقات</code>\n"
    f"{BULLET} السب: <code>قفل السب</code> ، <code>قفل السب بالكتم</code> ، "
    "<code>قفل السب بالحظر</code> ، <code>فتح السب</code>"
)

# ── الترحيب والتوديع ───────────────────────────────
DEFAULT_WELCOME = (
    "✿ هلا وغلا {الاسم} 🌸\n"
    "─── ⋆⋅🤍⋅⋆ ───\n"
    "◈ نوّرت {المجموعة} 🤍\n"
    "◈ انت العضو رقم {العدد}\n"
    "◈ نتمنالك وقت حلو ويانه ✨"
)
DEFAULT_GOODBYE = "◈ مع السلامة {الاسم} 🤍 الله وياك، ونتمنالك كل الخير ✨"
TEMPLATE_VARS = (
    f"{BULLET} المتغيرات اللي تگدر تستخدمها:\n"
    "    <code>{الاسم}</code> اسم العضو بمنشن\n"
    "    <code>{اليوزر}</code> يوزر العضو\n"
    "    <code>{الايدي}</code> ايدي العضو\n"
    "    <code>{المجموعة}</code> اسم المجموعة\n"
    "    <code>{العدد}</code> عدد الأعضاء"
)
WELCOME_STATUS = (
    title("{kind}", "👋") + "\n"
    f"{LINE}\n"
    f"{BULLET} الحالة: {{state}}\n"
    f"{BULLET} القالب: {{custom}}\n"
    f"{LINE}\n"
    f"{BULLET} معاينة:\n\n{{preview}}"
)
STATE_ON = "مفعّل ✅"
STATE_OFF = "معطّل ▫️"
TEMPLATE_CUSTOM = "مخصص ✏️"
TEMPLATE_DEFAULT = "افتراضي 🌸"
WELCOME_SET = f"{BULLET} انحفظ قالب {{kind}} ✨ وهاي معاينته:\n\n{{preview}}"
WELCOME_RESET = f"{BULLET} رجّعت {{kind}} للقالب الافتراضي 🌸"
WELCOME_ON = f"{BULLET} تم تفعيل {{kind}} ✅"
WELCOME_OFF = f"{BULLET} تم تعطيل {{kind}} ▫️"
WELCOME_EMPTY = f"{BULLET} اكتب نص القالب بعد الأمر رجاءً 🌸\n" + "{vars}"
WELCOME_TOO_LONG = f"{BULLET} القالب كلش طويل، الحد الأقصى 1000 حرف 🌸"
BTN_RULES = "📜 القوانين"

# ── القوانين والرابط والإحصائيات ─────────────────────
RULES_TEXT = title("قوانين {title}", "📜") + f"\n{LINE}\n{{rules}}"
RULES_EMPTY = (
    f"{BULLET} هاي المجموعة بعدها ما عدها قوانين 🌸\n"
    f"{BULLET} المدير يگدر يضيفها بأمر <code>تعيين القوانين</code>"
)
RULES_NEED_TEXT = f"{BULLET} اكتب القوانين بعد الأمر رجاءً 🌸"
RULES_SET = f"{BULLET} انحفظت القوانين ✨ أي عضو يگدر يشوفها إذا كتب <code>القوانين</code>"
RULES_DELETED = f"{BULLET} انمسحت القوانين 🌸"
RULES_ALERT_MORE = "\n… اكتب «القوانين» حتى تشوفها كاملة"
LINK_TEXT = title("رابط {title}", "🔗") + f"\n{LINE}\n{{link}}"
LINK_NONE = f"{BULLET} ماكو رابط هسه، وأحتاج صلاحية «<b>دعوة المستخدمين</b>» حتى أسوي واحد 🔐"
LINK_SET = f"{BULLET} انحفظ الرابط ✨"
LINK_BAD = f"{BULLET} الرابط مو صحيح 🌸 لازم يبدأ بـ <code>https://t.me/</code>"
LINK_DELETED = f"{BULLET} انمسح الرابط المحفوظ 🌸"
STATS_TEXT = (
    title("إحصائيات {title}", "📊") + "\n"
    f"{LINE}\n"
    f"{BULLET} الأعضاء: <b>{{members}}</b>\n"
    f"{BULLET} طاقم الإدارة: <b>{{staff}}</b>\n"
    f"{BULLET} الرسائل المحسوبة: <b>{{messages}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} المحظورين: <b>{{banned}}</b> ⋅ المكتومين: <b>{{muted}}</b>\n"
    f"{BULLET} مخالفات الحماية (24 ساعة): <b>{{guard24}}</b>\n"
    f"{BULLET} السب المحذوف (24 ساعة): <b>{{swear24}}</b>\n"
    f"{BULLET} المستوى: {{level}} ⋅ الأقفال الفعالة: <b>{{locks}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} الأكثر تفاعلاً:\n{{top}}"
)

# ── لوحة الإعدادات ─────────────────────────────────
SETTINGS_PANEL = (
    title("إعدادات {title}", "⚙️") + "\n"
    f"{LINE}\n"
    f"{BULLET} اضغط على أي خيار حتى تعدّله ✨\n"
    f"{BULLET} التحذيرات: الحد <b>{{limit}}</b> ⋅ العقوبة <b>{{action}}</b>\n"
    f"{BULLET} الحماية: {{level}} ⋅ الأقفال الفعالة: <b>{{locks}}</b>\n"
    f"{BULLET} السب: <b>{{swear}}</b>"
)
SETTINGS_NEED_MANAGER = "تعديل الإعدادات يحتاج رتبة مدير أو أعلى 🔐"
BTN_WELCOME = "👋 الترحيب"
BTN_GOODBYE = "🌙 التوديع"
BTN_LOCKS = "🔒 الأقفال"
BTN_PROTECT = "🛡 الحماية"
BTN_WARN_LIMIT = "⚠️ حد التحذيرات: {n}"
BTN_WARN_ACTION = "⚖️ العقوبة: {a}"
BTN_LOCK_ALL = "🔒 قفل الكل"
BTN_UNLOCK_ALL = "🔓 فتح الكل"

# ── المالك ─────────────────────────────────────────
OWNER_PANEL = (
    title("مركز المالك", "👑") + "\n"
    f"{LINE}\n"
    f"{BULLET} المجموعات الفعّالة: <b>{{active}}</b> من <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} وقت التشغيل: <b>{{uptime}}</b>\n"
    f"{BULLET} الإصدار: <code>{{version}}</code>\n"
    f"{BULLET} وضع الصيانة: {{maintenance}}\n"
    f"{BULLET} الأخطاء من التشغيل: <b>{{errors}}</b>"
)
MAINT_STATE_ON = "مفعّل 🛠"
MAINT_STATE_OFF = "مطفي ✅"
OWNER_ONLY = "هذا القسم بس لمطور زهو 🔐"
MAINTENANCE_ON = f"{BULLET} تفعّل وضع الصيانة 🛠"
MAINTENANCE_OFF = f"{BULLET} انطفى وضع الصيانة، ورجعنا نشتغل ✨"
AUDIT_HEADER = title("آخر العمليات", "📋") + f"\n{LINE}"
AUDIT_EMPTY = f"{BULLET} ماكو عمليات مسجلة لحد هسه 🌸"
AUDIT_FOOTER = "<i>الوقت بتوقيت UTC</i>"
GROUPS_HEADER = title("آخر المجموعات", "🌸") + f"\n{LINE}"
GROUPS_EMPTY = f"{BULLET} ماكو مجموعات لحد هسه"
NO_TITLE = "بدون اسم"
NEW_GROUP_NOTICE = title("انضفت لمجموعة جديدة", "🎀") + f"\n{LINE}\n{BULLET} {{title}}\n{BULLET} <code>{{chat_id}}</code>\n{BULLET} بواسطة: {{by}}"
LEFT_GROUP_NOTICE = title("طلعت من مجموعة", "🤍") + f"\n{BULLET} {{title}}\n{BULLET} <code>{{chat_id}}</code>"
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
