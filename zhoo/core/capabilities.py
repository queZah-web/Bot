"""الصلاحيات المخصصة لكل شخص: كل رتبة إلها صلاحيات افتراضية، والأعلى منه يگدر يشيل أو يضيف.

مثال: مدير بس بدون حظر ، أو مميز يگدر يرسل ملفات.
- الافتراضي = رتبة الشخص ≥ أقل رتبة للأمر (أو للقفل).
- المخصص يغلب الافتراضي: «سماح» يضيف صلاحية، «منع» يشيلها.
- أي تنزيل لعضو يمسح كل المخصص.
"""
from __future__ import annotations

from zhoo.core.ranks import Rank

# الصلاحية ← (الاسم، الإيموجي، أقل رتبة افتراضية)
CAPS: dict[str, tuple[str, str, Rank]] = {
    "ban": ("الحظر", "🚫", Rank.MANAGER),
    "kick": ("الطرد", "👢", Rank.SUPERVISOR),
    "mute": ("الكتم", "🔇", Rank.ADMIN),
    "restrict": ("التقييد", "⛓", Rank.ADMIN),
    "warn": ("التحذير", "⚠️", Rank.ADMIN),
    "clean": ("مسح الرسائل", "🧹", Rank.ADMIN),
    "filters": ("المنع", "⛔", Rank.ADMIN),
    "locks": ("الأقفال", "🔒", Rank.ADMIN),
    "promote": ("الرفع والتنزيل", "🎖", Rank.ADMIN),
    "settings": ("الإعدادات", "⚙️", Rank.MANAGER),
    "media": ("الوسائط المقفولة", "🖼", Rank.VIP),
    "files": ("الملفات والصوتيات", "📁", Rank.ADMIN),
    "links": ("الروابط والتوجيه", "🔗", Rank.ADMIN),
}

# الأمر ← الصلاحية اللي يحتاجها
COMMAND_CAP: dict[str, str] = {
    "ban": "ban", "unban": "ban", "lift_all": "ban", "clear_banned": "ban", "clear_muted": "mute",
    "kick": "kick", "kick_bots": "kick", "kick_deleted": "kick",
    "mute": "mute", "unmute": "mute",
    "restrict": "restrict", "unrestrict": "restrict",
    "warn": "warn", "clear_warns": "warn",
    "purge": "clean",
    "filter_add": "filters", "filter_del": "filters", "filter_clear": "filters",
    "lock_one": "locks", "unlock_one": "locks", "lock_all": "locks", "unlock_all": "locks", "locks_panel": "locks",
    "settings": "settings", "rules_set": "settings", "rules_del": "settings", "link_set": "settings",
    "link_del": "settings", "link_create": "settings", "welcome_set": "settings", "welcome_on": "settings",
    "welcome_off": "settings", "welcome_reset": "settings", "goodbye_set": "settings", "goodbye_on": "settings",
    "goodbye_off": "settings", "goodbye_reset": "settings", "feature_on": "settings", "feature_off": "settings",
    "greet_on": "settings", "greet_off": "settings", "id_tpl_set": "settings", "id_tpl_reset": "settings",
    "chat_photo": "settings", "chat_title": "settings", "chat_bio": "settings",
}
for _r in ("primary_owner", "owner", "general_manager", "manager", "supervisor", "admin", "vip"):
    COMMAND_CAP[f"promote_{_r}"] = "promote"
    COMMAND_CAP[f"demote_{_r}"] = "promote"
COMMAND_CAP["demote"] = "promote"
COMMAND_CAP["promote_suspect"] = COMMAND_CAP["demote_suspect"] = "promote"

# القفل ← الصلاحية اللي تتجاوزه (الأقفال الباقية للمشرفين بس)
LOCK_CAP: dict[str, str] = {
    **{k: "media" for k in ("photos", "videos", "gifs", "stickers", "animated_stickers", "premium_stickers",
                            "premium_emoji", "text", "long", "edit", "edit_media", "reactions")},
    **{k: "files" for k in ("files", "voice", "audio", "contacts", "locations", "polls")},
    **{k: "links" for k in ("links", "usernames", "tag", "forward", "inline")},
}


def default_on(cap: str, rank: Rank) -> bool:
    return rank >= CAPS[cap][2]


def decide(default: bool, cap: str, allow: frozenset[str], deny: frozenset[str]) -> bool:
    if cap in deny:
        return False
    return default or cap in allow


async def has_cap(svc, chat_id: int, user_id: int, cap: str, default: bool) -> bool:
    """القرار النهائي: مطور زهو دائماً نعم، وإلا الافتراضي + المخصص."""
    if svc.perms.is_developer(user_id):
        return True
    allow, deny = await svc.member_perms.get(chat_id, user_id)
    return decide(default, cap, allow, deny)
