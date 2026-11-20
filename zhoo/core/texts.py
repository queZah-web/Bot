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
    "تفضّل {name}، شلون أگدر أساعدك؟ 🌸",
    "حاضرة ✨",
    "موجودة، لا تشيل هم 🛡",
    "هلا بيك، أسمعك 🤍",
    "نعم {name}؟ گول عيني 🌷",
    "نعم عيني، شتحتاج؟ 🤍",
    "هنا، ما أطلع من المجموعة أبداً 🛡",
    "يا هلا {name}، آمرني 🎀",
    "حاضرة ومنتبهة، تفضّل ✨",
    "زهو وياك، اكتب «الاوامر» إذا تريد تشوف كلشي 🌸",
    "عيون زهو، شنو تريد؟ 🤍",
    "موجودة {name} 🌙 گلبي وعيني على المجموعة",
    "هلا والله، صوتك وصل 🌷",
    "نعم نعم، آني هنا وأسمعك 🎀",
    "تدلل {name}، شنو أسويلك؟ ✨",
    "أمرك، بس گول 🤍",
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
TOP_ACTIVE = (
    title("الـمُـتَـفَـاعِـلِـيـن", "🔥") + f"\n{LINE}\n"
    "🏡 <b>{title}</b>\n"
    "💬 مجموع الرسائل: <b>{total}</b> ⋅ 👥 المتفاعلين: <b>{members}</b>\n"
    f"{LINE}\n"
    "{items}\n"
    f"{LINE}\n"
    "{me}"
)
TOP_MEDALS = ("🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")
TOP_ACTIVE_ITEM = "{medal} {mention}\n      {bar} <b>{count}</b> رسالة ⋅ {pct}%"
TOP_ACTIVE_ME = "📍 ترتيبك: <b>#{pos}</b> ⋅ رسائلك: <b>{count}</b> ⋅ {level}"
TOP_ACTIVE_ME_NONE = "📍 بعدك ما كتبت، سولف ويانا حتى تدخل الترتيب 🌸"
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
    "lock": "مخالفة الأقفال",
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
    "smart": "🧠 تدريجي ذكي",
    "delete": "🗑 مسح",
    "mute": "🤐 مسح + كتم",
    "ban": "🚫 مسح + حظر",
}
SWEAR_LEVELS = {1: "🟢 إهانة (خفيف)", 2: "🟠 مسبة (متوسط)", 3: "🔴 فشار +18 (شديد)"}
# خيارات أمر الإضافة
SWEAR_LEVEL_WORDS = {"خفيف": 1, "اهانه": 1, "متوسط": 2, "مسبه": 2, "شديد": 3, "فشار": 3}
# نوعين قفل مستقلين: الفشار (+18 والمسبات) والإهانات
SWEAR_SCOPES = {"all": "🤬 السب بنوعيه", "vulgar": "🔞 الفشار +18", "insult": "🙊 الإهانات"}
SWEAR_SCOPE_COVERS = {
    "all": "الفشار +18 والمسبات + الإهانات",
    "vulgar": "الكلام البذيء والجنسي، والمسبات واللعن، والتجاوز على الدين والعرض",
    "insult": "الإهانات والتحقير والتنابز بالألقاب (للذكر والأنثى)",
}
# كلمات اختيارية بعد «قفل السب»: 18 ← الفشار بس
SWEAR_SCOPE_WORDS = {"18": "vulgar", "+18": "vulgar", "18+": "vulgar"}
SWEAR_MODE_WORDS = {"تدريجي": "smart", "التدريجي": "smart", "بالتدريج": "smart",
                    "بالمسح": "delete", "بالكتم": "mute", "بالحظر": "ban"}
SWEAR_GLOBAL_WORD = "عام"
SWEAR_PLANS = {
    "gradual": "📈 تدريجي",
    "mute": "🤐 كتم متصاعد",
    "ban": "🚫 حظر متصاعد",
    "delete": "🗑 مسح فقط",
    "off": "💤 تجاهل",
}
SWEAR_PLAN_HINTS = {
    "gradual": "تحذير ← تحذير ← كتم ساعة ← كتم يوم ← حظر يوم ← حظر دائم",
    "mute": "كتم ساعة ← يوم ← أسبوع ← دائم",
    "ban": "حظر يوم ← أسبوع ← دائم",
    "delete": "مسح الرسالة بس",
    "off": "ما يسوي شي لهاي الفئة",
}
SWEAR_SOURCES = {"base": "القاموس الأساسي", "global": "القاموس العام", "group": "قاموس المجموعة"}
SWEAR_KINDS = {"exact": "كلمة كاملة", "stem": "كلمة وتصريفاتها", "phrase": "عبارة", "reply": "رد بإهانة"}
# من أحد يغلط على زهو نفسها
ZHOO_INSULTED = (
    f"{BULLET} {{mention}} آني أحترم الكل، وأستاهل نفس الاحترام 🌸",
    f"{BULLET} {{mention}} الكلام الحلو يطلع من ناس حلوين، وانت منهم إن شاء الله 🤍",
    f"{BULLET} {{mention}} عيب عيني، زهو حارسة المجموعة مو مكان للغلط 🛡",
    f"{BULLET} {{mention}} سامحتك هالمرة، بس الأدب زينة 🎀",
    f"{BULLET} {{mention}} آني هنا أخدمكم، والاحترام يبقى بينا 🤍",
)
SWEAR_PERMANENT = "دائم"
SWEAR_STEP_DELETE = "مسح"
SWEAR_STEP_WARN = "تحذير"
SWEAR_LABEL = "🤬 السب"
SWEAR_BTN_SCOPE = {"vulgar": "🔞 الفشار: {mode}", "insult": "🙊 الإهانات: {mode}"}
SWEAR_SUMMARY = "🔞 {vulgar} ⋅ 🙊 {insult}"
SWEAR_REASON = "السب والكلام المسيء"
SWEAR_NOTICE = f"{BULLET} {{mention}} عيب عيني، هالكلام ما ينگال هنا 🤍 رسالتك انمسحت"
SWEAR_WARNED = (
    title("تَـحْـذِيـر", "⚠️") + "\n"
    f"{BULLET} {{mention}} رسالتك انمسحت لأن بيها كلام مسيء 🤍\n"
    f"{BULLET} هذا التحذير رقم <b>{{n}}</b>\n"
    f"{BULLET} المرة الجاية: <b>{{next}}</b>"
)
SWEAR_PUNISHED = (
    title("{head}", "{emoji}") + "\n"
    f"{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} السبب: السب والكلام المسيء ({{level}})\n"
    f"{BULLET} المخالفة رقم: <b>{{n}}</b>\n"
    f"{BULLET} المدة: <b>{{duration}}</b>"
)
SWEAR_LOCK_TITLES = {
    "all": title("تَـمَّ قَـفْـل الـسَّـب", "🤬"),
    "vulgar": title("تَـمَّ قَـفْـل الـفُـشَـار +18", "🔞"),
    "insult": title("تَـمَّ قَـفْـل الإِهَـانَـات", "🙊"),
}
SWEAR_UNLOCK_TITLES = {
    "all": title("تَـمَّ فَـتْـح الـسَّـب", "🔓"),
    "vulgar": title("تَـمَّ فَـتْـح الـفُـشَـار", "🔓"),
    "insult": title("تَـمَّ فَـتْـح الإِهَـانَـات", "🔓"),
}
SWEAR_MODE_SET = (
    "{head}\n"
    f"{BULLET} يشمل: {{covers}}\n"
    f"{BULLET} الوضع: <b>{{mode}}</b>\n"
    f"{BULLET} بواسطة: {{actor}}"
)
SWEAR_OTHER_STATE = f"{BULLET} {{scope}}: <b>{{mode}}</b>"
SWEAR_MODE_SMART_HINT = f"{BULLET} العقوبة حسب شدة الكلام وعدد المخالفات ⋅ تتغير من: <code>عقوبات السب</code>"
SWEAR_MODE_OFF = "{head}\n" + f"{BULLET} بواسطة: {{actor}}"
SWEAR_MODE_SAME = f"{BULLET} {{scope}} أصلاً على وضع <b>{{mode}}</b> ✨"
SWEAR_LOG_HEADER = title("مُـخَـالَـفَـات الـسَّـب", "🗑") + f"\n{LINE}"
SWEAR_LOG_EMPTY = f"{BULLET} ماكو مخالفات، المجموعة محترمة 🤍"
SWEAR_LOG_STRIKES = f"{BULLET} مخالفات {{mention}} آخر 7 أيام: <b>{{n}}</b>"
SWEAR_LOG_ITEM = (
    "▫️ {mention} ⋅ {action} ⋅ {level}\n"
    f"    {BULLET} الكلمة: <tg-spoiler>{{word}}</tg-spoiler>\n"
    f"    {BULLET} الرسالة: <i>{{text}}</i>\n"
    "    ⏱ <code>{when}</code>"
)
SWEAR_LOG_FOOTER = "<i>اضغط على الكلمة المخفية حتى تشوفها ⋅ الوقت UTC</i>"
SWEAR_LOG_CLEARED = f"{BULLET} انمسح سجل السب ✨"
SWEAR_LOG_USER_CLEARED = f"{BULLET} انمسحت مخالفات {{mention}} ورجعت صفحته بيضة 🤍"
SWEAR_ACTIONS = {"delete": "🗑 مسح", "warn": "⚠️ تحذير", "mute": "🤐 كتم", "ban": "🚫 حظر"}
SWEAR_WORD_ADDED = (
    f"{BULLET} انضافت <tg-spoiler>{{word}}</tg-spoiler> لقاموس {{where}} ✨\n"
    f"{BULLET} الفئة: <b>{{level}}</b> ⋅ النوع: {{kind}}"
)
SWEAR_WHERE_GROUP = "المجموعة"
SWEAR_WHERE_GLOBAL = "العام 🌍 (كل المجموعات)"
SWEAR_WORD_REMOVED = f"{BULLET} انشالت <tg-spoiler>{{word}}</tg-spoiler> من القاموس ✨"
SWEAR_WORD_ALLOWED = f"{BULLET} صارت <tg-spoiler>{{word}}</tg-spoiler> مسموحة بهاي المجموعة ✨"
SWEAR_WORD_NOT_SWEAR = f"{BULLET} هاي الكلمة أصلاً مو سب، ما تحتاج سماح 🌸"
SWEAR_UNALLOWED = f"{BULLET} رجعت <tg-spoiler>{{word}}</tg-spoiler> محظورة مثل قبل ✨"
SWEAR_ALLOW_NOT_FOUND = f"{BULLET} هاي الكلمة مو موجودة بالكلمات المسموحة 🌸"
SWEAR_WORD_BAD = (
    f"{BULLET} اكتب الكلمة أو العبارة بعد الأمر رجاءً 🌸 (من 2 لـ 60 حرف، وأكثر شي 6 كلمات)\n"
    f"{BULLET} مثال: <code>اضافة سب شديد الكلمة</code> ⋅ الفئات: خفيف، متوسط، شديد"
)
SWEAR_WORD_COLLIDES = (
    f"{BULLET} ما ضفتها 🌸 لأن راح تحظر كلام سليم مثل: {{words}}\n"
    f"{BULLET} إذا هي إهانة، ضيفها كعبارة كاملة (مثل: <code>اضافة سب يا ...</code>)"
)
SWEAR_WORD_IN_BASE = f"{BULLET} هاي الكلمة أصلاً موجودة بالقاموس الأساسي ({{level}}) ✨"
SWEAR_WORD_NOT_FOUND = f"{BULLET} هاي الكلمة مو موجودة بقاموس المجموعة 🌸"
SWEAR_WORD_BASE_REMOVE = (
    f"{BULLET} هاي من القاموس الأساسي وما تنحذف 🌸\n"
    f"{BULLET} إذا تريدها مسموحة بمجموعتك: <code>سماح كلمة ...</code>"
)
SWEAR_GLOBAL_DEV_ONLY = f"{BULLET} القاموس العام للمطور بس 🌸"
SWEAR_WORDS_LIMIT = f"{BULLET} قاموس المجموعة وصل الحد ({{n}} كلمة) 🌸 احذف شي قبل لا تضيف"
SWEAR_WORDS_HEADER = title("قَـامُـوس الـسَّـب", "📖") + f"\n{LINE}"
SWEAR_WORDS_BASE = f"{BULLET} القاموس الأساسي: <b>{{n}}</b> ({{detail}})"
SWEAR_WORDS_GLOBAL = f"{BULLET} القاموس العام: <b>{{n}}</b>"
SWEAR_WORDS_GROUP = f"{BULLET} كلمات المجموعة: <b>{{n}}</b>"
SWEAR_WORDS_EMPTY = f"{BULLET} ماكو كلمات مضافة، القاموس الأساسي شغّال 🤍"
SWEAR_WORDS_MORE = "▫️ … و{n} غيرها"
SWEAR_ALLOWED_LABEL = f"{BULLET} كلمات مسموحة (استثناءات):"
SWEAR_NEED_DELETE = f"{BULLET} تنبيه: أحتاج صلاحية «<b>حذف الرسائل</b>» حتى يشتغل قفل السب 🔐"
SWEAR_TEST_HEADER = title("فَـحْـص الـسَّـب", "🔎") + f"\n{LINE}"
SWEAR_TEST_NEED = f"{BULLET} اكتب النص بعد الأمر رجاءً 🌸 مثال: <code>فحص سب ك.ل.ب</code>"
SWEAR_TEST_NORM = f"{BULLET} بعد التطبيع: <tg-spoiler>{{norm}}</tg-spoiler>"
SWEAR_TEST_CLEAN = f"{BULLET} النتيجة: <b>سليمة</b> ✅"
SWEAR_TEST_ALLOWED = f"{BULLET} النتيجة: <b>مسموحة بهاي المجموعة</b> ✨ (استثناء)"
SWEAR_TEST_BLOCKED = (
    f"{BULLET} النتيجة: <b>محظورة</b> 🚫\n"
    f"{BULLET} اللي انكشف: <tg-spoiler>{{found}}</tg-spoiler>\n"
    f"{BULLET} يطابق: <tg-spoiler>{{key}}</tg-spoiler>\n"
    f"{BULLET} الفئة: <b>{{level}}</b> ⋅ {{kind}}\n"
    f"{BULLET} القفل: {{scope}} ⋅ <b>{{scope_mode}}</b>\n"
    f"{BULLET} المصدر: {{source}}\n"
    f"{BULLET} الإجراء هنا: <b>{{action}}</b>"
)
SWEAR_POLICY = (
    title("عُـقُـوبَـات الـسَّـب", "⚖️") + f"\n{LINE}\n"
    "{levels}\n" + f"{LINE}\n"
    "<i>{note}</i>"
)
SWEAR_POLICY_SCOPE = "<b>{scope}</b> ⋅ {mode}"
SWEAR_POLICY_LEVEL = "{level}: <b>{plan}</b>\n    ↫ {hint}"
SWEAR_POLICY_NOTE = ("المخالفات تنحسب آخر 7 أيام ⋅ مشرفين المجموعة: مسح بس بدون عقوبة ⋅ "
                     "اضغط على الفئة حتى تغير عقوبتها")
SWEAR_POLICY_NOTE_FIXED = "عقوبات الفئات تشتغل بوضع «🧠 تدريجي ذكي» بس ⋅ اضغط على الوضع حتى تغيره"
SWEAR_POLICY_FOOT = ("كل نوع يتقفل لوحده: «قفل الفشار» أو «قفل الاهانات» أو «قفل السب» للاثنين ⋅ "
                     "عقوبة الفئة تشتغل بالوضع التدريجي الذكي")
SWEAR_POLICY_NEED_RANK = "تغيير عقوبات السب يحتاج رتبة مدير 🌸"
SWEAR_BTN_MODE = "الوضع: {mode}"

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

# ── الملف الشخصي والشكر ─────────────────────────────
PROFILE = (
    title("مَـلَـفّ {name}", "🌸") + "\n"
    f"{LINE}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    f"{BULLET} المستوى: <b>{{level}}</b> ⋅ {{level_title}}\n"
    f"{BULLET} الرسائل: <b>{{messages}}</b> ⋅ التفاعل: {{activity}}\n"
    f"{BULLET} الشكر: <b>{{thanks}}</b> 🤍\n"
    f"{BULLET} التحذيرات: <b>{{warns}}/{{limit}}</b>\n"
    "{partner}"
    "{economy}"
    f"{BULLET} أول ظهور: <code>{{since}}</code>\n"
    "{rating}"
    f"{LINE}\n"
    f"{BULLET} النبذة: {{bio}}"
)
PROFILE_PARTNER = f"{BULLET} الشريك: {{partner}} 💍\n"
PROFILE_ECONOMY = f"{BULLET} الرصيد: <b>{{balance}}</b> 🌸\n"
PROFILE_SHOP_TITLE = f"{BULLET} اللقب الخاص: <b>{{title}}</b>\n"
PROFILE_RATING = (
    f"{LINE}\n"
    f"{BULLET} التقييم: {{stars}} <b>{{score}}</b>/10 <i>({{voters}} تقييم)</i>\n"
    f"{BULLET} إنسان جميل ✨: <b>{{good}}</b>\n"
    f"{BULLET} إنسان سيئ 👎🏻: <b>{{bad}}</b>\n"
)
PROFILE_RATE_HINT = f"{BULLET} <i>قيّمه من الأزرار الجوه 👇</i>"
RATE_NO_SCORE = "—"
BTN_RATE_GOOD = "إنسان جميل ✨ {n}"
BTN_RATE_BAD = "إنسان سيئ 👎🏻 {n}"
RATE_GOOD_DONE = "قيّمته: إنسان جميل ✨"
RATE_BAD_DONE = "قيّمته: إنسان سيئ 👎🏻"
RATE_REMOVED = "انشال تقييمك 🌸"
RATE_SCORE_DONE = "عطيته {n}/10 ⭐"
RATE_SELF = "ما يصير تقيّم نفسك 😄🌸"
RATE_BOT = "البوتات ما تنقيّم 🤖"
RATE_CMD_DONE = f"{BULLET} قيّمت {{mention}} بـ <b>{{n}}/10</b> ⭐"
RATE_CMD_BAD = f"{BULLET} اكتب رقم من 1 لـ 10 ويا الرد رجاءً 🌸 مثال: <code>قيمه 9</code>"
TOP_RATED_HEADER = title("الأعلى تقييماً", "⭐") + f"\n{LINE}"
TOP_RATED_EMPTY = f"{BULLET} ماكو تقييمات كافية لحد هسه 🌸 (يحتاج 3 تقييمات على الأقل)"
PROFILE_NO_BIO = "<i>ما مكتوبة بعد</i> ✏️"
BIO_SET = f"{BULLET} انحفظت نبذتك ✨ تطلع بملفك الشخصي"
BIO_DELETED = f"{BULLET} انمسحت نبذتك 🌸"
BIO_BAD = f"{BULLET} اكتب النبذة بعد الأمر رجاءً 🌸 (لحد 200 حرف)"
THANKS_DONE = f"{BULLET} وصل شكرك لـ {{mention}} 🤍 صار عنده <b>{{count}}</b> شكر"
THANKS_SELF = f"{BULLET} ما يصير تشكر نفسك 😄🌸"
THANKS_BOT = f"{BULLET} تسلم 🤍 بس البوتات ما تنحسب بالشكر"
THANKS_AGAIN = f"{BULLET} شكرت {{mention}} قبل شوية 🌸 تگدر تشكره مرة ثانية بعد {{left}}"
THANKS_LIMIT = f"{BULLET} وصلت للحد اليومي من الشكر 🌸 ارجع باچر"
TOP_THANKED_HEADER = title("الأكثر شكراً", "🤍") + f"\n{LINE}"
TOP_THANKED_EMPTY = f"{BULLET} ماكو شكر لحد هسه 🌸 اشكر أحد بالرد عليه بكلمة <code>شكر</code>"

# ── الاقتراحات ─────────────────────────────────────
SUGG_STATUS = {
    "new": "🆕 جديد",
    "review": "🔍 قيد المراجعة",
    "accepted": "✅ مقبول",
    "rejected": "❌ مرفوض",
}
SUGGESTION = (
    title("اِقْـتِـرَاح #{id}", "💡") + "\n"
    f"{LINE}\n"
    f"{BULLET} من: {{mention}}\n"
    f"{BULLET} الاقتراح:\n<i>{{text}}</i>\n"
    f"{LINE}\n"
    f"{BULLET} الحالة: <b>{{status}}</b>\n"
    f"{BULLET} التصويت: 👍 <b>{{up}}</b> ⋅ 👎 <b>{{down}}</b>"
    "{decided}"
)
SUGG_DECIDED = f"\n{BULLET} القرار بواسطة: {{actor}}"
SUGG_BAD = f"{BULLET} اكتب الاقتراح بعد الأمر رجاءً 🌸 (من 5 لـ 1000 حرف)"
SUGG_WAIT = f"{BULLET} على كيفك 🌸 تگدر تقترح مرة ثانية بعد {{left}}"
SUGG_VOTED = {1: "صوّتت 👍", -1: "صوّتت 👎", 0: "انلغى صوتك"}
SUGG_NEED_STAFF = "قرار الاقتراحات للأدمن وفوگ بس 🔐"
SUGG_GONE = "هذا الاقتراح ما موجود 🌸"
SUGG_LIST_HEADER = title("آخر الاقتراحات", "💡") + f"\n{LINE}"
SUGG_LIST_EMPTY = f"{BULLET} ماكو اقتراحات لحد هسه 🌸 اقترح بأمر <code>اقتراح</code>"
BTN_SUGG_REVIEW = "🔍 مراجعة"
BTN_SUGG_ACCEPT = "✅ قبول"
BTN_SUGG_REJECT = "❌ رفض"

# ── الشكاوى ────────────────────────────────────────
COMPLAINT_BAD = f"{BULLET} اكتب الشكوى بعد الأمر رجاءً 🌸 (من 5 لـ 1000 حرف)"
COMPLAINT_WAIT = f"{BULLET} شكوتك السابقة وصلت 🌸 تگدر ترسل وحدة ثانية بعد {{left}}"
COMPLAINT_SENT = f"{BULLET} {{mention}} وصلت شكوتك للإدارة بسرية تامة 🤍 رقمها <b>#{{id}}</b>"
COMPLAINT_DM = (
    title("شَـكْـوَى #{id}", "📮") + "\n"
    f"{LINE}\n"
    f"{BULLET} المجموعة: <b>{{group}}</b>\n"
    f"{BULLET} من: {{mention}}\n"
    f"{BULLET} الشكوى:\n<i>{{text}}</i>"
)
COMPLAINT_CLOSED_DM = f"{BULLET} شكوتك <b>#{{id}}</b> بمجموعة <b>{{group}}</b> انحلّت ✅ شكراً لصبرك 🤍"
COMPLAINT_CLOSED = f"{BULLET} انحلّت الشكوى <b>#{{id}}</b> ✅"
COMPLAINT_ALREADY = "هاي الشكوى انحلّت من قبل ✅"
COMPLAINT_NOT_FOUND = f"{BULLET} ماكو شكوى مفتوحة بهذا الرقم 🌸"
COMPLAINTS_HEADER = title("الشكاوى المفتوحة", "📮") + f"\n{LINE}"
COMPLAINTS_EMPTY = f"{BULLET} ماكو شكاوى مفتوحة، الكل مرتاح 🤍"
COMPLAINT_ITEM = "▫️ <b>#{id}</b> ⋅ {mention}\n    <i>{text}</i>"
COMPLAINTS_FOOTER = f"{LINE}\n{BULLET} للحل: <code>حل شكوى رقمها</code>"
COMPLAINT_NEED_STAFF = "حل الشكاوى للمدير وفوگ بس 🔐"
BTN_COMPLAINT_CLOSE = "✅ تم الحل"

# ── التصويت ────────────────────────────────────────
POLL_BAD = (
    f"{BULLET} اكتب السؤال بالسطر الأول، وكل خيار بسطر 🌸 (من 2 لـ 10 خيارات)\n"
    f"{BULLET} مثال:\n<code>تصويت شنو تحبون نسوي؟\nمسابقة\nسهرة\nتحدي</code>"
)
POLL_FAILED = f"{BULLET} ما گدرت أسوي التصويت 🤍 تأكد السؤال أقل من 300 حرف وكل خيار أقل من 100"

# ── الثنائيات ──────────────────────────────────────
PAIRS_OFF = f"{BULLET} الثنائيات معطّلة بهاي المجموعة 🌸 المدير يگدر يفعّلها بأمر <code>تفعيل الثنائيات</code>"
PAIRS_ON = f"{BULLET} تم تفعيل الثنائيات 💍"
PAIRS_DISABLED = f"{BULLET} تم تعطيل الثنائيات 🌸"
PAIR_REQUEST = (
    title("طَـلَـب اِرْتِـبَـاط", "💍") + "\n"
    f"{LINE}\n"
    f"{BULLET} {{from_}} يطلب الارتباط بـ {{to}} 🤍\n"
    f"{BULLET} القرار بإيد {{to}} بس"
)
PAIR_ACCEPTED = title("مَـبْـرُوك", "💍") + f"\n{LINE}\n{BULLET} {{a}} و {{b}} صاروا ثنائي 🤍✨"
PAIR_REJECTED = f"{BULLET} {{to}} اعتذر عن الطلب 🌸"
PAIR_SELF = f"{BULLET} ما يصير ترتبط بنفسك 😄🌸"
PAIR_BOT = f"{BULLET} البوتات ما ترتبط 🤖"
PAIR_YOU_TAKEN = f"{BULLET} انت مرتبط أصلاً 💍 فك ارتباطك أول"
PAIR_THEY_TAKEN = f"{BULLET} {{mention}} مرتبط أصلاً 🌸"
PAIR_NOT_YOURS = "القرار لصاحب الطلب بس 🌸"
PAIR_EXPIRED = "هذا الطلب ما عاد صالح 🌸"
PAIR_NONE = f"{BULLET} انت مو مرتبط 🌸"
PAIR_UNLINKED = f"{BULLET} تم فك الارتباط بين {{a}} و {{b}} 🤍"
PAIR_SHOW = f"{BULLET} شريكك: {{mention}} 💍 من <code>{{since}}</code>"
PAIR_HIDDEN = f"{BULLET} صار ارتباطك مخفي 🙈 ما يطلع بالملف ولا بالقائمة"
PAIR_SHOWN = f"{BULLET} صار ارتباطك ظاهر 💍"
PAIRS_HEADER = title("الثنائيات", "💍") + f"\n{LINE}"
PAIRS_EMPTY = f"{BULLET} ماكو ثنائيات لحد هسه 🌸"
BTN_PAIR_ACCEPT = "💍 قبول"
BTN_PAIR_REJECT = "🙅 رفض"

# ── المستويات ──────────────────────────────────────
LEVEL_CARD = (
    title("مُـسْـتَـوَى {name}", "📈") + "\n"
    f"{LINE}\n"
    f"{BULLET} المستوى: <b>{{level}}</b> ⋅ اللقب: {{title}}\n"
    f"{BULLET} الخبرة: <b>{{xp}}</b> نقطة\n"
    f"{BULLET} التقدم: {{bar}} <b>{{pct}}%</b>\n"
    f"{BULLET} باقي للمستوى {{next}}: <b>{{left}}</b> نقطة\n"
    f"{BULLET} الترتيب بالمجموعة: <b>#{{pos}}</b>\n"
    f"{BULLET} الفوز بالمسابقات: <b>{{wins}}</b> 🏆\n"
    f"{LINE}\n"
    f"{BULLET} الإنجازات: {{badges}}"
)
NO_BADGES = "<i>بعدها، كمّل وتوصل 💪</i>"
LEVEL_UP = f"🎉 {{mention}} وصل للمستوى <b>{{level}}</b> ✨\n{BULLET} اللقب: {{title}}"
LEVELS_OFF = f"{BULLET} المستويات معطّلة بهاي المجموعة 🌸"
LEADERBOARD_HEADERS = {
    "all": title("ترتيب المستويات", "🏆"),
    "week": title("ترتيب الأسبوع", "📅"),
    "month": title("ترتيب الشهر", "🗓"),
    "wins": title("ترتيب المسابقات", "🎯"),
}
LEADERBOARD_UNITS = {"all": "نقطة", "week": "نقطة", "month": "نقطة", "wins": "فوز"}
LEADERBOARD_EMPTY = f"{BULLET} ماكو نشاط بهاي الفترة لحد هسه 🌸"
TITLES_HEADER = title("الألقاب", "🎖") + f"\n{LINE}"
TITLES_LINE = "▫️ من المستوى <b>{level}</b> ← {title}"
TOGGLE_ON = f"{BULLET} تم تفعيل {{what}} ✅"
TOGGLE_OFF = f"{BULLET} تم تعطيل {{what}} ▫️"

# ── الألعاب ────────────────────────────────────────
GAMES_MENU = (
    title("الألعاب", "🎮") + "\n"
    f"{LINE}\n"
    f"{BULLET} اختار لعبة، وأول واحد يجاوب صح يفوز بنقاط خبرة 🏆\n"
    f"{BULLET} لعبة وحدة بكل مرة، والأجوبة تنكتب بالمجموعة عادي ✨"
)
GAMES_OFF = f"{BULLET} الألعاب معطّلة بهاي المجموعة 🌸"
GAME_RUNNING = f"{BULLET} اكو لعبة شغّالة هسه 🎮 جاوبوا عليها أول، أو اكتبوا <code>ايقاف اللعبة</code>"
GAME_COOLDOWN = "على كيفكم 🌸 ثواني وتبدي لعبة جديدة"
GAME_HEADER = {
    "quiz": ("سُـؤَال {level}", "❓"),
    "scramble": ("رَتِّـب الـحُـرُوف", "🔤"),
    "typing": ("أَسْـرَع كِـتَـابَـة", "⚡"),
    "math": ("رِيَـاضِـيَّـات", "➗"),
    "riddle": ("لُـغْـز", "🧩"),
    "daily": ("لُـغْـز الـيَـوْم", "🌟"),
    "duel": ("تَـحَـدِّي", "⚔️"),
}
GAME_PROMPTS = {
    "quiz": "{question}",
    "scramble": "رتب هاي الحروف وكوّن كلمة:\n\n<b>{question}</b>",
    "typing": "أول واحد يكتب هاي العبارة بالضبط يفوز:\n\n<b>{question}</b>",
    "math": "شكد ناتج:\n\n<b>{question}</b>",
    "riddle": "{question}",
    "daily": "{question}\n\n<i>أول واحد يحله اليوم ياخذ مكافأة كبيرة 🌟</i>",
    "duel": "{a} ضد {b}\nأول واحد منكم يجاوب يفوز:\n\n<b>{question}</b>",
}
GAME_BODY = (
    "\n" + f"{LINE}\n"
    f"{BULLET} الجائزة: <b>{{xp}}</b> نقطة خبرة ⋅ الوقت: <b>{{secs}}</b> ثانية ⏳"
)
QUIZ_LEVELS = {"easy": "سَـهْـل 🟢", "medium": "مُـتَـوَسِّـط 🟡", "hard": "صَـعْـب 🔴"}
GAME_WIN = (
    title("جَـوَاب صَـح", "🎉") + "\n"
    f"{LINE}\n"
    f"{BULLET} الفائز: {{mention}} 🏆\n"
    f"{BULLET} الجواب: <b>{{answer}}</b>\n"
    f"{BULLET} الوقت: <b>{{secs}}</b> ثانية\n"
    f"{BULLET} الجائزة: <b>+{{xp}}</b> نقطة خبرة و <b>+{{xp}}</b> 🌸"
)
GAME_TIMEOUT = title("خِـلَـص الـوَقْـت", "⏰") + f"\n{BULLET} الجواب الصحيح: <b>{{answer}}</b>\n{BULLET} الجاية تكون إلكم 💪"
GAME_STOPPED = f"{BULLET} توقفت اللعبة 🌸 الجواب كان: <b>{{answer}}</b>"
GAME_NONE = f"{BULLET} ماكو لعبة شغّالة هسه 🎮"
GAME_STOP_DENIED = f"{BULLET} اللي بدأ اللعبة أو الأدمن وفوگ بس يگدرون يوقفونها 🌸"
TYPING_COPY = "◈ النسخ واللصق ما يحسب 😄 اكتبها بإيدك"
DAILY_SOLVED = f"{BULLET} لغز اليوم انحل من قبل {{mention}} 🌟 ارجعوا باچر للغز جديد"
DUEL_SELF = f"{BULLET} ما يصير تتحدى نفسك 😄"
DUEL_BOT = f"{BULLET} ما يصير تتحدى بوت 🤖"
BTN_GAMES = {
    "quiz": "❓ سؤال",
    "scramble": "🔤 رتب",
    "typing": "⚡ أسرع",
    "math": "➗ رياضيات",
    "riddle": "🧩 لغز",
    "daily": "🌟 لغز اليوم",
}

# ── الاقتصاد ───────────────────────────────────────
COIN = "🌸"
CURRENCY = "زهرة"
ECONOMY_OFF = f"{BULLET} الاقتصاد معطّل بهاي المجموعة 🌸"
WALLET = (
    title("مَـحْـفَـظَـة {name}", "👛") + "\n"
    f"{LINE}\n"
    f"{BULLET} الرصيد: <b>{{balance}}</b> {COIN}\n"
    f"{BULLET} مجموع اللي ربحه: <b>{{earned}}</b> {COIN}\n"
    f"{BULLET} سلسلة الأيام: <b>{{streak}}</b> 🔥\n"
    f"{BULLET} الترتيب بالأغنى: <b>#{{pos}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} <i>الزهرات نقاط افتراضية للمتعة بس، مو فلوس حقيقية</i>"
)
DAILY_DONE = (
    title("الـمُـكَـافَـأَة الـيَـوْمِـيَّـة", "🎁") + "\n"
    f"{LINE}\n"
    f"{BULLET} ربحت: <b>+{{amount}}</b> {COIN}\n"
    f"{BULLET} سلسلة الأيام: <b>{{streak}}</b> 🔥 {{bonus}}\n"
    f"{BULLET} رصيدك هسه: <b>{{balance}}</b> {COIN}\n"
    f"{BULLET} ارجع باچر حتى تكبر السلسلة ✨"
)
DAILY_BONUS = "(+{n} مكافأة سلسلة)"
DAILY_WAIT = f"{BULLET} أخذت مكافأتك 🌸 ارجع بعد <b>{{left}}</b>"
MISSIONS_HEADER = title("مَـهَـامّ الـيَـوْم", "🎯") + f"\n{LINE}"
MISSION_LINE = "{mark} {name}  <b>{progress}/{target}</b> ⋅ " + COIN + " {reward}"
MISSIONS_FOOTER = f"{LINE}\n{BULLET} المهام تتجدد كل يوم، والمكافأة تنضاف تلقائياً لما تكملها ✨"
MISSION_DONE = f"🎯 {{mention}} خلص مهمة «{{name}}» وربح <b>+{{reward}}</b> {COIN}"
MISSION_NAMES = {
    "messages": "💬 تفاعل بالمجموعة",
    "win": "🎮 افوز بلعبة",
    "thank": "🤍 اشكر عضو",
}
SHOP_MARK = "الـمَـتْـجَـر"
SHOP = (
    title(SHOP_MARK, "🛍") + "\n"
    f"{LINE}\n"
    f"{BULLET} رصيدك: <b>{{balance}}</b> {COIN}\n"
    f"{BULLET} اضغط على أي عنصر حتى تشتريه وتلبسه مباشرة ✨\n"
    f"{BULLET} اللقب المخصص: اكتب <code>لقب مخصص النص</code>\n"
    f"{LINE}\n"
    f"{BULLET} <i>كل العناصر شكلية، تطلع بملفك الشخصي</i>"
)
SHOP_ITEM_BTN = "{name} ⋅ {price}{coin}"
SHOP_OWNED_BTN = "✅ {name}"
BOUGHT = "اشتريت {name} ولبسته ✨"
EQUIPPED = "لبست {name} ✨"
UNEQUIPPED = "نزعت {name} 🌸"
NO_FUNDS = "رصيدك ما يكفي 🌸 تحتاج {price}{coin} وعندك {balance}{coin}"
NO_FUNDS_TEXT = f"{BULLET} رصيدك ما يكفي 🌸 تحتاج <b>{{price}}</b> {COIN} وعندك <b>{{balance}}</b> {COIN}"
NOT_YOUR_SHOP = "هذا المتجر مو إلك 🌸 اكتب «المتجر» حتى يطلعلك متجرك"
INVENTORY = (
    title("مُـمْـتَـلَـكَـاتِـي", "🎒") + "\n"
    f"{LINE}\n"
    f"{BULLET} اللقب: {{title}}\n"
    f"{BULLET} الإطار: {{frame}}\n"
    f"{LINE}\n"
    f"{BULLET} اضغط على أي عنصر حتى تلبسه أو تنزعه ✨"
)
INVENTORY_EMPTY = f"{BULLET} ما عندك ممتلكات لحد هسه 🌸 روح للمتجر بأمر <code>المتجر</code>"
NOTHING = "ماكو"
CUSTOM_TITLE_BAD = f"{BULLET} اكتب اللقب بعد الأمر رجاءً 🌸 (من 2 لـ 20 حرف) مثال: <code>لقب مخصص ملك الضحك</code>"
CUSTOM_TITLE_SWEAR = f"{BULLET} هذا اللقب بيه كلام مو مقبول 🌸 اختار لقب ثاني"
CUSTOM_TITLE_DONE = f"{BULLET} صار لقبك: <b>{{title}}</b> ✨ وانخصم <b>{{price}}</b> {COIN}"
TRANSFER_DONE = (
    title("تَـمَّ الـتَّـحْـوِيـل", "💸") + "\n"
    f"{LINE}\n"
    f"{BULLET} من: {{from_}}\n"
    f"{BULLET} إلى: {{to}}\n"
    f"{BULLET} المبلغ: <b>{{amount}}</b> {COIN}\n"
    f"{BULLET} الرسوم: <b>{{fee}}</b> {COIN}"
)
TRANSFER_BAD = f"{BULLET} اكتب المبلغ ويا الرد على الشخص رجاءً 🌸 (لحد مليون) مثال: <code>تحويل 100</code>"
TRANSFER_SELF = f"{BULLET} ما يصير تحوّل لنفسك 😄"
TRANSFER_BOT = f"{BULLET} البوتات ما تستلم زهرات 🤖"
TRANSFER_NEW = f"{BULLET} حتى تگدر تحوّل، لازم يكون عندك {{n}} رسالة بالمجموعة على الأقل 🌸"
HISTORY_HEADER = title("سِـجِـلّ الـمَـحْـفَـظَـة", "📒") + f"\n{LINE}"
HISTORY_EMPTY = f"{BULLET} ماكو حركات لحد هسه 🌸"
TX_KINDS = {
    "daily": "🎁 مكافأة يومية", "mission": "🎯 مهمة", "game": "🎮 فوز بلعبة", "levelup": "📈 ترقية مستوى",
    "transfer_in": "📥 تحويل وارد", "transfer_out": "📤 تحويل صادر", "buy": "🛍 شراء",
    "admin_give": "👑 إضافة من الإدارة", "admin_take": "👑 خصم من الإدارة",
}
RICH_HEADER = title("الأَغْـنَـى", "💰")
ADMIN_GIVE = f"{BULLET} انضاف <b>{{amount}}</b> {COIN} لـ {{mention}} ✨ رصيده هسه <b>{{balance}}</b> {COIN}"
ADMIN_TAKE = f"{BULLET} انخصم <b>{{amount}}</b> {COIN} من {{mention}} 🌸 رصيده هسه <b>{{balance}}</b> {COIN}"
ADMIN_AMOUNT_BAD = f"{BULLET} اكتب المبلغ ويا الرد رجاءً 🌸 (من 1 لـ 100000)"

# ── القفل والفتح ───────────────────────────────────
LOCK_PANEL = (
    title("الأقفال", "🔒") + "\n"
    f"{LINE}\n"
    f"{BULLET} 🔒 مقفول ⋅ 🔓 مفتوح\n"
    f"{BULLET} اضغط على أي نوع حتى تقفله أو تفتحه ✨\n"
    f"{BULLET} زر السب يتنقل بين: مفتوح ← مسح ← كتم ← حظر\n"
    f"{LINE}\n"
    f"{BULLET} 🌟 المميز يكدر يرسل الصور والفيديو والملصقات حتى لو مقفولة\n"
    f"{BULLET} 🛡 الملفات والصوتيات والروابط وغيرها: للمشرفين بس"
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

# ── الأقفال v2: الأوضاع والصفحات ─────────────────────
LOCK_MODES = {
    "delete": ("🗑", "مسح"),
    "warn": ("⚠️", "تحذير"),
    "mute": ("🔇", "كتم ساعة"),
    "restrict": ("⛓", "تقييد"),
    "kick": ("👢", "طرد"),
}
LOCK_PAGES = {"media": "🖼 الوسائط", "content": "📝 المحتوى", "behavior": "🛡 السلوك"}
LOCK_PANEL_V2 = (
    title("الأقفال", "🔒") + "\n"
    f"{LINE}\n"
    f"{BULLET} الصفحة: <b>{{page}}</b> ⋅ الأقفال الفعالة: <b>{{count}}</b>\n"
    f"{BULLET} اضغط على أي نوع حتى يتنقل: 🔓 مفتوح ← 🗑 مسح ← ⚠️ تحذير ← 🔇 كتم ← ⛓ تقييد ← 👢 طرد\n"
    f"{BULLET} المسح متدرج: بعد 3 مخالفات بنص ساعة يصير كتم ساعة\n"
    f"{LINE}\n"
    f"{BULLET} 🌟 المميز يكدر يرسل الصور والفيديو والملصقات حتى لو مقفولة\n"
    f"{BULLET} 🛡 الملفات والصوتيات والروابط وغيرها: للمشرفين بس"
)
LOCKED_MODE = title("تَـمَّ الـقَـفْـل", "🔒") + f"\n{BULLET} {{what}}\n{BULLET} العقوبة: <b>{{mode}}</b>\n{BULLET} بواسطة: {{actor}}"
ALREADY_LOCKED_MODE = f"{BULLET} {{what}} مقفولة من قبل بوضع <b>{{mode}}</b> 🔒"
LOCK_MODE_NOT_ALLOWED = f"{BULLET} هذا القفل ما يقبل هالوضع 🌸 الأوضاع المتاحة: {{modes}}"
LOCK_STRIKE_NOTICE = f"{BULLET} {{mention}} عيني، <b>{{what}}</b> مقفولة هسه بالمجموعة 🔒 <i>({{strike}}/{{max}})</i>"
LOCK_PUNISHED = (
    title("{head}", "{emoji}") + "\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} السبب: <b>{{what}}</b> مقفولة\n"
    "{extra}"
)
LOCK_WARNED = f"{BULLET} التحذيرات: <b>{{count}}/{{limit}}</b>\n"
LOCK_WHY = "مخالفة الأقفال"
JOIN_KICKED = f"{BULLET} الدخول مقفول هسه 🔒 طلعت {{mention}} تلقائياً"
BOTS_ADDER_KICKED = f"{BULLET} وطردت {{mention}} اللي ضافه، لأن إضافة البوتات مقفولة بالطرد 👢"
EDIT_LOCK_NOTICE = f"{BULLET} {{mention}} عيني، التعديل مقفول بالمجموعة 🔒 انمسحت رسالتك المعدّلة"
HELP_LOCK_TYPES = (
    f"\n{BULLET} <b>الوسائط:</b> الصور، الفيديو، المتحركات، الملصقات، البصمات، الصوتيات، الملفات، "
    "الجهات، المواقع، الاستفتاءات\n"
    f"{BULLET} <b>المحتوى:</b> الكتابة، الروابط، المعرفات، التاك، التوجيه، الانلاين، الكلايش، "
    "الإيرانية، الإباحي، جمثون\n"
    f"{BULLET} <b>السلوك:</b> التعديل، تعديل الميديا، التكرار، الرياكت، الإشعارات، الدخول، البوتات، الدردشة\n"
    f"{BULLET} <b>الأوضاع:</b> <code>قفل الصور</code> (مسح) ، <code>قفل الصور بالتحذير</code> ، "
    "<code>بالكتم</code> ، <code>بالتقييد</code> ، <code>بالطرد</code>\n"
    f"{BULLET} السب: <code>قفل السب</code> ، <code>قفل السب بالكتم</code> ، <code>قفل السب بالحظر</code>"
)

# ── الميزات (تفعيل / تعطيل) ──────────────────────────
FEATURE_ON = f"{BULLET} تم تفعيل <b>{{what}}</b> ✅"
FEATURE_OFF_DONE = f"{BULLET} تم تعطيل <b>{{what}}</b> ▫️"
FEATURE_ALREADY_ON = f"{BULLET} <b>{{what}}</b> مفعّلة من قبل ✅"
FEATURE_ALREADY_OFF = f"{BULLET} <b>{{what}}</b> معطّلة من قبل ▫️"
FEATURE_DISABLED = f"{BULLET} هذا الأمر معطّل بهاي المجموعة 🌸"
FEATURES_PANEL = (
    title("الـمِـيـزَات", "🎛") + "\n"
    f"{LINE}\n"
    f"{BULLET} اضغط على أي ميزة حتى تشغّلها أو تطفيها ✨\n"
    f"{BULLET} أو بالأوامر: <code>تفعيل الكت</code> ، <code>تعطيل المنشن</code>\n"
    f"{LINE}\n"
    f"{BULLET} الميزات المعطّلة تبقى شغّالة للمالك وفوگ 👑"
)
FEATURES_HINT = f"{BULLET} اكتب اسم الميزة بعد الأمر 🌸 أو افتح <code>الميزات</code> حتى تشوفها كلها"

# ── ضافني وافتاري واطردني ────────────────────────────
WHO_ADDED = f"{BULLET} {{mention}} ضافه: {{adder}} 🤍"
WHO_ADDED_SELF = f"{BULLET} {{mention}} دخل بنفسه (بالرابط) 🔗"
WHO_ADDED_UNKNOWN = f"{BULLET} ما أعرف منو ضاف {{mention}} 🌸 (دخل قبل ما أصير بالمجموعة)"
AVATAR_CAPTION = f"{BULLET} صورة {{mention}} 📸 ⋅ عنده <b>{{count}}</b> صورة"
AVATAR_NONE = f"{BULLET} {{mention}} ما عنده صورة، أو مخفيها 🌸"
KICKME_ASK = f"{BULLET} {{mention}} متأكد تريد تطلع من المجموعة؟ 🥺"
KICKME_ADMIN = f"{BULLET} انت من الإدارة، ما أگدر أطلعك 🌸"
KICKME_DONE = f"{BULLET} طلّعت {{mention}} مثل ما طلب 👋 الله وياه"
KICKME_STAY = f"{BULLET} زين سويت 🤍 خلّيك ويانه"
KICKME_NOT_YOURS = "هذا الزر لصاحب الطلب بس 🌸"
BTN_KICKME_YES = "👋 إي، طلعني"
BTN_KICKME_NO = "🤍 لا، أبقى"

# ── المنشن للكل ─────────────────────────────────────
MENTION_HEADER = title("نِـدَاء لِـلـكُـلّ", "📣") + "\n{text}\n" + f"{LINE}\n"
MENTION_RUNNING = f"{BULLET} اكو منشن شغّال هسه 🌸 انتظره يخلص أو اكتب <code>ايقاف المنشن</code>"
MENTION_STOPPED = f"{BULLET} وگفت المنشن 🌸"
MENTION_NONE = f"{BULLET} ماكو منشن شغّال 🌸"
MENTION_EMPTY = f"{BULLET} ماكو أعضاء نشطين أنادي عليهم 🌸"
MENTION_DONE = f"{BULLET} خلص النداء ✅ ناديت <b>{{n}}</b> عضو"

# ── التسلية والكت ───────────────────────────────────
FUN_RATIO = f"{BULLET} {{what}} {{who}}: <b>{{pct}}%</b> {{emoji}}\n{BULLET} {{bar}}"
FUN_LOVE = f"{BULLET} نسبة الحب بين {{a}} و {{b}}: <b>{{pct}}%</b> 💞\n{BULLET} {{bar}}"
FUN_LOVE_NEED = f"{BULLET} رد على رسالة الشخص حتى أحسب نسبة الحب 💞"
FUN_LUCK = f"{BULLET} حظ {{mention}} اليوم: <b>{{luck}}</b>"
FUN_CHOICE = f"{BULLET} زهو تختار: <b>{{choice}}</b> ✨"
FUN_CHOICE_BAD = f"{BULLET} اكتب الخيارات بينهن «او» 🌸 مثال: <code>زهو اختاري شاي او قهوة</code>"
KT_TITLE = title("كَـت", "💭")

# ── الخدمية ─────────────────────────────────────────
TIME_TEXT = f"{BULLET} الساعة هسه ببغداد: <b>{{time}}</b> 🕰"
DATE_TEXT = f"{BULLET} اليوم: <b>{{weekday}}</b> ⋅ <b>{{day}} {{month}} {{year}}</b> 📅"
CALC_RESULT = f"{BULLET} <code>{{expr}}</code> = <b>{{result}}</b> 🧮"
CALC_BAD = f"{BULLET} ما فهمت العملية 🌸 مثال: <code>احسب (5 + 3) × 2</code>"

# ── يوتيوب ─────────────────────────────────────────
YT_NEED_QUERY = f"{BULLET} اكتب اللي تدور عليه بعد الأمر 🌸 مثال: <code>يوت زيارة عاشوراء</code>"
YT_SEARCHING = f"{BULLET} دا أدور على «<b>{{query}}</b>» 🔎"
YT_RESULTS = (
    title("نَـتَـائِـج الـبَـحْـث", "🎧") + "\n"
    f"{LINE}\n"
    f"{BULLET} «<b>{{query}}</b>»\n"
    f"{BULLET} اختار اللي تريده وأدزه إلك صوت 🎵"
)
YT_NONE = f"{BULLET} ما لگيت شي بهذا الاسم 🌸 جرب كلمات ثانية"
YT_DOWNLOADING = f"{BULLET} دا أحمّل «<b>{{title}}</b>» ⏳ ثواني وتوصلك..."
YT_TOO_LONG = f"{BULLET} هذا المقطع طويل (<b>{{dur}}</b>)، الحد الأقصى ساعة وحدة 🌸"
YT_TOO_BIG = f"{BULLET} الملف أكبر من حد تيليجرام (50 ميگا) 🌸 اختار مقطع أقصر"
YT_LIVE = f"{BULLET} هذا بث مباشر، ما أگدر أحمّله 🌸"
YT_FAILED = f"{BULLET} ما گدرت أحمّله 🤍 يمكن يوتيوب حاجبه أو النت ضعيف، جرب بعد شوية"
YT_NO_LIB = f"{BULLET} ميزة يوتيوب تحتاج مكتبة <code>yt-dlp</code> — لازم تنزلها من Pip"
YT_BUSY = f"{BULLET} اكو تحميل شغّال هسه بالمجموعة، انتظره يخلص 🌸"
YT_WAIT = f"{BULLET} على كيفك 🌸 تگدر تطلب مرة ثانية بعد <b>{{left}}</b>"
YT_NOT_YOURS = "هاي النتائج لصاحب الطلب بس 🌸 اكتب «يوت» واللي تريده"
YT_EXPIRED = "هاي النتائج قديمة 🌸 ابحث من جديد"
YT_CAPTION = f"🎧 <b>{{title}}</b>\n{BULLET} {{channel}} ⋅ ⏱ {{dur}}\n{BULLET} طلبها: {{mention}}"

# ── الذكاء الاصطناعي ───────────────────────────────
AI_NO_KEY = f"{BULLET} الذكاء الاصطناعي يحتاج مفتاح Claude من المطور (<code>ANTHROPIC_API_KEY</code>) 🔐"
AI_OFF = f"{BULLET} الذكاء الاصطناعي مطفي بهاي المجموعة 🌸 المالك يگدر يشغّله بأمر <code>تفعيل الذكاء</code>"
AI_ENABLED = (
    title("تَـمَّ تَـفْـعِـيـل الـذَّكَـاء", "🧠") + "\n"
    f"{LINE}\n"
    f"{BULLET} هسه تگدرون تسألوني: <code>اسأل شنو قوانين المجموعة؟</code>\n"
    f"{BULLET} وأگدر ألخص النقاش: <code>لخص</code>\n"
    f"{LINE}\n"
    f"⚠️ <b>للشفافية:</b>\n"
    f"{BULLET} الأسئلة، والرسائل اللي تطلبون تلخيصها، تنرسل لخدمة <b>Claude</b> من شركة Anthropic حتى أفهمها\n"
    f"{BULLET} أحتفظ بآخر 150 رسالة <b>بالذاكرة بس</b> (ما تنحفظ بقاعدة البيانات)، وتنمسح إذا انطفى الذكاء أو رجع البوت يشتغل\n"
    f"{BULLET} للإيقاف بأي وقت: <code>تعطيل الذكاء</code>\n"
    f"{BULLET} بواسطة: {{actor}}"
)
AI_DISABLED = f"{BULLET} انطفى الذكاء، ومسحت كل الرسائل المؤقتة 🌸"
AI_ALREADY_ON = f"{BULLET} الذكاء شغّال من قبل 🧠"
AI_ALREADY_OFF = f"{BULLET} الذكاء مطفي من قبل 🌸"
AI_THINKING = f"{BULLET} دا أفكر 🧠..."
AI_ANSWER = "🧠 {answer}"
AI_REFUSED = f"{BULLET} هذا الطلب ما أگدر أجاوب عليه 🌸"
AI_QUOTA_GROUP = f"{BULLET} خلصت حصة الذكاء اليومية للمجموعة (<b>{{n}}</b> طلب) 🌸 ترجع باچر"
AI_QUOTA_GLOBAL = f"{BULLET} الذكاء وصل حده اليومي على البوت كله 🌸 ارجعوا باچر"
AI_WAIT = f"{BULLET} على كيفك 🌸 تگدر تطلب مرة ثانية بعد <b>{{left}}</b>"
AI_ERR_KEY = f"{BULLET} مفتاح الذكاء مو صحيح أو انتهى رصيده 🔐 المطور لازم يتأكد منه"
AI_ERR_BUSY = f"{BULLET} خدمة الذكاء مزدحمة هسه، جرب بعد شوية 🌸"
AI_ERR_NET = f"{BULLET} ما گدرت أوصل لخدمة الذكاء 🤍 تأكد من النت أو الـ VPN"
AI_ERR = f"{BULLET} صار خلل بخدمة الذكاء، جرب بعد شوية 🤍"
AI_NO_LIB = f"{BULLET} الذكاء يحتاج مكتبة <code>anthropic</code> — المطور لازم ينزلها من Pip"
AI_NEED_QUESTION = f"{BULLET} اكتب سؤالك بعد الأمر 🌸 مثال: <code>اسأل شنو قوانين المجموعة؟</code>"
AI_SUMMARY = title("مُـلَـخَّـص الـنِّـقَـاش", "📝") + f"\n<i>آخر {{n}} رسالة</i>\n{LINE}\n{{text}}"
AI_SUMMARY_FEW = f"{BULLET} الرسائل قليلة للتلخيص 🌸 أحتاج 10 رسائل على الأقل من بعد ما اشتغل الذكاء"
AI_KB_SET = f"{BULLET} انحفظت معلومات المجموعة للذكاء ✨ هسه أجاوب منها"
AI_KB_DELETED = f"{BULLET} انمسحت معلومات الذكاء 🌸"
AI_KB_SHOW = title("مَـعْـلُـومَـات الـذَّكَـاء", "📚") + f"\n{LINE}\n{{text}}"
AI_KB_EMPTY = f"{BULLET} ماكو معلومات مضافة 🌸 (القوانين تنحسب تلقائياً)\n{BULLET} للإضافة: <code>تعيين معلومات الذكاء النص</code>"
AI_KB_BAD = f"{BULLET} اكتب المعلومات بعد الأمر رجاءً 🌸 (لحد 3000 حرف)"
AI_REPLY_NEED = f"{BULLET} رد على الرسالة اللي تريد أقترحلها رد 🌸"
AI_REPLY = title("رَد مُـقْـتَـرَح", "💡") + f"\n<i>اقتراح بس، وما نفذت أي عقوبة</i>\n{LINE}\n{{text}}"
AI_IDEAS = title("أَفْـكَـار فَـعَـالِـيَّـات", "🎉") + f"\n{LINE}\n{{text}}"
AI_CLASSIFY = title("تَـصْـنِـيـف الاقْـتِـرَاحَـات", "🗂") + f"\n{LINE}\n{{text}}"
AI_CLASSIFY_NONE = f"{BULLET} ماكو اقتراحات أصنفها 🌸"
AI_SETTINGS = title("مُـسَـاعِـد الإِعْـدَادَات", "⚙️") + f"\n<i>هاي توصيات بس، نفّذ اللي يعجبك</i>\n{LINE}\n{{text}}"
AI_SETTINGS_NEED = f"{BULLET} وصفلي مجموعتك بعد الأمر 🌸 مثال: <code>ساعدني بالاعدادات مجموعة دراسية فيها 500 عضو وبيها سبام روابط</code>"
AI_LIMIT_SET = f"{BULLET} صار حد الذكاء لهاي المجموعة <b>{{n}}</b> طلب باليوم ✨"
AI_LIMIT_BAD = f"{BULLET} اكتب رقم من 1 لـ 1000 🌸 مثال: <code>حد الذكاء 50</code>"
AI_USAGE = (
    title("اِسْـتِـهْـلَاك الـذَّكَـاء", "📊") + "\n"
    f"{LINE}\n"
    f"{BULLET} النموذج: <code>{{model}}</code> ⋅ المفتاح: {{key}}\n"
    f"{BULLET} اليوم: <b>{{t_req}}</b> طلب ⋅ <b>{{t_in}}</b> دخل ⋅ <b>{{t_out}}</b> خرج\n"
    f"{BULLET} آخر 30 يوم: <b>{{m_req}}</b> طلب ⋅ التكلفة التقريبية: <b>${{cost}}</b>\n"
    f"{BULLET} الحد اليومي للبوت كله: <b>{{limit}}</b> طلب\n"
    f"{BULLET} المجموعات المفعّل بيها: <b>{{groups}}</b>"
)

# ── الأذكار ────────────────────────────────────────
AZKAR_TITLE = title("ذِكْـر", "📿")

# ── الترحيب والتوديع ───────────────────────────────
DEFAULT_WELCOME = (
    "✿ هلا وميت هلا {الاسم} 🌸\n"
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
LINK_TEXT = (
    title("رَابِـط الـمَـجْـمُـوعَـة", "🔗") + f"\n{LINE}\n"
    "🏡 <b>{title}</b>\n"
    "{members}"
    f"{LINE}\n"
    "🔗 <code>{link}</code>\n"
    f"{LINE}\n"
    "<i>اضغط «انضمام» أو انسخ الرابط وشاركه ويا أحبابك 🤍</i>"
)
LINK_MEMBERS = "👥 الأعضاء: <b>{n}</b>\n"
LINK_BTN_JOIN = "🚪 انضمام"
LINK_BTN_SHARE = "📤 مشاركة"
LINK_BTN_COPY = "📋 نسخ الرابط"
LINK_SHARE_TEXT = "تعال انضم ويانا بمجموعة {title} 🤍"
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

# ── إيقاف وتعطيل زهو ───────────────────────────────
BOT_PAUSED = (
    title("تَـمَّ إِيـقَـاف زَهـو", "🌙") + "\n"
    f"{LINE}\n"
    f"{BULLET} الحماية باقية شغّالة بصمت: أمسح السب والمقفولات بسرعة، بدون كتم ولا ردود\n"
    f"{BULLET} لتشغيل كل الخدمات اكتب: <code>/فتح زهو</code>\n"
    f"{BULLET} بواسطة: {{actor}}"
)
BOT_PAUSED_REPLY = (
    f"{BULLET} البوت تم إيقاف نص خدماته 🌙\n"
    f"{BULLET} لتشغيلها اكتب: <code>/فتح زهو</code>"
)
BOT_RESUMED = title("تَـمَّ تَـشْـغِـيـل زَهـو", "✨") + f"\n{BULLET} رجعت كل الخدمات 🤍\n{BULLET} بواسطة: {{actor}}"
BOT_DISABLED = (
    title("تَـمَّ تَـعْـطِـيـل الـبُـوت", "💤") + "\n"
    f"{LINE}\n"
    f"{BULLET} الحماية والردود كلها متوقفة\n"
    f"{BULLET} للتفعيل اكتب: <code>/تفعيل البوت</code>\n"
    f"{BULLET} بواسطة: {{actor}}"
)
BOT_ENABLED = title("تَـمَّ تَـفْـعِـيـل الـبُـوت", "✨") + f"\n{BULLET} رجعت الحماية وكل الخدمات 🤍\n{BULLET} بواسطة: {{actor}}"
BOT_ALREADY_PAUSED = f"{BULLET} زهو موقوفة من قبل 🌙"
BOT_ALREADY_DISABLED = f"{BULLET} البوت معطّل من قبل 💤"
BOT_ALREADY_ON = f"{BULLET} زهو شغّالة أصلاً ✨"
BOT_QUIET_ALERT = "زهو موقوفة بهاي المجموعة 🌙"

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

# ── الإذاعة ────────────────────────────────────────
BC_TARGETS = {"groups": "👥 المجموعات", "users": "👤 المستخدمين", "all": "🌐 الكل"}
BC_ASK_TARGET = (
    title("الإِذَاعَـة", "📢") + "\n"
    f"{LINE}\n"
    f"{BULLET} المجموعات الفعّالة: <b>{{groups}}</b>\n"
    f"{BULLET} المستخدمين اللي بدوا محادثة ويايه: <b>{{users}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} منو تريد توصله الإذاعة؟"
)
BC_ASK_CONTENT = (
    f"{BULLET} تمام ✨ الجمهور: <b>{{target}}</b>\n"
    f"{BULLET} هسه دزلي رسالة الإذاعة (نص، صورة، فيديو، ملف، أو أي شي)\n" + "{cancel}"
)
BC_CONFIRM = (
    title("مُـعَـايَـنَـة الإِذَاعَـة", "👀") + "\n"
    f"{LINE}\n"
    f"{BULLET} فوگ تشوف شكل الرسالة بالضبط\n"
    f"{BULLET} الجمهور: <b>{{target}}</b> ⋅ العدد: <b>{{count}}</b>\n"
    f"{BULLET} الوقت المتوقع: <b>{{eta}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} متأكد تريد ترسلها؟"
)
BC_PRESS_BUTTON = f"{BULLET} اضغط «إرسال» أو «إلغاء» فوگ 🌸"
BC_STARTED = f"{BULLET} بديت الإرسال ⏳ أبلغك أول ما أخلص"
BC_BUSY = "اكو إذاعة شغّالة هسه، انتظرها تخلص 🌸"
BC_EXPIRED = "هاي الإذاعة انتهت أو انلغت 🌸"
BC_CANCELLED = f"{BULLET} انلغت الإذاعة 🌸"
BC_DONE = (
    title("خِـلْـصَـت الإِذَاعَـة", "✅") + "\n"
    f"{LINE}\n"
    f"{BULLET} وصلت: <b>{{sent}}</b>\n"
    f"{BULLET} ما وصلت: <b>{{failed}}</b> <i>(طلعوني أو حظروني)</i>\n"
    f"{BULLET} الوقت: <b>{{secs}}</b>"
)
BC_EMPTY = f"{BULLET} ماكو أحد بهذا الجمهور لحد هسه 🌸"
LESS_THAN_MINUTE = "أقل من دقيقة"
BTN_BC_SEND = "✅ إرسال"
BTN_BC_CANCEL = "✖️ إلغاء"

# ── النسخ الاحتياطي ─────────────────────────────────
BACKUP_CAPTION = (
    title("نُـسْـخَـة اِحْـتِـيَـاطِـيَّـة", "💾") + "\n"
    f"{BULLET} المجموعات: <b>{{groups}}</b> ⋅ المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} إصدار القاعدة: <b>{{version}}</b> ⋅ الحجم: <b>{{size}}</b>\n"
    f"{BULLET} السلامة: ✅ مفحوصة\n"
    f"{BULLET} <i>احتفظ بيها، وللاستعادة: <code>استعادة نسخة</code></i>"
)
BACKUP_WORKING = f"{BULLET} دا أسوي نسخة احتياطية ⏳"
BACKUP_FAILED = f"{BULLET} ما گدرت أسوي النسخة 🤍 شوف السجل"
RESTORE_ASK = (
    title("اِسْـتِـعَـادَة نُـسْـخَـة", "♻️") + "\n"
    f"{LINE}\n"
    f"{BULLET} دزلي ملف النسخة (ينتهي بـ <code>.db</code>)\n"
    f"{BULLET} قبل الاستعادة راح أسوي نسخة أمان من الحالية، فما يضيع شي\n" + "{cancel}"
)
RESTORE_NEED_FILE = f"{BULLET} لازم تدزلي ملف <code>.db</code> 🌸 (أقل من 20 ميگا)"
RESTORE_BAD_FILE = f"{BULLET} هذا الملف مو نسخة صالحة من زهو 🤍 (فشل فحص السلامة)"
RESTORE_CONFIRM = (
    title("فَـحْـص الـنُّـسْـخَـة", "🔍") + "\n"
    f"{LINE}\n"
    f"{BULLET} السلامة: ✅\n"
    f"{BULLET} المجموعات: <b>{{groups}}</b> ⋅ المستخدمين: <b>{{users}}</b>\n"
    f"{BULLET} إصدار القاعدة: <b>{{version}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} ⚠️ الاستعادة تبدل كل البيانات الحالية بهاي النسخة. متأكد؟"
)
RESTORE_DONE = (
    title("تَـمَّـت الاِسْـتِـعَـادَة", "✅") + "\n"
    f"{BULLET} رجعت البيانات من النسخة بنجاح 🤍\n"
    f"{BULLET} نسخة الأمان من قبل الاستعادة: <code>{{pre}}</code>"
)
RESTORE_FAILED = f"{BULLET} فشلت الاستعادة، ورجّعت البيانات مثل ما جانت 🤍"
RESTORE_MEMORY = f"{BULLET} الاستعادة تحتاج قاعدة بيانات بملف 🌸"
BTN_RESTORE_GO = "♻️ استعادة"

# ── التقارير ────────────────────────────────────────
REPORT_GLOBAL = (
    title("تَـقْـرِيـر زَهـو", "📊") + "\n"
    f"<i>آخر {{days}} أيام</i>\n"
    f"{LINE}\n"
    f"{BULLET} المجموعات الفعّالة: <b>{{groups}}</b> ⋅ جديدة: <b>+{{new_groups}}</b>\n"
    f"{BULLET} المستخدمين: <b>{{users}}</b> ⋅ جدد: <b>+{{new_users}}</b>\n"
    f"{BULLET} بدوا محادثة بالخاص: <b>{{started}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} العقوبات: <b>{{punish}}</b> ⋅ السب المحذوف: <b>{{swear}}</b>\n"
    f"{BULLET} إجراءات الحماية: <b>{{guard}}</b> ⋅ الأخطاء من التشغيل: <b>{{errors}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} أنشط المجموعات:\n{{top}}"
)
REPORT_GROUP = (
    title("تَـقْـرِيـر {title}", "📊") + "\n"
    f"<i>آخر {{days}} أيام</i>\n"
    f"{LINE}\n"
    f"{BULLET} الأعضاء: <b>{{members}}</b> ⋅ جدد: <b>+{{new}}</b>\n"
    f"{BULLET} الأعضاء النشطين: <b>{{active}}</b>\n"
    f"{BULLET} الخبرة المكتسبة: <b>{{xp}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} العقوبات: <b>{{punish}}</b> ⋅ السب المحذوف: <b>{{swear}}</b>\n"
    f"{BULLET} إجراءات الحماية: <b>{{guard}}</b>\n"
    f"{LINE}\n"
    f"{BULLET} الأنشط بهالفترة:\n{{top}}"
)
REPORT_NONE = "    —"
EXPORT_SENT = f"{BULLET} دزيتلك ملف الأعضاء بالخاص 📩"
EXPORT_NEED_START = f"{BULLET} ما گدرت أدزلك بالخاص 🌸 ابدأ محادثة ويايه أول (<code>/start</code>) وارجع جرب"
EXPORT_CAPTION = f"{BULLET} أعضاء <b>{{title}}</b> ⋅ <b>{{n}}</b> عضو 📄"

# ── فحص النظام ──────────────────────────────────────
HEALTH = (
    title("فَـحْـص الـنِّـظَـام", "🩺") + "\n"
    f"{LINE}\n"
    f"{BULLET} قاعدة البيانات: {{db}} ⋅ الحجم: <b>{{size}}</b>\n"
    f"{BULLET} اتصال تيليجرام: {{tg}} ⋅ <b>{{ping}}</b>\n"
    f"{BULLET} المهام المجدولة: <b>{{jobs}}</b>\n"
    f"{BULLET} آخر نسخة احتياطية: <b>{{backup}}</b>\n"
    f"{BULLET} وقت التشغيل: <b>{{uptime}}</b> ⋅ الأخطاء: <b>{{errors}}</b>\n"
    f"{BULLET} الإصدارات: زهو <code>{{version}}</code> ⋅ بايثون <code>{{py}}</code> ⋅ PTB <code>{{ptb}}</code>"
)
HEALTH_OK = "✅ سليمة"
HEALTH_BAD = "❌ بيها مشكلة"

# ── المساعدين ──────────────────────────────────────
HELPER_ADDED = f"{BULLET} صار <code>{{id}}</code> مساعد للمطور ✨ (يشوف اللوحة والتقارير والفحص بس)"
HELPER_REMOVED = f"{BULLET} انشال <code>{{id}}</code> من المساعدين 🌸"
HELPER_BAD = f"{BULLET} اكتب ايدي الشخص بعد الأمر رجاءً 🌸 مثال: <code>رفع مساعد 123456789</code>"
HELPER_NOT_FOUND = f"{BULLET} هذا مو من المساعدين 🌸"
HELPERS_HEADER = title("مُـسَـاعِـدِيـن الـمُـطَـوِّر", "🧑‍💻") + f"\n{LINE}"
HELPERS_EMPTY = f"{BULLET} ماكو مساعدين لحد هسه 🌸"
DEV_ONLY = "هذا للمطور بس 🔐"

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
BTN_BROADCAST = "📢 إذاعة"
BTN_BACKUP = "💾 نسخة احتياطية"
BTN_REPORT = "📊 تقرير"
BTN_HEALTH = "🩺 فحص النظام"


# ── معلومات المجموعة والمنشئ ─────────────────────────
GROUP_INFO = (
    title("مَـعْـلُـومَـات الـمَـجْـمُـوعَـة", "🏡") + f"\n{LINE}\n"
    f"{BULLET} الاسم: <b>{{title}}</b>\n"
    f"{BULLET} الايدي: <code>{{id}}</code>\n"
    f"{BULLET} اليوزر: {{username}}\n"
    f"{BULLET} الأعضاء: <b>{{members}}</b> ⋅ المشرفين: <b>{{admins}}</b>\n"
    f"{BULLET} المنشئ: {{creator}}\n"
    f"{LINE}\n"
    f"{BULLET} زهو: {{state}}\n"
    f"{BULLET} الحماية: {{guard}} ⋅ الأقفال: <b>{{locks}}</b>\n"
    f"{BULLET} السب: {{swear}}\n"
    f"{BULLET} الاشتراك الإجباري: {{channels}}\n"
    f"{BULLET} صلاحيات زهو: {{rights}}"
)
GROUP_NO_USERNAME = "خاصة 🔒"
GROUP_CREATOR_HIDDEN = "مخفي 🌸"
GROUP_CHANNELS_NONE = "مطفي"
GROUP_CHANNELS_COUNT = "<b>{n}</b> قناة"
GROUP_RIGHTS_FULL = "✅ كاملة"
GROUP_RIGHTS_MISSING = "⚠️ ناقصها: {names}"
GROUP_BOT_NOT_ADMIN = "⚠️ مو مشرفة"
GROUP_STATES = {"on": "🟢 شغّالة", "paused": "⏸ موقوفة", "disabled": "⛔ معطّلة"}
BOT_RIGHT_NAMES = {
    "can_delete_messages": "حذف الرسائل",
    "can_restrict_members": "حظر المستخدمين",
    "can_invite_users": "دعوة المستخدمين",
    "can_pin_messages": "تثبيت الرسائل",
    "can_change_info": "تغيير المعلومات",
}
CREATOR_TEXT = title("مُـنْـشِـئ الـمَـجْـمُـوعَـة", "👑") + f"\n{LINE}\n{BULLET} {{mention}}"
CREATOR_HIDDEN = f"{BULLET} منشئ المجموعة مخفي 🌸"

# ── إنشاء رابط ─────────────────────────────────────
LINK_CREATED = (
    title("تَـمَّ إِنْـشَـاء الـرَّابِـط", "🔗") + f"\n{LINE}\n"
    "{link}\n"
    f"{BULLET} صار هذا رابط المجموعة الحالي ✨"
)
LINK_NEED_INVITE = f"{BULLET} أحتاج صلاحية «<b>دعوة المستخدمين</b>» حتى أسوي رابط 🔐"

# ── كليشة الايدي ───────────────────────────────────
# المتغيرات (مع صيغها البديلة) ← مفتاح القيمة
ID_TPL_VARS = {
    "الاسم": "name", "اليوزر": "username", "المعرف": "username", "الايدي": "id",
    "الرتبة": "rank", "الرتبه": "rank", "الرسائل": "messages", "التفاعل": "activity",
    "المجموعة": "group", "المجموعه": "group",
}
ID_TPL_HELP = (
    title("كَـلِـيـشَـة الايـدي", "🪪") + f"\n{LINE}\n"
    f"{BULLET} اكتب الكليشة بعد الأمر، وحط المتغيرات بين قوسين:\n"
    "<code>{الاسم}</code> <code>{اليوزر}</code> <code>{الايدي}</code> <code>{الرتبة}</code> "
    "<code>{الرسائل}</code> <code>{التفاعل}</code> <code>{المجموعة}</code>\n"
    f"{BULLET} مثال:\n"
    "<code>تعيين الايدي\n✨ {الاسم}\n🆔 {الايدي}\n🎖 {الرتبة}\n💌 {الرسائل}</code>"
)
ID_TPL_SET = f"{BULLET} انحفظت كليشة الايدي ✨ هاي معاينتها:"
ID_TPL_RESET = f"{BULLET} رجعت كليشة الايدي الأصلية 🌸"
ID_TPL_DEFAULT = f"{BULLET} المجموعة تستخدم الكليشة الأصلية ✨"
ID_TPL_CURRENT = f"{BULLET} الكليشة الحالية:\n<code>{{tpl}}</code>"
ID_TPL_BAD = f"{BULLET} الكليشة لازم تكون من 5 لـ 800 حرف، وبيها متغير واحد على الأقل مثل <code>{{الاسم}}</code> 🌸"

# ── الاشتراك الإجباري ───────────────────────────────
FSUB_NOTICE = f"{BULLET} {{mention}} حتى تكدر تكتب بالمجموعة، اشترك بالقناة أولاً 🤍 وبعدها اضغط «اشتركت»"
FSUB_BTN_JOIN = "📢 {title}"
FSUB_BTN_CHECK = "✅ اشتركت"
FSUB_OK = "تم التحقق، تكدر تكتب هسه 🤍"
FSUB_NOT_YET = "بعدك ما مشترك بكل القنوات 🌸"
FSUB_NOT_YOURS = "هذا الزر لصاحب الرسالة بس 🌸"
FSUB_ADDED = (
    title("تَـمَّ إِضَـافَـة الـقَـنَـاة", "📢") + f"\n{LINE}\n"
    f"{BULLET} القناة: <b>{{title}}</b>\n"
    f"{BULLET} هسه الأعضاء لازم يشتركون بيها حتى يكتبون (المشرفين مستثنين) 🌸"
)
FSUB_REMOVED = f"{BULLET} انشالت القناة <b>{{title}}</b> من الاشتراك الإجباري ✨"
FSUB_CLEARED = f"{BULLET} انطفى الاشتراك الإجباري وانشالت كل القنوات 🌸"
FSUB_NOT_FOUND = f"{BULLET} هاي القناة مو مضافة 🌸 شوف <code>القنوات</code>"
FSUB_EXISTS = f"{BULLET} هاي القناة مضافة من قبل ✨"
FSUB_LIMIT = f"{BULLET} أكثر شي {{n}} قنوات 🌸 احذف وحدة قبل لا تضيف"
FSUB_NEED_ARG = f"{BULLET} اكتب يوزر القناة أو ايديها 🌸 مثال: <code>اضف قناه @channel</code>"
FSUB_BAD_CHANNEL = f"{BULLET} ما لگيت هاي القناة 🌸 تأكد من اليوزر (@...) أو الايدي (-100...)"
FSUB_NOT_CHANNEL = f"{BULLET} هذا مو قناة 🌸 الاشتراك الإجباري للقنوات بس"
FSUB_BOT_NOT_ADMIN = f"{BULLET} لازم ترفعني مشرفة بالقناة أولاً حتى أكدر أتأكد من المشتركين 🔐"
FSUB_NO_LINK = f"{BULLET} القناة خاصة وما كدرت أسوي إلها رابط 🌸 انطيني صلاحية «دعوة المستخدمين» بالقناة"
FSUB_LIST_HEADER = title("قَـنَـوَات الاشْـتِـرَاك", "📢") + f"\n{LINE}"
FSUB_LIST_EMPTY = f"{BULLET} الاشتراك الإجباري مطفي، ماكو قنوات 🌸"
FSUB_LIST_ITEM = "▫️ <a href=\"{link}\">{title}</a> ⋅ <code>{id}</code>"

# ── التحميل (تيك توك + ساوند كلاود) ────────────────
DL_NEED_URL = f"{BULLET} حط الرابط بعد الأمر 🌸 مثال: <code>{{example}}</code>"
DL_BAD_URL = f"{BULLET} هذا مو رابط {{site}} 🌸"
DL_SITES = {"tiktok": "تيك توك", "soundcloud": "ساوند كلاود"}
DL_EXAMPLES = {"tiktok": "تيك https://vm.tiktok.com/...", "soundcloud": "ساوند https://soundcloud.com/..."}
DL_DOWNLOADING = f"{BULLET} دا أحمّل من {{site}} ⏳ ثواني وتوصلك..."
DL_TOO_LONG = f"{BULLET} المقطع طويل (<b>{{dur}}</b>)، الحد الأقصى {{limit}} 🌸"
DL_FAILED = f"{BULLET} ما گدرت أحمّله 🤍 يمكن الرابط خاص أو محذوف أو النت ضعيف"
DL_CAPTION_VIDEO = f"🎬 {{title}}\n{BULLET} طلبه: {{mention}}"
DL_CAPTION_AUDIO = f"🎧 <b>{{title}}</b>\n{BULLET} {{artist}} ⋅ ⏱ {{dur}}\n{BULLET} طلبها: {{mention}}"


# ── ردود السلام ────────────────────────────────────
GREET_OFF = (
    title("تَـمَّ إِيـقَـاف رُدُود الـسَّـلَام", "🔕") + f"\n{LINE}\n"
    f"{BULLET} زهو ما راح ترد على السلام والترحيب وصباح ومساء الخير وغيرها\n"
    f"{BULLET} الأوامر والحماية والأقفال والطرد والحظر كلها شغّالة عادي 🛡\n"
    f"{BULLET} حتى ترجعها: <code>تشغيل ردود السلام</code>"
)
GREET_ON = (
    title("تَـمَّ تَـشْـغِـيـل رُدُود الـسَّـلَام", "🔔") + f"\n{LINE}\n"
    f"{BULLET} رجعت زهو ترد على السلام والترحيب وصباح ومساء الخير 🤍"
)
GREET_ALREADY_OFF = f"{BULLET} ردود السلام موقوفة من قبل 🔕"
GREET_ALREADY_ON = f"{BULLET} ردود السلام شغّالة من قبل 🔔"


# ── حالة الأقفال (شنو مقفول وشنو مفتوح) ─────────────
LOCK_STATUS_HEADER = title("حَـالَـة الـمَـجْـمُـوعَـة", "🔐") + f"\n{LINE}"
LOCK_STATUS_LOCKED_HEAD = "🔒 <b>الأشياء الموقوفة:</b>"
LOCK_STATUS_LOCKED_ITEM = "  {emoji} تم إيقاف <b>{name}</b> ⋅ {mode}{vip}"
LOCK_STATUS_VIP_MARK = " ⋅ 🌟"
LOCK_STATUS_NONE_LOCKED = "  ✨ ماكو شي موقوف، كلشي مسموح"
LOCK_STATUS_OPEN_HEAD = "🔓 <b>الأشياء المسموحة:</b>"
LOCK_STATUS_SWEAR = "🤬 <b>السب:</b> {summary}"
LOCK_STATUS_FEATURES_OFF = "⚙️ <b>الميزات المعطّلة:</b> {names}"
LOCK_STATUS_FOOTER = (
    "<i>🌟 = المميز يكدر يرسلها حتى لو موقوفة ⋅ الباقي للمشرفين بس\n"
    "للتغيير: «قفل الصور» ، «فتح الصور» ، أو «الاقفال» للأزرار</i>"
)


# ── مالك زهو ───────────────────────────────────────
DEV_JOINED = (
    title("نَـوَّرْت يَـا مَـالِـك زَهْـو", "👑") + f"\n{LINE}\n"
    f"{BULLET} {{mention}} مطوّر زهو ومالكها دخل المجموعة 🤍\n"
    f"{BULLET} إله كل الصلاحيات هنا: الأوامر والعقوبات والإعدادات 🛡"
)


# ── الصلاحيات المخصصة ──────────────────────────────
CAP_REVOKED = f"{BULLET} صلاحية «<b>{{cap}}</b>» مسحوبة منك بهاي المجموعة 🌸"
PERM_HINT = f"{BULLET} تكدر تعدل صلاحياته من الأزرار جوه 👇"
PERM_PANEL = (
    title("الـصَّـلَاحِـيَّـات", "🎛") + f"\n{LINE}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    f"{BULLET} ✅ مسموح ⋅ ▫️ ممنوع ⋅ ✏️ مخصص (مو حسب الرتبة)\n"
    f"{BULLET} اضغط على أي صلاحية حتى تشغلها أو تطفيها"
)
PERM_OF = f"{BULLET} صلاحيات {{mention}}"
PERM_BTN_RESET = "↺ حسب الرتبة"
PERM_MINE = (
    title("صَـلَاحِـيَّـاتِـي", "🎛") + f"\n{LINE}\n"
    f"{BULLET} الرتبة: {{rank}}\n"
    f"{BULLET} ✅ تكدر: {{on}}\n"
    f"{BULLET} ▫️ ما تكدر: {{off}}"
)
PERM_NOT_ALLOWED = "تكدر تعدل صلاحيات اللي رتبتهم أقل منك بس 🌸"
PERM_PROTECTED = "هذا الشخص محمي، صلاحياته ما تتغير 🛡"
PERM_YOU_LACK = "ما تكدر تنطي أو تسحب صلاحية انت ما عندك 🌸"
PERM_RESET_DONE = "رجعت صلاحياته حسب رتبته ✨"
RANK_TG_PROMOTED = f"{BULLET} وصار مشرف بتيليجرام كمان (حذف، حظر، تثبيت، دعوة) 🛡"
RANK_TG_FAILED = (f"{BULLET} صار مشرف بزهو، بس ما كدرت أرفعه مشرف بتيليجرام 🌸 "
                  "أحتاج صلاحية «<b>إضافة مشرفين</b>»")
RANK_TG_DEMOTED = f"{BULLET} وانشال إشرافه بتيليجرام كمان 🔻"
RANK_ALL_REVOKED = f"{BULLET} انسحبت كل صلاحياته، صار عضو عادي ✨"


# ── المسح والمنع والتنظيف ──────────────────────────
CLEAR_RANK_DONE = f"{BULLET} نزلت <b>{{n}}</b> من {{what}} لأعضاء، وانسحبت صلاحياتهم ✨"
CLEAR_RANK_EMPTY = f"{BULLET} ماكو {{what}} بالمجموعة 🌸"
CLEAR_ALL_CONFIRM = (
    title("مَـسْـح الـرُّتَـب", "⚠️") + f"\n{LINE}\n"
    f"{BULLET} راح أنزل <b>كل الرتب</b> اللي تحت رتبتك ({{rank}}) لأعضاء، وأسحب كل صلاحياتهم\n"
    f"{BULLET} متأكد؟"
)
BTN_CONFIRM_CLEAR = "✅ اي، امسح"
BTN_CANCEL_CLEAR = "✖️ لا، الغي"
CLEAR_ALL_CANCELLED = f"{BULLET} تم الإلغاء، محد تغيرت رتبته 🌸"
CLEAR_ALL_NEED_RANK = "مسح الكل يحتاج رتبة مالك أو أعلى 🌸"
CLEAR_ALL_DONE = title("تَـمَّ مَـسْـح الـرُّتَـب", "🧹") + f"\n{BULLET} نزل <b>{{n}}</b> شخص لعضو عادي ✨"
CLEAR_LIST_DONE = f"{BULLET} انفكت القيود عن <b>{{n}}</b> من {{what}} ✨"
CLEAR_LIST_EMPTY = f"{BULLET} ماكو {{what}} حالياً 🌸"
PURGE_HINT = f"{BULLET} اكتب العدد (مثل <code>مسح 50</code>) أو رد على رسالة بكلمة <code>مسح</code> 🌸"
PURGE_DONE = f"🧹 انمسحت <b>{{n}}</b> رسالة"
FILTER_HINT = (f"{BULLET} رد على ملصق أو متحركة أو صورة أو فيديو بكلمة <code>منع</code>، "
               "أو اكتب: <code>منع الكلمة</code> 🌸")
FILTER_ADDED = title("تَـمَّ الـمَـنْـع", "⛔") + f"\n{BULLET} {{what}}\n{BULLET} أي أحد يرسله تنمسح رسالته (المشرفين مستثنين)"
FILTER_EXISTS = f"{BULLET} هذا ممنوع من قبل ⛔"
FILTER_REMOVED = f"{BULLET} رجع <b>{{what}}</b> مسموح ✨"
FILTER_NOT_FOUND = f"{BULLET} هذا مو موجود بقائمة المنع 🌸"
FILTER_NOTICE = f"{BULLET} {{mention}} عيني، هذا ممنوع بالمجموعة ⛔ رسالتك انمسحت"
FILTER_LIST_HEADER = title("قَـائِـمَـة الـمَـنْـع", "⛔") + f"\n{LINE}"
FILTER_LIST_EMPTY = f"{BULLET} ماكو شي ممنوع 🌸"
FILTER_KINDS = {"sticker": "🧸 ملصقات", "animation": "🎞 متحركات", "photo": "🖼 صور", "video": "🎬 فيديوهات",
                "word": "✍️ كلمات"}
FILTER_CLEARED = f"{BULLET} انمسحت قائمة المنع (<b>{{n}}</b>) ✨"
BOTS_HEADER = title("الـبُـوتَـات", "🤖") + f"\n{LINE}"
BOTS_EMPTY = f"{BULLET} ما لگيت بوتات غيري 🌸"
BOTS_FOOTER = "<i>🛡 = مشرف ⋅ تيليجرام ما يخلي البوتات تشوف كل الأعضاء، فأعرض اللي أعرفهم بس</i>"
BOTS_KICKED = f"{BULLET} انطرد <b>{{n}}</b> بوت 🤖 ⋅ ما كدرت على <b>{{failed}}</b> (مشرفين ما رفعتهم آني)"
DELETED_SCANNING = f"{BULLET} دا أفحص الأعضاء عن الحسابات المحذوفة ⏳"
DELETED_BUSY = f"{BULLET} الفحص شغّال هسه، انتظره يخلص 🌸"
DELETED_DONE = (
    title("طَـرْد الـمَـحْـذُوفِـيـن", "👻") + f"\n{LINE}\n"
    f"{BULLET} فحصت: <b>{{checked}}</b> عضو\n"
    f"{BULLET} انطرد: <b>{{n}}</b> حساب محذوف\n"
    "<i>أفحص الأعضاء اللي أعرفهم بس (تيليجرام ما يعطي البوتات قائمة كاملة)</i>"
)
LIFT_ALL_DONE = (
    title("تَـمَّ رَفْـع الـقُـيُـود", "🕊") + f"\n{LINE}\n"
    f"{BULLET} العضو: {{mention}}\n"
    f"{BULLET} انفك عنه الحظر والكتم والتقييد\n"
    f"{BULLET} بواسطة: {{actor}}"
)
RIGHT_DELETE = "حذف الرسائل"


# ── صورة واسم وبايو المجموعة ───────────────────────
CHAT_INFO_NEED_RIGHT = f"{BULLET} أحتاج صلاحية «<b>تغيير معلومات المجموعة</b>» حتى أكدر أغيرها 🔐"
CHAT_INFO_FAILED = f"{BULLET} ما كدرت أغيرها 🌸 تأكد من صلاحياتي وجرب مرة ثانية"
CHAT_PHOTO_ASK = f"{BULLET} ارسل الصورة الجديدة للمجموعة هسه 🖼\n{BULLET} للإلغاء اكتب: <code>الغاء</code>"
CHAT_PHOTO_NEED = f"{BULLET} أنتظر صورة 🖼 ارسلها، أو اكتب <code>الغاء</code>"
CHAT_PHOTO_TOO_BIG = f"{BULLET} الصورة كبيرة هوايه 🌸 اختار وحدة أصغر من 10 ميگا"
CHAT_PHOTO_DONE = title("تَـغَـيَّـرَت صُـورَة الـمَـجْـمُـوعَـة", "🖼") + f"\n{BULLET} بواسطة: {{actor}}"
CHAT_TITLE_ASK = f"{BULLET} اكتب الاسم الجديد للمجموعة ✍️\n{BULLET} للإلغاء اكتب: <code>الغاء</code>"
CHAT_TITLE_BAD = f"{BULLET} الاسم لازم يكون من 1 لـ {{n}} حرف 🌸"
CHAT_TITLE_DONE = (title("تَـغَـيَّـر اسْـم الـمَـجْـمُـوعَـة", "✏️") + f"\n{BULLET} الاسم الجديد: <b>{{title}}</b>"
                   f"\n{BULLET} بواسطة: {{actor}}")
CHAT_BIO_ASK = f"{BULLET} اكتب البايو الجديد للمجموعة 📝\n{BULLET} للإلغاء اكتب: <code>الغاء</code>"
CHAT_BIO_BAD = f"{BULLET} البايو أطول من {{n}} حرف 🌸 اختصره شوية"
CHAT_BIO_SAME = f"{BULLET} هذا نفس البايو الحالي ✨"
CHAT_BIO_DONE = (title("تَـغَـيَّـر بَـايُـو الـمَـجْـمُـوعَـة", "📝") + f"\n{BULLET} البايو: <i>{{bio}}</i>"
                 f"\n{BULLET} بواسطة: {{actor}}")
CHAT_TEXT_NEED = f"{BULLET} أنتظر نص 🌸 اكتبه، أو اكتب <code>الغاء</code>"


# ── كشف عضو ────────────────────────────────────────
INSPECT = (
    title("كَـشْـف عُـضْـو", "🔎") + f"\n{LINE}\n"
    "👤 الاسم: {name}\n"
    "🆔 الايدي: <code>{id}</code>\n"
    "🔗 اليوزر: {username}\n"
    "🪪 النوع: {kind}\n"
    f"{LINE}\n"
    "🎖 الرتبة: {rank}\n"
    "🛡 بتيليجرام: {tg}\n"
    "{custom}"
    f"{LINE}\n"
    "💬 الرسائل: <b>{messages}</b> ⋅ الترتيب: <b>{position}</b>\n"
    "⚡ التفاعل: {activity}\n"
    "⭐ المستوى: <b>{level}</b> ({xp} خبرة) ⋅ 🏆 فوز بالألعاب: <b>{wins}</b>\n"
    "🤍 الشكر: <b>{thanks}</b> ⋅ 📊 التقييم: {rating} ⋅ ✨ {good} ⋅ 👎🏻 {bad}\n"
    "{economy}"
    f"{LINE}\n"
    "⚠️ التحذيرات: <b>{warns}/{limit}</b>\n"
    "🤬 السب: <b>{swear}</b> مرة{swear_detail} ⋅ آخر 7 أيام: <b>{swear_week}</b>\n"
    "🚫 العقوبات: {punish}\n"
    "⛓ الحالية: {active}\n"
    f"{LINE}\n"
    "📅 أول ظهور: <code>{first}</code> ⋅ 🕐 آخر تفاعل: <code>{last}</code>\n"
    "👋 ضافه: {added}"
)
INSPECT_KIND_USER = "حساب شخصي 🙋"
INSPECT_KIND_BOT = "بوت 🤖"
INSPECT_TG = {
    "tg_owner": "صاحب المجموعة 🏛", "tg_admin": "مشرف 🛡", "tg_member": "عضو ✅",
    "tg_restricted": "مقيّد ⛓", "tg_muted": "مكتوم 🔇", "tg_left": "طالع من المجموعة 🚪",
    "tg_banned": "محظور 🚫", "unknown": "—",
}
INSPECT_CUSTOM_PERMS = "🎛 صلاحيات مخصصة: {perms}\n"
INSPECT_ECONOMY = "💰 الرصيد: <b>{balance}</b>\n"
INSPECT_NO_RATING = "ماكو"
INSPECT_SWEAR_LEVELS = {1: "🟢", 2: "🟠", 3: "🔴"}
INSPECT_PUNISH_KINDS = {"ban": "حظر", "kick": "طرد", "mute": "كتم", "restrict": "تقييد"}
INSPECT_CLEAN = "سجله نظيف ✨"
INSPECT_NO_ACTIVE = "ماكو ✅"
INSPECT_SELF_JOINED = "دخل بنفسه (بالرابط)"
INSPECT_UNKNOWN = "—"


# ── مراقبة «ش» (مخفية) ─────────────────────────────
WATCH_ON = "تم التفعيل ✅"
WATCH_OFF = "تم الإيقاف ▫️"
WATCH_ALERT = (
    title("تَـنْـبِـيـه أَمْـنِـي", "🚨") + f"\n{LINE}\n"
    f"{BULLET} {{actor}} طرد/حظر <b>{{n}}</b> أعضاء خلال أقل من 10 دقايق\n"
    f"{BULLET} نزلت رتبته لعضو وانسحبت صلاحياته للتحقيق بالموضوع 🔍\n"
    f"{BULLET} {{owner}} بس انت تكدر ترجّع رتبته"
)
WATCH_NO_OWNER = "صاحب المجموعة"
WATCH_LOCKED = f"{BULLET} {{mention}} رتبته موقوفة للتحقيق 🔍 بس صاحب المجموعة يكدر يرفعه"
