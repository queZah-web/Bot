"""أوامر مطور البوت (OWNER_ID فقط)."""
from __future__ import annotations

from zhoo.core import texts as T
from zhoo.core.commands import registry
from zhoo.core.context import CommandContext
from zhoo.core.ranks import Rank
from zhoo.handlers.views import audit_text, groups_text, owner_panel_text
from zhoo.keyboards.menus import owner_keyboard

S = "dev"


@registry.command("owner_panel", ("مركز المالك", "لوحه التحكم", "لوحة التحكم"), section=S,
                  min_rank=Rank.DEVELOPER, where="private", description="لوحة التحكم الكاملة بالأزرار")
async def cmd_owner_panel(cx: CommandContext) -> None:
    svc = cx.services
    await cx.reply(await owner_panel_text(svc), reply_markup=owner_keyboard(svc.maintenance))


@registry.command("maint_on", ("تفعيل الصيانه", "تفعيل الصيانة"), section=S, min_rank=Rank.DEVELOPER,
                  where="any", description="يوقف البوت للجميع عدا المطور", order=1)
async def cmd_maint_on(cx: CommandContext) -> None:
    await cx.services.bot_settings.set("maintenance", "1")
    await cx.services.audit.log("maintenance_on", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.MAINTENANCE_ON)


@registry.command("maint_off", ("تعطيل الصيانه", "تعطيل الصيانة", "ايقاف الصيانه"), section=S,
                  min_rank=Rank.DEVELOPER, where="any", description="يرجع البوت للعمل", order=2)
async def cmd_maint_off(cx: CommandContext) -> None:
    await cx.services.bot_settings.set("maintenance", "0")
    await cx.services.audit.log("maintenance_off", chat_id=cx.chat.id, actor_id=cx.user.id)
    await cx.reply(T.MAINTENANCE_OFF)


@registry.command("audit", ("سجل العمليات",), section=S, min_rank=Rank.DEVELOPER, where="any",
                  description="آخر العمليات الإدارية المسجلة", order=3)
async def cmd_audit(cx: CommandContext) -> None:
    await cx.reply(await audit_text(cx.services))


@registry.command("my_groups", ("مجموعاتي", "المجموعات"), section=S, min_rank=Rank.DEVELOPER,
                  where="any", description="آخر المجموعات اللي ضافتني", order=4)
async def cmd_groups(cx: CommandContext) -> None:
    await cx.reply(await groups_text(cx.services))
