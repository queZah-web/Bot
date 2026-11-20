"""متجر زهو: عناصر شكلية بس (ألقاب وإطارات) — ما تعطي أي صلاحيات."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    key: str
    kind: str      # title | frame | custom
    name: str
    price: int
    left: str = ""
    right: str = ""


ITEMS: tuple[Item, ...] = (
    Item("t_night", "title", "🌙 سهران", 200),
    Item("t_heart", "title", "🤍 قلب طيب", 250),
    Item("t_star", "title", "⭐ نجم المجموعة", 300),
    Item("t_rose", "title", "🌹 وردة المجموعة", 300),
    Item("t_lion", "title", "🦁 شجاع", 400),
    Item("t_crown", "title", "👑 ملكي", 800),
    Item("t_diamond", "title", "💎 ماسي", 1500),
    Item("f_stars", "frame", "✧ نجوم ✧", 250, "✧ ", " ✧"),
    Item("f_flowers", "frame", "❀ ورود ❀", 250, "❀ ", " ❀"),
    Item("f_hearts", "frame", "♡ قلوب ♡", 300, "♡ ", " ♡"),
    Item("f_brackets", "frame", "『 أنيق 』", 300, "『 ", " 』"),
    Item("f_wings", "frame", "꧁ أجنحة ꧂", 500, "꧁ ", " ꧂"),
    Item("custom", "custom", "✏️ لقب مخصص", 1000),
)
ITEM_MAP = {i.key: i for i in ITEMS}
SLOT = {"title": "title_item", "frame": "frame_item", "custom": "custom_title"}
