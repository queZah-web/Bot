"""شاشات مشتركة تُستخدم من الأوامر النصية ومن الأزرار."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from zhoo import __version__
from zhoo.core import texts as T
from zhoo.core.context import Services
from zhoo.core.fmt import duration, esc
from zhoo.core.ranks import Rank, rank_label


def help_main_text(rank: Rank) -> str:
    return T.HELP_MAIN.format(rank=rank_label(rank))


async def about_text(svc: Services) -> str:
    return T.ABOUT.format(
        version=__version__,
        groups=await svc.groups.count_active(),
        users=await svc.users.count(),
        uptime=duration(time.time() - svc.started_at),
    )


async def owner_panel_text(svc: Services) -> str:
    return T.OWNER_PANEL.format(
        active=await svc.groups.count_active(),
        groups=await svc.groups.count_all(),
        users=await svc.users.count(),
        uptime=duration(time.time() - svc.started_at),
        version=__version__,
        maintenance=T.MAINT_STATE_ON if svc.maintenance else T.MAINT_STATE_OFF,
        errors=svc.error_count,
    )


def _ts(value: int) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%m-%d %H:%M")


async def audit_text(svc: Services, limit: int = 12) -> str:
    rows = await svc.audit.recent(limit)
    if not rows:
        return f"{T.AUDIT_HEADER}\n{T.AUDIT_EMPTY}"
    lines = []
    for r in rows:
        mark = "✅" if r["result"] == "ok" else "⚠️"
        lines.append(
            f"{mark} <code>{_ts(r['created_at'])}</code> {esc(r['action'])}"
            f" ⌯ منفذ <code>{r['actor_id'] or '-'}</code> ⌯ هدف <code>{r['target_id'] or '-'}</code>"
        )
    return f"{T.AUDIT_HEADER}\n" + "\n".join(lines) + "\n" + T.AUDIT_FOOTER


async def groups_text(svc: Services, limit: int = 15) -> str:
    rows = await svc.groups.recent(limit)
    if not rows:
        return f"{T.GROUPS_HEADER}\n{T.GROUPS_EMPTY}"
    lines = []
    for r in rows:
        mark = "🟢" if r["is_active"] else "⚫"
        title = esc(r["title"] or T.NO_TITLE)
        if r["username"]:
            title = f'<a href="https://t.me/{esc(r["username"])}">{title}</a>'
        lines.append(f"{mark} {title}\n    <code>{r['chat_id']}</code>")
    return f"{T.GROUPS_HEADER}\n" + "\n".join(lines)
