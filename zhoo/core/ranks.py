"""الرتب وقواعد تغييرها — مكان واحد مركزي لكل منطق الرتب."""
from __future__ import annotations

from enum import IntEnum


class Rank(IntEnum):
    MEMBER = 0           # العضو
    VIP = 10             # المميز
    ADMIN = 20           # الأدمن
    SUPERVISOR = 30      # المشرف
    MANAGER = 40         # المدير
    GENERAL_MANAGER = 50 # المنشئ (كان اسمه «مدير عام»، نفس القيمة بالقاعدة)
    OWNER = 60           # المالك
    PRIMARY_OWNER = 65   # المالك الأساسي (يرفعه صاحب المجموعة بس)
    CREATOR = 70         # صاحب المجموعة (منشئها في تيليجرام — تلقائي)
    DEVELOPER = 100      # مطور البوت (OWNER_ID — تلقائي)


RANK_NAMES: dict[Rank, str] = {
    Rank.MEMBER: "عضو",
    Rank.VIP: "مميز",
    Rank.ADMIN: "أدمن",
    Rank.SUPERVISOR: "مشرف",
    Rank.MANAGER: "مدير",
    Rank.GENERAL_MANAGER: "منشئ",
    Rank.OWNER: "مالك",
    Rank.PRIMARY_OWNER: "مالك أساسي",
    Rank.CREATOR: "صاحب المجموعة",
    Rank.DEVELOPER: "مطور زهو",
}

RANK_EMOJI: dict[Rank, str] = {
    Rank.MEMBER: "👤",
    Rank.VIP: "⭐",
    Rank.ADMIN: "🔰",
    Rank.SUPERVISOR: "🛡",
    Rank.MANAGER: "💼",
    Rank.GENERAL_MANAGER: "🎖",
    Rank.OWNER: "🔱",
    Rank.PRIMARY_OWNER: "👑",
    Rank.CREATOR: "🏛",
    Rank.DEVELOPER: "💎",
}

# الرتب التي تُمنح بالأوامر (المنشئ والمطور تلقائيان ولا يُمنحان)
ASSIGNABLE: tuple[Rank, ...] = (
    Rank.PRIMARY_OWNER,
    Rank.OWNER,
    Rank.GENERAL_MANAGER,
    Rank.MANAGER,
    Rank.SUPERVISOR,
    Rank.ADMIN,
    Rank.VIP,
)

PROTECTED: frozenset[Rank] = frozenset({Rank.CREATOR, Rank.DEVELOPER})

# صيغة الجمع لعرض القوائم
RANK_PLURALS: dict[Rank, str] = {
    Rank.PRIMARY_OWNER: "المالكين الأساسيين",
    Rank.OWNER: "المالكين",
    Rank.GENERAL_MANAGER: "المنشئين",
    Rank.MANAGER: "المدراء",
    Rank.SUPERVISOR: "المشرفين",
    Rank.ADMIN: "الأدمنية",
    Rank.VIP: "المميزين",
}


def rank_label(rank: Rank | int) -> str:
    rank = Rank(rank)
    return f"{RANK_EMOJI[rank]} {RANK_NAMES[rank]}"


def coerce_rank(value: int) -> Rank:
    """يحول قيمة مخزنة إلى رتبة صالحة (أي قيمة غريبة تُعتبر عضو)."""
    try:
        rank = Rank(int(value))
    except (ValueError, TypeError):
        return Rank.MEMBER
    return rank if rank in ASSIGNABLE else Rank.MEMBER


class RankDecision:
    OK = "ok"
    SELF = "self"
    PROTECTED = "protected"
    TARGET_HIGHER = "target_higher"
    CANT_GRANT = "cant_grant"
    SAME = "same"
    BELOW_FLOOR = "below_floor"


def check_rank_change(
    actor: Rank,
    target_effective: Rank,
    target_floor: Rank,
    new_rank: Rank,
    *,
    is_self: bool,
) -> str:
    """يقرر هل يُسمح بتغيير الرتبة.

    actor: رتبة المنفذ الفعلية.
    target_effective: رتبة المستهدف الفعلية الحالية.
    target_floor: أقل رتبة ممكنة للمستهدف بسبب تيليجرام (أدمن تيليجرام = أدمن على الأقل).
    new_rank: الرتبة المطلوبة (عضو = تنزيل).
    """
    if is_self:
        return RankDecision.SELF
    if target_effective in PROTECTED:
        return RankDecision.PROTECTED
    if target_effective >= actor:
        return RankDecision.TARGET_HIGHER
    if new_rank != Rank.MEMBER and (new_rank not in ASSIGNABLE or new_rank >= actor):
        return RankDecision.CANT_GRANT
    if new_rank == target_effective:
        return RankDecision.SAME
    if new_rank < target_floor:
        return RankDecision.BELOW_FLOOR
    return RankDecision.OK
