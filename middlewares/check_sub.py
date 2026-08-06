from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
import config
from keyboards.inline import get_subscription_keyboard
from database.requests import add_user, is_banned, get_sponsor_channels

class CheckSubMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Faqat matnli xabarlar va buyruqlarni tekshiramiz
        if not isinstance(event, Message):
            return await handler(event, data)
            
        user_id = event.from_user.id
        username = event.from_user.username or ""
        full_name = event.from_user.full_name or ""
        
        # 1. Foydalanuvchi bloklanganini tekshirish (doimiy va vaqtincha)
        from database.requests import is_user_temp_banned
        try:
            result = await is_user_temp_banned(user_id)
            if result is None:
                is_banned_flag, rem_str = False, ""
            else:
                is_banned_flag, rem_str = result
        except Exception:
            is_banned_flag, rem_str = False, ""
        if is_banned_flag:
            if rem_str and rem_str != "Doimiy":
                await event.answer(f"🚫 <b>Sizning hisobingiz vaqtincha bloklangan!</b>\n\n⏰ <b>Qolgan ban muddati:</b> {rem_str}\n<i>Muddat tugagach botdan qayta foydalanishingiz mumkin.</i>", parse_mode="HTML")
            else:
                await event.answer("🚫 <b>Siz botdan foydalanishdan bloklangansiz!</b>\n\n<i>Murojaat uchun adminga bog'laning.</i>", parse_mode="HTML")
            return
            
        # Foydalanuvchini bazaga qo'shish
        await add_user(user_id, username, full_name)
        
        # Faollik vaqtini yangilash
        from database.requests import update_user_activity
        await update_user_activity(user_id)
        
        # Adminlar va Moderatorlar uchun har qanday obuna tekshiruvini 100% aylanib o'tamiz
        user_id_int = int(user_id)
        admin_ids = [int(a) for a in config.ADMINS]
        db_admins = [int(a) for a in await get_all_admins()]
        if user_id_int in admin_ids or user_id_int in db_admins:
            return await handler(event, data)

        # 1.5. Bot Yangilanmoqda (Maintenance Mode) tekshiruvi
        from database.requests import get_setting
        m_mode = await get_setting("bot_maintenance_mode")
        if m_mode == "1":
            if not is_admin_user:
                await event.answer(
                    "🛠️ <b>BOT YANGILANMOQDA!</b> 🚀\n\n"
                    "Hurmatli foydalanuvchi, botimizga siz uchun yanada ko'p qulayliklar va yangi va zo'r funksiyalar qo'shilmoqda! ✨\n\n"
                    "🕒 <i>Juda tez orada botimiz yangi imkoniyatlar bilan ishga tushadi. Sabringiz uchun rahmat!</i> 🍿",
                    parse_mode="HTML"
                )
                return

        # Premium to'lov cheki yuborayotgan foydalanuvchilar obuna tekshiruvidan ozod qilinadi
        if curr_state and ("waiting_for_payment" in str(curr_state) or "payment" in str(curr_state).lower()):
            return await handler(event, data)

        # Premium/VIP foydalanuvchilar obuna tekshiruvidan ozod qilinadi (Whitelist)
        try:
            if await is_user_premium(user_id):
                return await handler(event, data)
        except Exception:
            pass
            
        # 2. Kanallarni olish (static + dynamic)
        db_channels = await get_sponsor_channels()
        formatted_channels = []
        for ch in config.CHANNELS:
            formatted_channels.append((ch, ch))
        for db_ch in db_channels:
            formatted_channels.append((db_ch[1], db_ch[2] or db_ch[1]))

        # Agar kanallar sozlanmagan bo'lsa tekshirmaymiz
        if not formatted_channels:
            return await handler(event, data)

        bot = data["bot"]
        not_subscribed_channels = []

        for ch_tuple in formatted_channels:
            ch_id = ch_tuple[0]
            ch_target = str(ch_id).strip()
            
            # Link shaklida bo'lsa chat_id ni tozalash (masalan: https://t.me/kanal_nomi -> @kanal_nomi)
            if "t.me/" in ch_target:
                parts = ch_target.split("t.me/")[1].strip("/")
                if not parts.startswith("+") and not parts.startswith("joinchat/") and not parts.startswith("c/"):
                    ch_target = "@" + parts.split("/")[0]

            try:
                member = await bot.get_chat_member(chat_id=ch_target, user_id=user_id)
                if member.status not in ["creator", "administrator", "member"]:
                    not_subscribed_channels.append(ch_tuple)
            except Exception as e:
                print(f"Kanal tekshirishda xato ({ch_target}): {e}")
                not_subscribed_channels.append(ch_tuple)

        if not_subscribed_channels:
            await event.answer(
                "📢 <b>Botdan foydalanish va kinolarni tomosha qilish uchun quyidagi homiy kanallarimizga a'zo bo'ling:</b>",
                parse_mode="HTML",
                reply_markup=get_subscription_keyboard(not_subscribed_channels)
            )
            return

        return await handler(event, data)


class StateCancelMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.text:
            text_clean = event.text.lower().replace("\ufe0f", "").strip()
            state = data.get("state")
            if state:
                current_state = await state.get_state()
                if current_state is not None:
                    # Admin FSM holatida turgan bo'lsa, holat faqat /cancel yoki /start da tozalanadi
                    if "AdminStates" in str(current_state):
                        if text_clean in ["/start", "/cancel", "bekor qilish ❌", "bekor qilish"]:
                            await state.clear()
                            data["raw_state"] = None
                            import logging
                            logging.info(f"Admin FSM state '{current_state}' canceled explicitly by '{text_clean}'.")
                    else:
                        is_url = text_clean.startswith(("http://", "https://", "t.me/")) or "://" in text_clean
                        if not is_url:
                            menu_keywords = [
                                "qidirish", "saqlanganlar", "tanlanganlar", "tasodifiy", "so'rash",
                                "ballarim", "bonus", "reytinglar", "referal", "so'rovlari",
                                "sozlamalar", "profilim", "top kinolar", "tug'ilgan kun", "yordam", "murojaat",
                                "kino qo'shish", "kino o'chirish", "kino tahrirlash", "statistika", "reklama",
                                "kassa", "audit", "tahlili", "bot rejimi", "nofaollarga", "promo", "zaxira",
                                "moderatorlar", "trendlari", "kun kinosi", "shubhali", "keshni", "ommaviy"
                            ]
                            exact_cancel_cmds = ["/start", "/cancel", "/help", "/stop", "start", "cancel"]
                            if text_clean in exact_cancel_cmds or any(kw == text_clean for kw in menu_keywords):
                                await state.clear()
                                data["raw_state"] = None
                                import logging
                                logging.info(f"FSM state '{current_state}' cleared automatically for command/menu button '{text_clean}'.")
        return await handler(event, data)


# Vaqtinchalik bloklangan foydalanuvchilar (user_id -> unban_timestamp)
TEMP_BANS = {}

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 0.5):
        self.limit = limit
        self.last_request = {} # user_id -> last_timestamp
        
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
            
        user_id = event.from_user.id
        
        # Bosh admin va Moderatorlar Anti-Flood cheklovidan 100% ozod qilinadi
        user_id_int = int(user_id)
        admin_ids = [int(a) for a in config.ADMINS]
        if user_id_int in admin_ids:
            return await handler(event, data)
            
        import time
        now = time.time()
        
        # 1. Temp ban tekshirish
        if user_id in TEMP_BANS:
            ban_expiry = TEMP_BANS[user_id]
            if now < ban_expiry:
                remaining = int(ban_expiry - now)
                last_warn = self.last_request.get(f"warn_{user_id}", 0)
                if now - last_warn > 5:
                    self.last_request[f"warn_{user_id}"] = now
                    await event.answer(
                        f"❌ <b>Siz spam tufayli vaqtincha bloklangansiz!</b>\n\n"
                        f"🕒 Iltimos, {remaining} soniyadan keyin qayta urining.",
                        parse_mode="HTML"
                    )
                return
            else:
                # Ban muddati tugagan
                del TEMP_BANS[user_id]
                from database.requests import add_abuse_log
                await add_abuse_log(user_id, "AUTO_UNBAN", "Vaqtinchalik blok muddati tugadi.")
        
        # 2. Flood tekshirish
        last_time = self.last_request.get(user_id, 0)
        if now - last_time < self.limit:
            self.last_request[user_id] = now
            last_warn = self.last_request.get(f"flood_warn_{user_id}", 0)
            if now - last_warn > 5:
                self.last_request[f"flood_warn_{user_id}"] = now
                from utils.alerts import send_abuse_alert
                await send_abuse_alert(event.bot, user_id, "FLOOD_SPAM", "Tugmalarni/xabarlarni ketma-ket juda tez yubordi (Anti-Flood).")
                await event.answer(
                    "⚠️ <b>Spam taqiqlanadi!</b> Iltimos, xabarlar va tugmalarni sekinroq bosing.",
                    parse_mode="HTML"
                )
            return
            
        self.last_request[user_id] = now
        return await handler(event, data)


