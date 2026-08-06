"""
Barcha botdan chiqadigan xabarlarga avtomatik footer qo'shuvchi middleware.
Faqat text xabarlar uchun ishlaydi (photo/video/audio emas).
"""
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

CONTACT_FOOTER = "\n\n📩 <b>Murojaat uchun:</b> @Abdulaziz7o1"
CONTACT_FOOTER_PLAIN = "\n\nMurojaat uchun: @Abdulaziz7o1"

def _append_footer(text: str, parse_mode: str = None) -> str:
    """Xabar matniga footer qo'shish (agar allaqachon bo'lmasa)"""
    if not text:
        return text
    if "@Abdulaziz7o1" in text or "Murojaat uchun" in text:
        return text
    if parse_mode and parse_mode.upper() == "HTML":
        return text + CONTACT_FOOTER
    return text + CONTACT_FOOTER_PLAIN


class ContactFooterMiddleware(BaseMiddleware):
    """
    Har bir xabarga murojaat footerini qo'shadi.
    Faqat bot -> user yo'nalishidagi matn xabarlarga qo'shiladi.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        return await handler(event, data)
