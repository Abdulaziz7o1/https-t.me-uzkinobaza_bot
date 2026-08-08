from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_admin_menu():
    """Bosh Adminlar uchun to'liq boshqaruv menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Kino qo'shish ➕"),
                KeyboardButton(text="Kino o'chirish ❌")
            ],
            [
                KeyboardButton(text="Kino tahrirlash ✏️"),
                KeyboardButton(text="Kino faylini yangilash 🔄")
            ],
            [
                KeyboardButton(text="Statistika 📊"),
                KeyboardButton(text="Kino so'rovlari 📥")
            ],
            [
                KeyboardButton(text="Reklama yuborish 📢"),
                KeyboardButton(text="Rejalashtirilgan reklama 📅")
            ],
            [
                KeyboardButton(text="Homiy Kanallar 📢"),
                KeyboardButton(text="Zaxira (Backup) 💾")
            ],
            [
                KeyboardButton(text="Moderatorlar 👥"),
                KeyboardButton(text="Moderatorlarni boshqarish ⚙️")
            ],
            [
                KeyboardButton(text="Kino Trendlari 📈"),
                KeyboardButton(text="Referal sozlash 👥")
            ],
            [
                KeyboardButton(text="Kun Kinosi ☀️"),
                KeyboardButton(text="Ballar 💎")
            ],
            [
                KeyboardButton(text="Shubhali harakatlar 🚨"),
                KeyboardButton(text="Keshni tozalash 🧹")
            ],
            [
                KeyboardButton(text="Ommaviy yuklash 🔄"),
                KeyboardButton(text="Sozlamalar ⚙️")
            ],
            [
                KeyboardButton(text="Izohlar moderatsiyasi 💬"),
                KeyboardButton(text="🚫 Bloklanganlar")
            ],
            [
                KeyboardButton(text="💎 Premium Obunachilar"),
                KeyboardButton(text="Card 💳")
            ],
            [
                KeyboardButton(text="Limit ⏳"),
                KeyboardButton(text="Kassa 💰")
            ],
            [
                KeyboardButton(text="Promo Kodlar 🎁"),
                KeyboardButton(text="2X Referal ⚡")
            ],
            [
                KeyboardButton(text="Audit Log 🛡️"),
                KeyboardButton(text="Faollik Tahlili 📊")
            ],
            [
                KeyboardButton(text="Yuborilgan reklamalar 📢"),
                KeyboardButton(text="Bot Rejimi 🛠️")
            ],
            [
                KeyboardButton(text="Nofaollarga Eslatma 💤"),
                KeyboardButton(text="Premium Sozlamalar 👑")
            ],
            [
                KeyboardButton(text="➕ Mannual Premium Qo'shish")
            ]
        ],
        resize_keyboard=True
    )

def get_moderator_menu(permissions: dict):
    """Moderatorlar uchun ruxsatnomalariga ko'ra dinamik menyu"""
    keyboard = []
    
    # Qator 1: Kino qo'shish, o'chirish
    row1 = []
    if permissions.get("add_movie", True):
        row1.append(KeyboardButton(text="Kino qo'shish ➕"))
        row1.append(KeyboardButton(text="Kino o'chirish ❌"))
    if row1:
        keyboard.append(row1)
        
    # Qator 2: Kino tahrirlash, fayl yangilash
    row2_edit = []
    if permissions.get("add_movie", True):
        row2_edit.append(KeyboardButton(text="Kino tahrirlash ✏️"))
        row2_edit.append(KeyboardButton(text="Kino faylini yangilash 🔄"))
    if row2_edit:
        keyboard.append(row2_edit)
        
    # Qator 3: Statistika va Kino so'rovlari
    row2 = []
    if permissions.get("view_stats", True):
        row2.append(KeyboardButton(text="Statistika 📊"))
        row2.append(KeyboardButton(text="Kino so'rovlari 📥"))
    if row2:
        keyboard.append(row2)
        
    # Qator 4: Reklama va Rejalashtirilgan reklama
    row_broadcast = []
    if permissions.get("send_broadcast", False):
        row_broadcast.append(KeyboardButton(text="Reklama yuborish 📢"))
        row_broadcast.append(KeyboardButton(text="Rejalashtirilgan reklama 📅"))
    if row_broadcast:
        keyboard.append(row_broadcast)
        
    # Qator 5: Homiy kanallar va Zaxira (Backup)
    row3 = []
    if permissions.get("manage_sponsors", False):
        row3.append(KeyboardButton(text="Homiy Kanallar 📢"))
    if permissions.get("backup_db", False):
        row3.append(KeyboardButton(text="Zaxira (Backup) 💾"))
    if row3:
        keyboard.append(row3)
        
    # Qator 6: Trendlar
    row4 = []
    if permissions.get("view_trends", True):
        row4.append(KeyboardButton(text="Kino Trendlari 📈"))
    if row4:
        keyboard.append(row4)
        
    # Agar hech qanday ruxsat yo'q bo'lsa, oddiy user menyusini qaytaramiz
    if not keyboard:
        return get_user_menu()
        
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_user_menu():
    """Oddiy foydalanuvchilar uchun menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💎 VIP Premium"),
                KeyboardButton(text="🔍 Kino qidirish")
            ],
            [
                KeyboardButton(text="⭐️ Saqlanganlar"),
                KeyboardButton(text="Tasodifiy Kino 🎲")
            ],
            [
                KeyboardButton(text="Kino so'rash 🎬"),
                KeyboardButton(text="💎 Mening Ballarim")
            ],
            [
                KeyboardButton(text="🎁 Kunlik Bonus"),
                KeyboardButton(text="🏆 Reytinglar")
            ],
            [
                KeyboardButton(text="👥 Referal"),
                KeyboardButton(text="🗳️ Kino so'rovlari")
            ],
            [
                KeyboardButton(text="👑 Profilim"),
                KeyboardButton(text="🔝 TOP Kinolar")
            ],
            [
                KeyboardButton(text="⚙️ Sozlamalar"),
                KeyboardButton(text="🎂 Tug'ilgan Kun")
            ],
            [
                KeyboardButton(text="🆘 Yordam / Murojaat")
            ]
        ],
        resize_keyboard=True
    )
