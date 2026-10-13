from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.custom_emoji import get_custom_emoji_id_for_text

def make_kb_btn(text: str, custom_emoji_id: str = None, **kwargs) -> KeyboardButton:
    """Tugmaga mos Telegram Premium Custom Emoji ID sini avtomatik biriktiruvchi yordamchi"""
    cid = custom_emoji_id or get_custom_emoji_id_for_text(text)
    if cid:
        return KeyboardButton(text=text, icon_custom_emoji_id=cid, **kwargs)
    return KeyboardButton(text=text, **kwargs)

def get_admin_menu():
    """Bosh Adminlar uchun to'liq premium boshqaruv menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                make_kb_btn("Kino qo'shish ➕"),
                make_kb_btn("Kino o'chirish ❌")
            ],
            [
                make_kb_btn("Kino tahrirlash ✏️"),
                make_kb_btn("Kino faylini yangilash 🔄")
            ],
            [
                make_kb_btn("Statistika 📊"),
                make_kb_btn("Kino so'rovlari 📥")
            ],
            [
                make_kb_btn("Reklama yuborish 📢"),
                make_kb_btn("Rejalashtirilgan reklama 📅")
            ],
            [
                make_kb_btn("Homiy Kanallar 📢"),
                make_kb_btn("Zaxira (Backup) 💾")
            ],
            [
                make_kb_btn("Moderatorlar 👥"),
                make_kb_btn("Moderatorlarni boshqarish ⚙️")
            ],
            [
                make_kb_btn("Kino Trendlari 📈")
            ],
            [
                make_kb_btn("Ballar 💎"),
                make_kb_btn("➕ Mannual Premium Qo'shish")
            ],
            [
                make_kb_btn("Shubhali harakatlar 🚨"),
                make_kb_btn("Keshni tozalash 🧹")
            ],
            [
                make_kb_btn("Ommaviy yuklash 🔄"),
                make_kb_btn("Sozlamalar ⚙️")
            ],
            [
                make_kb_btn("Izohlar moderatsiyasi 💬"),
                make_kb_btn("🚫 Bloklanganlar")
            ],
            [
                make_kb_btn("💎 Premium Obunachilar"),
                make_kb_btn("Card 💳")
            ],
            [
                make_kb_btn("Limit ⏳"),
                make_kb_btn("Kassa 💰")
            ],
            [
                make_kb_btn("Promo Kodlar 🎁")
            ],
            [
                make_kb_btn("Audit Log 🛡️"),
                make_kb_btn("Faollik Tahlili 📊")
            ],
            [
                make_kb_btn("Yuborilgan reklamalar 📢"),
                make_kb_btn("Bot Rejimi 🛠️")
            ],
            [
                make_kb_btn("Nofaollarga Eslatma 💤"),
                make_kb_btn("Premium Sozlamalar 👑")
            ],
            [
                make_kb_btn("📉 Eng past baholi kinolar (75+ 👎)"),
                make_kb_btn("📊 Aktivlik Grafigi")
            ],
            [
                make_kb_btn("Treyler Post Yuborish 🎬"),
                make_kb_btn("🗑 Savat (3 kunlik)")
            ],
            [
                make_kb_btn("👥 Barcha Foydalanuvchilar"),
                make_kb_btn("🚫 Botni Bloklaganlar")
            ],
            [
                make_kb_btn("✅ Barcha Kanallarga Obuna Bo'lganlar"),
                make_kb_btn("🔍 Foydalanuvchi Qidirish")
            ],
            [
                make_kb_btn("📁 Kolleksiyalar"),
                make_kb_btn("📊 Dashboard")
            ],
            [
                make_kb_btn("✨ Premium Emojilar")
            ]
        ],
        resize_keyboard=True
    )

def get_moderator_menu(permissions: dict = None):
    """Moderatorlar uchun ruxsatnomalariga ko'ra dinamik premium menyu"""
    if permissions is None:
        permissions = {}
    keyboard = []
    
    # Qator 1: Kino qo'shish, o'chirish
    row1 = []
    if permissions.get("add_movie", True):
        row1.append(make_kb_btn("Kino qo'shish ➕"))
        row1.append(make_kb_btn("Kino o'chirish ❌"))
    if row1:
        keyboard.append(row1)
        
    # Qator 2: Kino tahrirlash, fayl yangilash
    row2_edit = []
    if permissions.get("add_movie", True):
        row2_edit.append(make_kb_btn("Kino tahrirlash ✏️"))
        row2_edit.append(make_kb_btn("Kino faylini yangilash 🔄"))
    if row2_edit:
        keyboard.append(row2_edit)
        
    # Qator 3: Statistika va Kino so'rovlari
    row2 = []
    if permissions.get("view_stats", True):
        row2.append(make_kb_btn("Statistika 📊"))
        row2.append(make_kb_btn("Kino so'rovlari 📥"))
    if row2:
        keyboard.append(row2)
        
    # Qator 4: Reklama va Rejalashtirilgan reklama
    row_broadcast = []
    if permissions.get("send_broadcast", False):
        row_broadcast.append(make_kb_btn("Reklama yuborish 📢"))
        row_broadcast.append(make_kb_btn("Rejalashtirilgan reklama 📅"))
    if row_broadcast:
        keyboard.append(row_broadcast)
        
    # Qator 5: Homiy kanallar va Zaxira (Backup)
    row3 = []
    if permissions.get("manage_sponsors", False):
        row3.append(make_kb_btn("Homiy Kanallar 📢"))
    if permissions.get("backup_db", False):
        row3.append(make_kb_btn("Zaxira (Backup) 💾"))
    if row3:
        keyboard.append(row3)
        
    # Qator 6: Trendlar
    row4 = []
    if permissions.get("view_trends", True):
        row4.append(make_kb_btn("Kino Trendlari 📈"))
    if row4:
        keyboard.append(row4)
        
    # Agar hech qanday ruxsat yo'q bo'lsa, oddiy user menyusini qaytaramiz
    if not keyboard:
        return get_user_menu()
        
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_user_menu():
    """Oddiy foydalanuvchilar uchun premium menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                make_kb_btn("💎 VIP Premium"),
                make_kb_btn("🔍 Kino qidirish")
            ],
            [
                make_kb_btn("🔥 Menga mos kinolar"),
                make_kb_btn("⭐️ Saqlanganlar")
            ],
            [
                make_kb_btn("Tarixim 🕐"),
                make_kb_btn("Tasodifiy Kino 🎲")
            ],
            [
                make_kb_btn("Kino so'rash 🎬"),
                make_kb_btn("💎 Mening Ballarim")
            ],
            [
                make_kb_btn("🎁 Kunlik Bonus"),
                make_kb_btn("🏆 Reytinglar")
            ],
            [
                make_kb_btn("🗳️ Kino so'rovlari")
            ],
            [
                make_kb_btn("👑 Profilim"),
                make_kb_btn("🔝 TOP Kinolar")
            ],
            [
                make_kb_btn("💳 To'lovlarim"),
                make_kb_btn("🎂 Tug'ilgan Kun")
            ],
            [
                make_kb_btn("⚙️ Sozlamalar"),
                make_kb_btn("🆘 Yordam / Murojaat")
            ]
        ],
        resize_keyboard=True
    )
