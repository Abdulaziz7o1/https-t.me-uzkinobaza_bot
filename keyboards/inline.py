from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config

def get_subscription_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Majburiy obuna kanallari tugmalari va tekshirish tugmasi"""
    builder = InlineKeyboardBuilder()
    
    for idx, channel in enumerate(channels, 1):
        if isinstance(channel, (tuple, list)):
            ch_id = channel[0]
            ch_name = channel[1] if len(channel) > 1 else str(ch_id)
        else:
            ch_id, ch_name = channel, str(channel)
            
        ch_str = str(ch_id).strip()
        if ch_str.startswith("http://") or ch_str.startswith("https://"):
            link = ch_str
        elif ch_str.startswith("t.me/"):
            link = "https://" + ch_str
        elif ch_str.startswith("@"):
            link = f"https://t.me/{ch_str[1:]}"
        else:
            link = f"https://t.me/{ch_str}"
            
        display_name = ch_name if ch_name and str(ch_name) != str(ch_id) else f"{idx}-Kanal"
        if not display_name.startswith("📢") and not display_name.endswith("📢"):
            display_name = f"📢 {display_name}"
            
        builder.button(text=display_name, url=link)
            
    builder.button(text="A'zo bo'ldim ✅", callback_data="check_sub")
    builder.button(text="💎 VIP Premium olish (Kutish va Obunalarsiz!) 🚀", callback_data="sub_buy_premium")
    builder.adjust(1)
    return builder.as_markup()

def get_movie_action_keyboard(movie_id: int, is_fav: bool, avg_rating: float, likes: int = 0, dislikes: int = 0, fires: int = 0) -> InlineKeyboardMarkup:
    """Kino ostidagi harakatlar (Reaksiyalar, Tanlanganlar, Ulashish, Reyting)"""
    builder = InlineKeyboardBuilder()
    
    # 0. Reaksiya tugmalari (👍 👎 🔥)
    builder.button(text=f"👍 {likes}", callback_data=f"react_{movie_id}_like")
    builder.button(text=f"👎 {dislikes}", callback_data=f"react_{movie_id}_dislike")
    builder.button(text=f"🔥 {fires}", callback_data=f"react_{movie_id}_fire")

    # 1. Tanlanganlar
    fav_text = "Tanlanganlardan o'chirish ❌" if is_fav else "Tanlanganlarga qo'shish ⭐"
    builder.button(text=fav_text, callback_data=f"fav_toggle_{movie_id}")
    
    # 2. Baho berish
    rating_text = f"Baho berish ⭐ ({avg_rating} ★)" if avg_rating > 0 else "Baho berish ⭐"
    builder.button(text=rating_text, callback_data=f"rate_menu_{movie_id}")
    
    # 3. Ulashish — deep link orqali, do'st bosganida bot videoni yuboradi
    bot_clean = config.BOT_USERNAME.lstrip('@')
    share_text = f"🎬 Kino kodi: {movie_id} | {config.BOT_USERNAME} orqali ko'ring!"
    deep_link = f"https://t.me/{bot_clean}?start=movie_{movie_id}"
    share_url = f"https://t.me/share/url?url={deep_link}&text={share_text}"
    builder.button(text="Do'stlarga ulashish 🚀", url=share_url)
    
    # 4. Izohlar va Muhokama guruhi
    builder.button(text="Izohlar 💬", callback_data=f"comments_list_{movie_id}")
    builder.button(text="💬 Muhokama guruhi", url="https://t.me/+FPb6kIcYVwphNjEy")
    
    # 5. Faylda nuqson borligi haqida shikoyat
    builder.button(text="⚠️ Faylda nuqson bor", callback_data=f"report_movie_{movie_id}")
    
    builder.adjust(3, 1, 1, 1, 1, 1, 1)
    return builder.as_markup()

def get_comments_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Izohlar menyusi tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Izoh yozish ✍️", callback_data=f"add_comment_start_{movie_id}")
    builder.button(text="Orqaga ↩️", callback_data=f"movie_menu_{movie_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_rating_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Kinoga 1 dan 5 gacha baho berish tugmalari (hissiyotli va rangli)"""
    builder = InlineKeyboardBuilder()

    ratings = [
        (1, "1 😡 Daxshat"),
        (2, "2 😐 Qoniqarsiz"),
        (3, "3 🙂 Yomon emas"),
        (4, "4 😊 Yaxshi"),
        (5, "5 🔥 Zo'r!")
    ]
    for r_val, r_text in ratings:
        builder.button(text=r_text, callback_data=f"rate_{movie_id}_{r_val}")

    builder.button(text="Ortga ↩️", callback_data=f"movie_menu_{movie_id}")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    """Reklama auditoriyasini tanlash tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Barcha foydalanuvchilar", callback_data="bc_target_all")
    builder.button(text="👑 Faqat Premium a'zolar", callback_data="bc_target_premium")
    builder.button(text="⚡️ Oxirgi 7 kunda faol bo'lganlar", callback_data="bc_target_active_7d")
    builder.button(text="❌ Bekor qilish", callback_data="bc_cancel")
    builder.adjust(1)
    return builder.as_markup()

def get_ticket_reply_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Admin javob berishi uchun inline tugma"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Javob berish", callback_data=f"reply_ticket_{ticket_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_user_manage_keyboard(target_user_id: int) -> InlineKeyboardMarkup:
    """Admin foydalanuvchini boshqarish inline tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚫 Bloklash", callback_data=f"admin_ban_{target_user_id}")
    builder.button(text="🔓 Blokdan Chiqarish", callback_data=f"admin_unban_{target_user_id}")
    builder.button(text="💎 +10 Ball Berish", callback_data=f"admin_addpts_{target_user_id}_10")
    builder.button(text="💎 -10 Ball Ayirish", callback_data=f"admin_subpts_{target_user_id}_10")
    builder.button(text="👑 Premium Berish (7 kun)", callback_data=f"admin_premium_{target_user_id}")
    builder.button(text="🎂 Tug'ilgan Kun Reset", callback_data=f"admin_resetbday_{target_user_id}")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_top_movies_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """TOP kinolar sahifali navigatsiya"""
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="⬅️ Oldingi", callback_data=f"top_movies_page_{page-1}")
    if total_pages > 1:
        builder.button(text=f"📄 {page}/{total_pages}", callback_data="top_movies_info")
    if page < total_pages:
        builder.button(text="Keyingi ➡️", callback_data=f"top_movies_page_{page+1}")
    builder.adjust(3)
    return builder.as_markup()


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Profil kartasi tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔝 TOP Kinolar", callback_data="show_top_movies_1")
    builder.button(text="⭐️ Saqlanganlar", callback_data="show_favorites_profile")
    builder.button(text="🕒 Ko'rilgan Kinolar", callback_data="show_watch_history")
    builder.adjust(1)
    return builder.as_markup()


def get_admin_card_keyboard(card_exists: bool) -> InlineKeyboardMarkup:
    """Admin karta boshqaruvi inline tugmalari"""
    builder = InlineKeyboardBuilder()
    if card_exists:
        builder.button(text="✏️ Tahrirlash", callback_data="admin_card_edit")
        builder.button(text="❌ O'chirish", callback_data="admin_card_delete")
        builder.adjust(2)
    else:
        builder.button(text="➕ Karta qo'shish", callback_data="admin_card_edit")
        builder.adjust(1)
    return builder.as_markup()


def get_abuse_action_keyboard(target_user_id: int) -> InlineKeyboardMarkup:
    """Shubhali harakat logi ostidagi inline harakat tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Ogohlantirish", callback_data=f"warn_usr_{target_user_id}")
    builder.button(text="🚫 Bloklash", callback_data=f"admin_ban_{target_user_id}")
    builder.adjust(2)
    return builder.as_markup()


def get_ban_duration_keyboard(target_user_id: int) -> InlineKeyboardMarkup:
    """Bloklash muddatini tanlash inline tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏱ 1 soat", callback_data=f"do_ban_{target_user_id}_1h")
    builder.button(text="⏱ 24 soat (1 kun)", callback_data=f"do_ban_{target_user_id}_24h")
    builder.button(text="⏱ 7 kun (1 hafta)", callback_data=f"do_ban_{target_user_id}_7d")
    builder.button(text="⏱ 30 kun (1 oy)", callback_data=f"do_ban_{target_user_id}_30d")
    builder.button(text="🛑 Doimiy (Permanent)", callback_data=f"do_ban_{target_user_id}_perm")
    builder.button(text="🔙 Bekor qilish", callback_data=f"cancel_ban_{target_user_id}")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def get_premium_user_action_keyboard(target_user_id: int) -> InlineKeyboardMarkup:
    """Premium foydalanuvchi kartasi ostidagi inline tugmalar"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ Ogohlantirish", callback_data=f"prem_warn_{target_user_id}")
    builder.button(text="🚫 Bloklash", callback_data=f"prem_ban_{target_user_id}")
    builder.button(text="❌ Premiumni O'chirish", callback_data=f"prem_remove_{target_user_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_moderator_perm_matrix_keyboard(target_user_id: int, perms: dict) -> InlineKeyboardMarkup:
    """Moderator ruxsatlarini boshqarish dinamik tugmalari"""
    builder = InlineKeyboardBuilder()
    
    labels = {
        "add_movie": "➕ Kino qo'shish",
        "delete_movie": "❌ Kino o'chirish",
        "view_stats": "📊 Statistika ko'rish",
        "send_broadcast": "📢 Reklama yuborish",
        "manage_sponsors": "📢 Homiy kanallar",
        "view_trends": "📈 Kino trendlari",
        "backup_db": "💾 Zaxira (Backup)"
    }
    
    for key, label in labels.items():
        status = "ON ✅" if perms.get(key, False) else "OFF ❌"
        builder.button(
            text=f"{label}: {status}",
            callback_data=f"mod_perm_toggle_{target_user_id}_{key}"
        )
        
    builder.button(text="🔙 Moderatorlar ro'yxatiga qaytish", callback_data="mod_perms_list_back")
    builder.adjust(1)
    return builder.as_markup()




