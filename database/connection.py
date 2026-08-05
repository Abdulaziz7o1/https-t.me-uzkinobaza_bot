import aiosqlite
import os
from datetime import datetime, timedelta

DB_PATH = "kino_bot.db"

# Simple in-memory cache with TTL
class SimpleCache:
    def __init__(self):
        self.cache = {}
        self.ttls = {}
    
    def get(self, key):
        if key in self.cache:
            if key in self.ttls:
                if datetime.now() > self.ttls[key]:
                    del self.cache[key]
                    del self.ttls[key]
                    return None
            return self.cache[key]
        return None
    
    def set(self, key, value, ttl_seconds=300):
        self.cache[key] = value
        self.ttls[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
        if key in self.ttls:
            del self.ttls[key]

    def clear(self):
        self.cache.clear()
        self.ttls.clear()

# Global cache instance
cache = SimpleCache()

def get_db():
    """Ma'lumotlar bazasiga ulanishni qaytaradi"""
    return aiosqlite.connect(DB_PATH)

async def init_db():
    """Barcha jadvallarni yaratish va bazani faollashtirish"""
    async with get_db() as db:
        # Users jadvali (role va status bilan)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                status TEXT DEFAULT 'active',
                role TEXT DEFAULT 'member',
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notify_points INTEGER DEFAULT 1,
                referral_rewarded INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Faqat 7140599182 ni Yagona Bosh Admin qilish, qolgan BARCHA foydalanuvchilarning admin/moderator roolini olib tashlash
        await db.execute("UPDATE users SET role = 'member' WHERE id != 7140599182")
        await db.execute("INSERT OR IGNORE INTO users (id, username, full_name, role) VALUES (7140599182, 'admin', 'Bosh Admin', 'admin')")
        await db.execute("UPDATE users SET role = 'admin' WHERE id = 7140599182")
        await db.commit()
        cache.clear()

        # Movies jadvali (views_count bilan)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                caption TEXT,
                views_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Eski test videosini bazadan to'liq tozalash
        await db.execute("DELETE FROM movies WHERE caption NOT LIKE '%Qimorda%' AND (caption IS NULL OR caption = '' OR file_id LIKE '%BAACAgI%')")
        await db.commit()
        
        # Favorites jadvali (tanlangan kinolar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                movie_id INTEGER,
                PRIMARY KEY (user_id, movie_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
            )
        """)
        
        # Ratings jadvali (1-5 yulduz)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER,
                movie_id INTEGER,
                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
            )
        """)
        
        # Requests jadvali (kino buyurtmalari)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Sponsor channels jadvali (homiy kanallar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sponsor_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT
            )
        """)
        
        # Moderator permissions jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS moderator_permissions (
                user_id INTEGER PRIMARY KEY,
                add_movie INTEGER DEFAULT 1,
                delete_movie INTEGER DEFAULT 1,
                view_stats INTEGER DEFAULT 1,
                send_broadcast INTEGER DEFAULT 0,
                manage_sponsors INTEGER DEFAULT 0,
                view_trends INTEGER DEFAULT 1,
                backup_db INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Comments jadvali (kino izohlari)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_id INTEGER,
                comment_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
            )
        """)

        # Scheduled broadcasts jadvali (rejalashtirilgan reklamalar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                send_at TIMESTAMP NOT NULL,
                is_sent INTEGER DEFAULT 0
            )
        """)

        # Users jadvaliga referal ustunlarini qo'shish (agar mavjud bo'lmasa)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN referrals_count INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
        except Exception:
            pass

        # Ball tizimi uchun points ustuni
        try:
            await db.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
        except Exception:
            pass

        # Nofaol a'zolarni tozalash uchun oxirgi faollik ustuni (constant default yordamida)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_active_at TIMESTAMP DEFAULT '2026-07-20 00:00:00'")
        except Exception:
            pass

        # Shaxsiy sozlamalar — ball bildirishnomalari
        try:
            await db.execute("ALTER TABLE users ADD COLUMN notify_points INTEGER DEFAULT 1")
        except Exception:
            pass

        # Referal mukofoti berilganini tekshirish ustuni
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referral_rewarded INTEGER DEFAULT 0")
        except Exception:
            pass

        # Reyting jadvaliga qo'shilgan vaqt ustuni
        try:
            await db.execute("ALTER TABLE ratings ADD COLUMN created_at TIMESTAMP DEFAULT '2026-08-04 00:00:00'")
        except Exception:
            pass

        # Kunlik ballarni hisobga olish jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_points (
                user_id INTEGER,
                date TEXT,
                points INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        """)

        # Kunlik bonus kino limitlari jadvali (faqat o'sha kunga beriladigan qo'shimcha limit)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_bonus_limits (
                user_id INTEGER,
                date TEXT,
                bonus_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        """)

        # Shubhali harakatlar jurnali (abuse logs) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS abuse_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Izohlar holati (moderatsiya uchun: 'approved' yoki 'pending')
        try:
            await db.execute("ALTER TABLE comments ADD COLUMN status TEXT DEFAULT 'approved'")
        except Exception:
            pass

        # Kinoni qaysi admin/moderator qo'shgani
        try:
            await db.execute("ALTER TABLE movies ADD COLUMN added_by INTEGER")
        except Exception:
            pass

        # Abuse logda admin_id ustuni
        try:
            await db.execute("ALTER TABLE abuse_logs ADD COLUMN admin_id INTEGER")
        except Exception:
            pass

        # Kun kinosi logi jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_movie_log (
                date TEXT PRIMARY KEY,
                movie_id INTEGER
            )
        """)

        # Bot sozlamalari jadvali (promo xabar va boshqa global o'zgaruvchilar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # YouTube kanallari jadvali (homiy YouTube kanallari)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS youtube_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT,
                channel_url TEXT
            )
        """)

        # Saqlangan kinolar (Favorites) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER,
                movie_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_id)
            )
        """)

        # Izohlar likelari jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS comment_likes (
                comment_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (comment_id, user_id)
            )
        """)

        # Kunlik bonuslar jurnali jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_claims (
                user_id INTEGER,
                claim_date TEXT,
                PRIMARY KEY (user_id, claim_date)
            )
        """)

        # Premium / VIP foydalanuvchi ustunlari
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_premium INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN premium_until TIMESTAMP")
        except Exception:
            pass

        # Foydalanuvchi YouTube obunasi jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS youtube_subscriptions (
                user_id INTEGER,
                youtube_channel_id INTEGER,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, youtube_channel_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (youtube_channel_id) REFERENCES youtube_channels(id) ON DELETE CASCADE
            )
        """)

        # Premium obunalar jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium_subscriptions (
                user_id INTEGER PRIMARY KEY,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                plan TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Kunlik kino limiti jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_movie_limits (
                user_id INTEGER,
                date TEXT DEFAULT (date('now')),
                movies_watched INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Qo'llab-quvvatlash / Tickets jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                reply_text TEXT,
                admin_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Admin PIN jadvali (2FA xavfsizlik)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_pins (
                admin_id INTEGER PRIMARY KEY,
                pin_hash TEXT NOT NULL,
                last_changed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                failed_attempts INTEGER DEFAULT 0,
                blocked_until TIMESTAMP
            )
        """)

        # Broadcast click tracker jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(broadcast_id, user_id)
            )
        """)

        # Foydalanuvchi Watch History
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watch_history (
                user_id INTEGER,
                movie_id INTEGER,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, movie_id)
            )
        """)

        # Users jadvaliga birthday ustuni qo'shish
        try:
            await db.execute("ALTER TABLE users ADD COLUMN birthday TEXT")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_birthday_bonus_year INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN pin_failed_attempts INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN warning_count INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN ban_stage INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE users ADD COLUMN temp_ban_until TEXT")
        except Exception:
            pass

        # Movies jadvaliga muddat (expiry) ustunlarini qo'shish
        try:
            await db.execute("ALTER TABLE movies ADD COLUMN expires_at TEXT")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE movies ADD COLUMN is_expired INTEGER DEFAULT 0")
        except Exception:
            pass

        # To'lovlar yozuvlari (Kassa) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                plan TEXT NOT NULL,
                confirmed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Promo kodlar jadvali (Premium skidka va mukofotlar)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                reward_type TEXT NOT NULL, -- 'days' (kun), 'discount' (skidka %), 'points' (ball)
                reward_value INTEGER NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                expires_at TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Promo kodlar ishlatilishi jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (code, user_id),
                FOREIGN KEY (code) REFERENCES promo_codes(code) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        try:
            await db.execute("ALTER TABLE promo_uses ADD COLUMN is_consumed INTEGER DEFAULT 0")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE promo_uses ADD COLUMN reward_type TEXT")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE promo_uses ADD COLUMN discount_pct INTEGER DEFAULT 0")
        except Exception:
            pass

        # 100% dan yuqori skidkalarni 100% ga to'g'rilash va limit to'lgan promo kodlarni avtomatik o'chirish
        try:
            await db.execute("UPDATE promo_codes SET reward_value = 100 WHERE reward_type = 'discount' AND reward_value > 100")
            await db.execute("DELETE FROM promo_codes WHERE used_count >= max_uses")
            await db.execute(
                """UPDATE premium_subscriptions 
                   SET plan = '1 kunlik' 
                   WHERE plan = '1 haftalik' 
                     AND (julianday(end_date) - julianday(start_date)) <= 1.5"""
            )
            await db.commit()
        except Exception:
            pass

        # Movies jadvaliga parolli va homiy bot ustunlarini qo'shish
        try:
            await db.execute("ALTER TABLE movies ADD COLUMN passcode TEXT")
        except Exception:
            pass

        try:
            await db.execute("ALTER TABLE movies ADD COLUMN sponsor_bot_url TEXT")
        except Exception:
            pass

        # Kino reaksiya tugmalari (👍 👎 🔥) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movie_reactions (
                movie_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reaction TEXT NOT NULL,
                PRIMARY KEY (movie_id, user_id),
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Kino boyicha shikoyatlar (faylda nuqson bor) jadvali
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movie_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        await db.commit()


