"""بوت آمن: أي رسالة أو تعليق أو تنبيه يطلع من زهو ينفحص قبل الإرسال، وأي سب بيه يتغطى (••••).

هذا خط الدفاع الأخير: حتى لو نص جاي من عضو (اسمه، رد مضاف، نبذة، قوانين، عنوان يوتيوب...)
بيه سب، ما يوصل للمجموعة من زهو أبداً.
"""
from __future__ import annotations

from telegram.ext import ExtBot

from zhoo.core.swear import detector


def clean(text):
    return detector.mask_html(text) if isinstance(text, str) and text else text


def _fix(args: tuple, kwargs: dict, key: str, pos: int | None) -> tuple[tuple, dict]:
    if key in kwargs:
        kwargs[key] = clean(kwargs[key])
    elif pos is not None and len(args) > pos:
        args = args[:pos] + (clean(args[pos]),) + args[pos + 1:]
    return args, kwargs


class SafeOutputMixin:
    """يغطي السب بكل النصوص الطالعة من البوت."""

    async def send_message(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "text", 1)
        return await super().send_message(*args, **kwargs)

    async def edit_message_text(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "text", 0)
        return await super().edit_message_text(*args, **kwargs)

    async def edit_message_caption(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 3)
        return await super().edit_message_caption(*args, **kwargs)

    async def answer_callback_query(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "text", 1)
        return await super().answer_callback_query(*args, **kwargs)

    async def send_photo(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 2)
        return await super().send_photo(*args, **kwargs)

    async def send_video(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 3)
        return await super().send_video(*args, **kwargs)

    async def send_audio(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 5)
        return await super().send_audio(*args, **kwargs)

    async def send_document(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 2)
        return await super().send_document(*args, **kwargs)

    async def send_animation(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 5)
        return await super().send_animation(*args, **kwargs)

    async def send_voice(self, *args, **kwargs):
        args, kwargs = _fix(args, kwargs, "caption", 3)
        return await super().send_voice(*args, **kwargs)


class SafeBot(SafeOutputMixin, ExtBot):
    """بوت زهو الفعلي."""
