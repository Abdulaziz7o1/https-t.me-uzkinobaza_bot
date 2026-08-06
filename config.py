import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    raise ValueError("BOT_TOKEN .env faylida ko'rsatilmagan!")

# Yagona Bosh Admin
ADMINS = [7140599182]

# Kanallar ro'yxatini olish
channels_raw = os.getenv("CHANNELS", "")
CHANNELS = []
if channels_raw:
    for channel in channels_raw.split(","):
        channel = channel.strip()
        if channel:
            # Agar ID bo'lsa (masalan -100...), uni int qilib olamiz
            if channel.startswith("-") and channel[1:].isdigit():
                CHANNELS.append(int(channel))
            else:
                CHANNELS.append(channel)

# Bot usernamesi (captionlarda ko'rsatish uchun)
BOT_USERNAME = os.getenv("BOT_USERNAME", "@uzkinobaza_bot")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@Abdulaziz7o1")

# Proxy settings (optional - agar Telegram bloklangan bo'lsa)
# Masalan: PROXY_URL=http://username:password@proxy-server:port
# yoki: PROXY_URL=socks5://username:password@proxy-server:port
PROXY_URL = os.getenv("PROXY_URL", "")

# Payment system settings
CLICK_SERVICE_ID = os.getenv("CLICK_SERVICE_ID", "")
CLICK_MERCHANT_ID = os.getenv("CLICK_MERCHANT_ID", "")
CLICK_SECRET_KEY = os.getenv("CLICK_SECRET_KEY", "")

PAYME_MERCHANT_ID = os.getenv("PAYME_MERCHANT_ID", "")
PAYME_SECRET_KEY = os.getenv("PAYME_SECRET_KEY", "")

# Admin payment verification (manual payment)
ADMIN_PAYMENT_CHAT_ID = os.getenv("ADMIN_PAYMENT_CHAT_ID", "")
