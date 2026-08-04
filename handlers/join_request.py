from aiogram import Router
from aiogram.types import ChatJoinRequest
from database import requests as db_req

router = Router()

@router.chat_join_request()
async def auto_approve_join_request(update: ChatJoinRequest):
    user = update.from_user
    
    # 1. So'rovni avtomatik tasdiqlash
    try:
        await update.approve()
    except Exception as e:
        print(f"Join request tasdiqlashda xato: {e}")
        return
        
    # 2. Foydalanuvchini bot bazasiga qo'shish
    await db_req.add_user(user.id, user.username or "", user.full_name)
    
    # 3. Foydalanuvchiga shaxsiy xabar yuborishga urinish
    try:
        await update.bot.send_message(
            chat_id=user.id,
            text=f"👋 <b>Assalomu alaykum, {user.first_name}!</b>\n\n"
                 f"✅ <b>{update.chat.title}</b> kanaliga qo'shilish so'rovingiz muvaffaqiyatli tasdiqlandi.\n\n"
                 f"🍿 Menga shunchaki kino kodini yuborib tomosha qilishingiz mumkin!"
        )
    except Exception:
        # Agar foydalanuvchi botga avval start bosmagan bo'lsa xato beradi, uni e'tiborsiz qoldiramiz
        pass
