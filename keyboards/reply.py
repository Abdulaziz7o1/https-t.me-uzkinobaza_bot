import re
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.custom_emoji import (
    get_custom_emoji_id,
    get_custom_emoji_id_for_text,
    DEFAULT_CUSTOM_EMOJIS
)

# Har bir tugma matni uchun maxsus Telegram Premium Custom Emoji ID xaritasi
BUTTON_CUSTOM_EMOJIS: dict[str, str] = {
    # Bosh Admin va Moderator menyulari
    "Kino qo'shish": DEFAULT_CUSTOM_EMOJIS.get("➕", "5226945370684140473"),
    "Kino o'chirish": DEFAULT_CUSTOM_EMOJIS.get("❌", "5465665476971471368"),
    "Kino tahrirlash": DEFAULT_CUSTOM_EMOJIS.get("✏️", "5199501302756812716"),
    "Kino faylini yangilash": DEFAULT_CUSTOM_EMOJIS.get("🔄", "5226702984204797593"),
    "Statistika": DEFAULT_CUSTOM_EMOJIS.get("📊", "5431577498364158238"),
    "Kino so'rovlari": DEFAULT_CUSTOM_EMOJIS.get("📥", "5433811242135331842"),
    "Reklama yuborish": DEFAULT_CUSTOM_EMOJIS.get("📢", "5199850887324902331"),
    "Rejalashtirilgan reklama": DEFAULT_CUSTOM_EMOJIS.get("📅", "5431897022456145283"),
    "Homiy Kanallar": DEFAULT_CUSTOM_EMOJIS.get("📢", "5199850887324902331"),
    "Zaxira (Backup)": DEFAULT_CUSTOM_EMOJIS.get("💾", "5433653135799228968"),
    "Moderatorlar": DEFAULT_CUSTOM_EMOJIS.get("👥", "5372926953978341366"),
    "Moderatorlarni boshqarish": DEFAULT_CUSTOM_EMOJIS.get("⚙️", "5199638831904596483"),
    "Kino Trendlari": DEFAULT_CUSTOM_EMOJIS.get("📈", "5197503331215361533"),
    "Ballar": DEFAULT_CUSTOM_EMOJIS.get("💎", "5471952986970267163"),
    "Mannual Premium Qo'shish": DEFAULT_CUSTOM_EMOJIS.get("➕", "5226945370684140473"),
    "Shubhali harakatlar": DEFAULT_CUSTOM_EMOJIS.get("🚨", "4983302733659374380"),
    "Keshni tozalash": DEFAULT_CUSTOM_EMOJIS.get("🧹", "5355021050637722984"),
    "Ommaviy yuklash": DEFAULT_CUSTOM_EMOJIS.get("🔄", "5226702984204797593"),
    "Sozlamalar": DEFAULT_CUSTOM_EMOJIS.get("⚙️", "5199638831904596483"),
    "Izohlar moderatsiyasi": DEFAULT_CUSTOM_EMOJIS.get("💬", "5465300082628763143"),
    "Bloklanganlar": DEFAULT_CUSTOM_EMOJIS.get("🚫", "5465665476971471368"),
    "Premium Obunachilar": DEFAULT_CUSTOM_EMOJIS.get("💎", "5471952986970267163"),
    "Card": DEFAULT_CUSTOM_EMOJIS.get("💳", "5280872069519654995"),
    "Limit": DEFAULT_CUSTOM_EMOJIS.get("⏳", "5451732530048802485"),
    "Kassa": DEFAULT_CUSTOM_EMOJIS.get("💰", "5375296873982604963"),
    "Promo Kodlar": DEFAULT_CUSTOM_EMOJIS.get("🎁", "5199749070830197566"),
    "Audit Log": DEFAULT_CUSTOM_EMOJIS.get("🛡️", "5373173798633752502"),
    "Faollik Tahlili": DEFAULT_CUSTOM_EMOJIS.get("📊", "5431577498364158238"),
    "Yuborilgan reklamalar": DEFAULT_CUSTOM_EMOJIS.get("📢", "5199850887324902331"),
    "Bot Rejimi": DEFAULT_CUSTOM_EMOJIS.get("🛠️", "5199638831904596483"),
    "Nofaollarga Eslatma": DEFAULT_CUSTOM_EMOJIS.get("💤", "5215252253501301306"),
    "Premium Sozlamalar": DEFAULT_CUSTOM_EMOJIS.get("👑", "5467406098367521267"),
    "Eng past baholi kinolar (75+)": DEFAULT_CUSTOM_EMOJIS.get("📉", "5429518319243775957"),
    "Eng past baholi kinolar": DEFAULT_CUSTOM_EMOJIS.get("📉", "5429518319243775957"),
    "Aktivlik Grafigi": DEFAULT_CUSTOM_EMOJIS.get("📊", "5431577498364158238"),
    "Treyler Post Yuborish": DEFAULT_CUSTOM_EMOJIS.get("🎬", "5375464961822695044"),
    "Savat (3 kunlik)": DEFAULT_CUSTOM_EMOJIS.get("🗑", "5355021050637722984"),
    "Barcha Foydalanuvchilar": DEFAULT_CUSTOM_EMOJIS.get("👥", "5372926953978341366"),
    "Botni Bloklaganlar": DEFAULT_CUSTOM_EMOJIS.get("🚫", "5465665476971471368"),
    "Barcha Kanallarga Obuna Bo'lganlar": DEFAULT_CUSTOM_EMOJIS.get("✅", "5427009714745517609"),
    "Foydalanuvchi Qidirish": DEFAULT_CUSTOM_EMOJIS.get("🔍", "5188217332748527444"),
    "Kolleksiyalar": DEFAULT_CUSTOM_EMOJIS.get("📁", "5433653135799228968"),
    "Dashboard": DEFAULT_CUSTOM_EMOJIS.get("📊", "5431577498364158238"),
    "Premium Emojilar": DEFAULT_CUSTOM_EMOJIS.get("✨", "5472164874886846699"),

    # Foydalanuvchi menyusi
    "VIP Premium": DEFAULT_CUSTOM_EMOJIS.get("💎", "5471952986970267163"),
    "Kino qidirish": DEFAULT_CUSTOM_EMOJIS.get("🔍", "5188217332748527444"),
    "Menga mos kinolar": DEFAULT_CUSTOM_EMOJIS.get("🔥", "5420315771991497307"),
    "Saqlanganlar": DEFAULT_CUSTOM_EMOJIS.get("⭐️", "5435957248314579621"),
    "Tarixim": DEFAULT_CUSTOM_EMOJIS.get("🕐", "5413704112220949842"),
    "Tasodifiy Kino": DEFAULT_CUSTOM_EMOJIS.get("🎲", "5386782763288371963"),
    "Kino so'rash": DEFAULT_CUSTOM_EMOJIS.get("🎬", "5375464961822695044"),
    "Mening Ballarim": DEFAULT_CUSTOM_EMOJIS.get("💎", "5471952986970267163"),
    "Kunlik Bonus": DEFAULT_CUSTOM_EMOJIS.get("🎁", "5199749070830197566"),
    "Reytinglar": DEFAULT_CUSTOM_EMOJIS.get("🏆", "5409008750893734809"),
    "Profilim": DEFAULT_CUSTOM_EMOJIS.get("👑", "5467406098367521267"),
    "TOP Kinolar": DEFAULT_CUSTOM_EMOJIS.get("🔝", "5422354988103901774"),
    "To'lovlarim": DEFAULT_CUSTOM_EMOJIS.get("💳", "5280872069519654995"),
    "Tug'ilgan Kun": DEFAULT_CUSTOM_EMOJIS.get("🎂", "5370999492914976897"),
    "Yordam / Murojaat": DEFAULT_CUSTOM_EMOJIS.get("🆘", "5377316857231450742")
}


def clean_button_text(text: str) -> str:
    """Tugma matnidan oddiy yozilgan emojilarni olib tashlaydi"""
    if not text:
        return ""
    cleaned = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\ufe0f]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else text


def make_kb_btn(text: str, custom_emoji_id: str = None, emoji_char: str = None, **kwargs) -> KeyboardButton:
    """Tugmaga mos Telegram Premium Custom Emoji ID sini avtomatik biriktiruvchi yordamchi"""
    cid = custom_emoji_id
    if not cid and emoji_char:
        cid = get_custom_emoji_id(emoji_char) or get_custom_emoji_id_for_text(emoji_char)

    clean = clean_button_text(text)

    if not cid:
        cid = BUTTON_CUSTOM_EMOJIS.get(clean) or BUTTON_CUSTOM_EMOJIS.get(text)
    if not cid:
        cid = get_custom_emoji_id_for_text(text)

    if cid:
        return KeyboardButton(text=clean, icon_custom_emoji_id=cid, **kwargs)
    return KeyboardButton(text=clean, **kwargs)


def get_admin_menu():
    """Bosh Adminlar uchun ixcham, professional premium boshqaruv menyusi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                make_kb_btn("Kino qo'shish"),
                make_kb_btn("Kino o'chirish")
            ],
            [
                make_kb_btn("Kino tahrirlash"),
                make_kb_btn("Kino faylini yangilash")
            ],
            [
                make_kb_btn("Statistika"),
                make_kb_btn("Kino so'rovlari")
            ],
            [
                make_kb_btn("Reklama yuborish"),
                make_kb_btn("Rejalashtirilgan reklama")
            ],
            [
                make_kb_btn("Homiy Kanallar"),
                make_kb_btn("Zaxira (Backup)")
            ],
            [
                make_kb_btn("Foydalanuvchi Qidirish"),
                make_kb_btn("Barcha Foydalanuvchilar")
            ],
            [
                make_kb_btn("Premium Obunachilar"),
                make_kb_btn("Kassa")
            ],
            [
                make_kb_btn("Card"),
                make_kb_btn("Promo Kodlar")
            ],
            [
                make_kb_btn("Treyler Post Yuborish"),
                make_kb_btn("Kolleksiyalar")
            ],
            [
                make_kb_btn("Moderatorlar"),
                make_kb_btn("Savat (3 kunlik)")
            ],
            [
                make_kb_btn("Sozlamalar"),
                make_kb_btn("Premium Emojilar")
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
        row1.append(make_kb_btn("Kino qo'shish"))
        row1.append(make_kb_btn("Kino o'chirish"))
    if row1:
        keyboard.append(row1)

    # Qator 2: Kino tahrirlash, fayl yangilash
    row2_edit = []
    if permissions.get("add_movie", True):
        row2_edit.append(make_kb_btn("Kino tahrirlash"))
        row2_edit.append(make_kb_btn("Kino faylini yangilash"))
    if row2_edit:
        keyboard.append(row2_edit)

    # Qator 3: Statistika va Kino so'rovlari
    row2 = []
    if permissions.get("view_stats", True):
        row2.append(make_kb_btn("Statistika"))
        row2.append(make_kb_btn("Kino so'rovlari"))
    if row2:
        keyboard.append(row2)

    # Qator 4: Reklama va Rejalashtirilgan reklama
    row_broadcast = []
    if permissions.get("send_broadcast", False):
        row_broadcast.append(make_kb_btn("Reklama yuborish"))
        row_broadcast.append(make_kb_btn("Rejalashtirilgan reklama"))
    if row_broadcast:
        keyboard.append(row_broadcast)

    # Qator 5: Homiy kanallar va Zaxira (Backup)
    row3 = []
    if permissions.get("manage_sponsors", False):
        row3.append(make_kb_btn("Homiy Kanallar"))
    if permissions.get("backup_db", False):
        row3.append(make_kb_btn("Zaxira (Backup)"))
    if row3:
        keyboard.append(row3)

    # Qator 6: Trendlar
    row4 = []
    if permissions.get("view_trends", True):
        row4.append(make_kb_btn("Kino Trendlari"))
    if row4:
        keyboard.append(row4)

    # Agar hech qanday ruxsat yo'q bo'lsa, oddiy user menyusini qaytaramiz
    if not keyboard:
        return get_user_menu()

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_user_menu():
    """Oddiy foydalanuvchilar uchun ixcham va professional premium menyu"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                make_kb_btn("Kino qidirish"),
                make_kb_btn("VIP Premium")
            ],
            [
                make_kb_btn("TOP Kinolar"),
                make_kb_btn("Tasodifiy Kino")
            ],
            [
                make_kb_btn("Saqlanganlar"),
                make_kb_btn("Tarixim")
            ],
            [
                make_kb_btn("Kino so'rash"),
                make_kb_btn("Kunlik Bonus")
            ],
            [
                make_kb_btn("Reytinglar"),
                make_kb_btn("Mening Ballarim")
            ],
            [
                make_kb_btn("Profilim"),
                make_kb_btn("Yordam / Murojaat")
            ]
        ],
        resize_keyboard=True
    )
