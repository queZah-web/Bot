"""الأقسام والأزرار التفاعلية.

صيغة بيانات الأزرار (أقل من 64 بايت):
  h:<uid>:<section>   قائمة الأوامر (uid = صاحب القائمة، ما أحد غيره يكدر يضغط)
  o:<action>          مركز المالك (للمطور فقط)
  s:<action>          شاشة البداية بالخاص
"""
from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup

from zhoo.core import texts as T
from zhoo.core.commands import Command, CommandRegistry
from zhoo.core.fmt import esc
from zhoo.core.ranks import RANK_NAMES, Rank


@dataclass(frozen=True)
class Section:
    key: str
    title: str
    emoji: str
    phase: int | None = None             # None = جاهز، رقم = مرحلة قادمة
    planned: tuple[str, ...] = ()
    min_rank: Rank = Rank.MEMBER         # من يشوف زر القسم أصلاً

    @property
    def label(self) -> str:
        suffix = " 🔜" if self.phase else ""
        return f"{self.emoji} {self.title}{suffix}"


SECTIONS: tuple[Section, ...] = (
    Section("general", "العامة", "🧭"),
    Section("ranks", "الرتب والإدارة", "👥"),
    Section("punish", "العقوبات", "⛔"),
    Section("protect", "الحماية", "🛡"),
    Section("locks", "القفل والفتح", "🔒"),
    Section("group", "إعدادات المجموعة", "⚙️"),
    Section("welcome", "الترحيب والتوديع", "👋"),
    Section("replies", "الردود والاختصارات", "💬"),
    Section("social", "التفاعل", "🤝"),
    Section("games", "الألعاب", "🎮"),
    Section("levels", "المستويات", "📈"),
    Section("economy", "الاقتصاد", "💰", 8, ("نقاطي", "المكافأة اليومية", "المتجر", "تحويل")),
    Section("dev", "المطور", "💎", None, (), Rank.DEVELOPER),
)
SECTION_MAP = {s.key: s for s in SECTIONS}


def _rows(buttons: list[B], per_row: int = 2) -> list[list[B]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def help_main_keyboard(uid: int, rank: Rank, *, private: bool = False) -> InlineKeyboardMarkup:
    buttons = [B(s.label, callback_data=f"h:{uid}:{s.key}") for s in SECTIONS if rank >= s.min_rank]
    rows = _rows(buttons)
    if private:
        rows.append([B(T.BTN_HOME, callback_data="s:home")])
    else:
        rows.append([B(T.BTN_CLOSE, callback_data=f"h:{uid}:close")])
    return InlineKeyboardMarkup(rows)


def section_keyboard(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        B(T.BTN_BACK, callback_data=f"h:{uid}:main"),
        B(T.BTN_CLOSE, callback_data=f"h:{uid}:close"),
    ]])


def _command_line(cmd: Command, show_rank: bool) -> str:
    line = f"▫️ <code>{esc(cmd.display_name)}</code>"
    if cmd.usage:
        line += f" ‹ {esc(cmd.usage)} ›"
    line += f"\n    ↫ {esc(cmd.description)}"
    if show_rank and cmd.min_rank > Rank.MEMBER:
        line += f"  <i>({RANK_NAMES[cmd.min_rank]}+)</i>"
    return line


def section_text(section: Section, registry: CommandRegistry, rank: Rank, *, private: bool) -> str:
    header = T.title(section.title, section.emoji) + f"\n{T.LINE}\n"
    if section.phase:
        planned = "\n".join(f"   ▫️ {esc(p)}" for p in section.planned)
        return header + T.HELP_SOON.format(phase=section.phase, planned=planned)

    cmds = registry.by_section(section.key)
    if private:
        visible, locked = cmds, []
    else:
        visible = [c for c in cmds if rank >= c.min_rank]
        locked = [c for c in cmds if rank < c.min_rank]

    if not visible:
        body = T.NO_COMMANDS_FOR_RANK
    else:
        body = "\n".join(_command_line(c, show_rank=private) for c in visible)
    text = header + body
    if locked:
        text += T.HELP_LOCKED_HINT.format(count=len(locked))
    text += T.HELP_USAGE_HINT
    if section.key == "punish":
        text += T.HELP_DURATION_HINT
    elif section.key == "locks":
        text += T.HELP_LOCK_TYPES
    elif section.key == "welcome":
        text += "\n" + T.TEMPLATE_VARS
    return text


def start_keyboard(bot_username: str, is_developer: bool) -> InlineKeyboardMarkup:
    add_url = (
        f"https://t.me/{bot_username}?startgroup=zhoo"
        "&admin=change_info+delete_messages+restrict_members+invite_users+pin_messages+manage_chat"
    )
    rows = [
        [B(T.BTN_ADD, url=add_url)],
        [B(T.BTN_COMMANDS, callback_data="s:help"), B(T.BTN_ABOUT, callback_data="s:about")],
    ]
    if is_developer:
        rows.append([B(T.BTN_OWNER, callback_data="o:main")])
    return InlineKeyboardMarkup(rows)


def back_to_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[B(T.BTN_HOME, callback_data="s:home")]])


def owner_keyboard(maintenance: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [B(T.BTN_REFRESH, callback_data="o:main"),
         B(T.BTN_MAINT_OFF if maintenance else T.BTN_MAINT_ON, callback_data="o:maint")],
        [B(T.BTN_AUDIT, callback_data="o:audit"), B(T.BTN_GROUPS, callback_data="o:groups")],
        [B(T.BTN_HOME, callback_data="s:home")],
    ])


def owner_sub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[B(T.BTN_BACK, callback_data="o:main")]])
