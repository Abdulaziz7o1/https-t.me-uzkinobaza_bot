import logging
from aiogram import Bot
import config
from database import requests as db_req

async def send_abuse_alert(bot: Bot, user_id: int, alert_type: str, details: str):
    """Shubhali harakat sodir bo'lganda bosh adminlarga tezkor ogohlantirish yuborish"""
    try:
        # DB journalga ham yozish
        await db_req.add_abuse_log(user_id, alert_type, details)
        
        # User ma'lumotlarini olish
        user = await db_req.get_user(user_id)
        username = f"@{user[1]}" if user and user[1] else (user[2] if user else str(user_id))
        
        from keyboards.inline import get_abuse_action_keyboard
        
        alert_text = (
            f"🚨 <b>SHOSHILINCH OGOHLANTIRISH! (Spam Alert)</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {username} (ID: <code>{user_id}</code>)\n"
            f"⚡ <b>Harakat turi:</b> <code>{alert_type}</code>\n"
            f"📝 <b>Tafsilot:</b> {details}\n\n"
            f"⚠️ <i>Boshqaruv paneli orqali ushbu foydalanuvchini bloklashingiz mumkin.</i>"
        )
        
        admins = set(config.ADMINS)
        try:
            db_admins = await db_req.get_all_admins()
            admins.update(db_admins)
        except Exception:
            pass
        
        for admin_id in admins:
            try:
                await bot.send_message(
                    admin_id, 
                    alert_text, 
                    parse_mode="HTML", 
                    reply_markup=get_abuse_action_keyboard(user_id)
                )
            except Exception as e:
                logging.error(f"Admin alert yuborishda xato: {e}")
    except Exception as e:
        logging.error(f"send_abuse_alert xatosi: {e}")
