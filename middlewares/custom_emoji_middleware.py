import logging
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import (
    SendMessage,
    EditMessageText,
    SendPhoto,
    SendVideo,
    SendDocument,
    SendAnimation,
    EditMessageCaption,
    SendAudio,
    SendVoice
)
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from utils.custom_emoji import (
    apply_custom_emojis,
    get_custom_emoji_id_for_text,
    is_custom_emojis_enabled
)

logger = logging.getLogger(__name__)


class CustomEmojiRequestMiddleware(BaseRequestMiddleware):
    """
    Aiogram botining barcha chiquvchi so'rovlarini tahlil qilib:
    1. Xabar va sarlavhalardagi (text, caption) emojilarni avtomatik
       Telegram Premium animatsiyali <tg-emoji> formatiga o'tkazadi.
    2. Barcha Reply va Inline tugmalardagi emojilarni aniqlab, ularga
       icon_custom_emoji_id maydonini o'rnatadi.
    """

    async def __call__(self, make_request, bot, method):
        if not is_custom_emojis_enabled():
            return await make_request(bot, method)

        try:
            # 1. Matnli xabarlar
            if isinstance(method, (SendMessage, EditMessageText)):
                if getattr(method, "text", None):
                    method.text = apply_custom_emojis(method.text)

            # 2. Media fayllar sarlavhalari (caption)
            elif isinstance(method, (SendPhoto, SendVideo, SendDocument, SendAnimation, EditMessageCaption, SendAudio, SendVoice)):
                if getattr(method, "caption", None):
                    method.caption = apply_custom_emojis(method.caption)

            # 3. Tugmalar (Keyboard / InlineKeyboard)
            rm = getattr(method, "reply_markup", None)
            if rm:
                if isinstance(rm, ReplyKeyboardMarkup) and rm.keyboard:
                    for row in rm.keyboard:
                        for btn in row:
                            if getattr(btn, "icon_custom_emoji_id", None) is None and getattr(btn, "text", None):
                                cid = get_custom_emoji_id_for_text(btn.text)
                                if cid:
                                    btn.icon_custom_emoji_id = cid
                elif isinstance(rm, InlineKeyboardMarkup) and rm.inline_keyboard:
                    for row in rm.inline_keyboard:
                        for btn in row:
                            if getattr(btn, "icon_custom_emoji_id", None) is None and getattr(btn, "text", None):
                                cid = get_custom_emoji_id_for_text(btn.text)
                                if cid:
                                    btn.icon_custom_emoji_id = cid
        except Exception as e:
            logger.debug(f"CustomEmojiRequestMiddleware error: {e}")

        return await make_request(bot, method)
