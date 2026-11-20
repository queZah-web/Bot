"""سجل الأوامر العربية ومحلّلها.

كل أمر يُسجَّل مرة واحدة مع: أسمائه، قسمه، أقل رتبة مطلوبة، ووصفه.
القائمة التفاعلية تُبنى تلقائياً من هذا السجل، فما في تكرار.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Awaitable, Callable

from zhoo.core.normalize import normalize, split_tokens
from zhoo.core.ranks import Rank

if TYPE_CHECKING:
    from zhoo.core.context import CommandContext

Handler = Callable[["CommandContext"], Awaitable[None]]


@dataclass
class Command:
    key: str
    names: tuple[str, ...]
    section: str
    min_rank: Rank
    description: str
    handler: Handler
    usage: str = ""             # مثل: «بالرد/اليوزر/الايدي»
    where: str = "group"        # group | private | any
    show_in_help: bool = True
    order: int = 0
    args: str = "none"          # none | target | punish (هدف + مدة/سبب) | text
    helpers: bool = False       # يسمح لمساعدين المطور (مع إن الرتبة مطور)

    @property
    def display_name(self) -> str:
        return self.names[0]


@dataclass
class ParsedCommand:
    command: Command
    args: list[str]
    raw_args: str


@dataclass
class CommandRegistry:
    commands: list[Command] = field(default_factory=list)
    _index: dict[tuple[str, ...], Command] = field(default_factory=dict)
    _max_words: int = 1

    def add(self, cmd: Command) -> Command:
        for name in cmd.names:
            words = tuple(normalize(name).split())
            if not words:
                raise ValueError(f"اسم أمر فارغ: {cmd.key}")
            if words in self._index and self._index[words] is not cmd:
                raise ValueError(f"اسم أمر مكرر: {name} ({cmd.key} / {self._index[words].key})")
            self._index[words] = cmd
            self._max_words = max(self._max_words, len(words))
        self.commands.append(cmd)
        return cmd

    def command(self, key: str, names: tuple[str, ...] | list[str] | str, *, section: str,
                description: str, min_rank: Rank = Rank.MEMBER, usage: str = "",
                where: str = "group", show_in_help: bool = True, order: int = 0,
                args: str = "none", helpers: bool = False):
        """مزخرف لتسجيل أمر."""
        if isinstance(names, str):
            names = (names,)

        def deco(func: Handler) -> Handler:
            self.add(Command(key, tuple(names), section, min_rank, description, func,
                             usage, where, show_in_help, order, args, helpers))
            return func
        return deco

    def parse(self, text: str, *, has_text_mention: bool = False,
              has_reply: bool = False) -> ParsedCommand | None:
        """يطابق بداية الرسالة مع أطول اسم أمر. الكلمات داخل الجملة لا تُعتبر أمراً.

        الأمر اللي ما ياخذ إضافات لازم يكون الرسالة كلها، حتى «زهو شلونك» ما تنحسب أمر.
        """
        if not text or len(text) > 4096:
            return None
        if text.startswith("/") and len(text) > 1 and not text[1].isascii():
            text = text[1:]  # «/فتح زهو» = «فتح زهو»
        tokens = split_tokens(text)
        if not tokens:
            return None
        norm = [normalize(t[0]) for t in tokens[: self._max_words]]
        for n in range(min(len(norm), self._max_words), 0, -1):
            cmd = self._index.get(tuple(norm[:n]))
            if cmd is None:
                continue
            rest = text[tokens[n - 1][2]:].strip() if n < len(tokens) else ""
            if rest and not _accepts(cmd.args, rest, has_text_mention, has_reply):
                return None
            return ParsedCommand(cmd, rest.split(), rest)
        return None

    def by_section(self, section: str) -> list[Command]:
        cmds = [c for c in self.commands if c.section == section and c.show_in_help]
        return sorted(cmds, key=lambda c: (c.order, c.min_rank))

    def get(self, key: str) -> Command | None:
        return next((c for c in self.commands if c.key == key), None)


_TARGET_ARG = re.compile(r"^(@[A-Za-z][A-Za-z0-9_]{3,31}|\d{5,15})(\s|$)")


def _accepts(mode: str, rest: str, has_text_mention: bool, has_reply: bool = False) -> bool:
    if mode == "text":
        return True
    if mode == "punish":  # بالرد: أي إضافة = مدة/سبب. بدون رد: لازم يبدأ بهدف
        return has_reply or has_text_mention or bool(_TARGET_ARG.match(rest))
    if mode == "target":
        return has_text_mention or bool(_TARGET_ARG.match(rest))
    return False


registry = CommandRegistry()
