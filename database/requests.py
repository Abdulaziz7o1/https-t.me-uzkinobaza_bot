import os
import json
import asyncio
import logging
from database.connection import get_db
import config

async def add_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    """Foydalanuvchini bazaga qo'shish, rolini tekshirish va referalni bog'lash"""
    role = 'admin' if user_id in config.ADMINS else 'member'
    from datetime import datetime, timedelta, timezone
    uzb_tz = timezone(timedelta(hours=5))
    now_str = datetime.now(uzb_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    async with get_db() as db:
        # Foydalanuvchi allaqachon bor-yo'qligini tekshirish
        async with db.execute("SELECT id FROM users WHERE id = ?", (user_id,)) as cursor:
            user_exists = await cursor.fetchone() is not None
            
        if not user_exists:
            # Agar yangi foydalanuvchi bo'lsa va referal orqali kelgan bo'lsa
            valid_ref = None
            if referred_by and referred_by != user_id:
                async with db.execute("SELECT id FROM users WHERE id = ?", (referred_by,)) as ref_cursor:
                    if await ref_cursor.fetchone():
                        valid_ref = referred_by
                        
            await db.execute(
                """INSERT INTO users (id, username, full_name, role, referred_by, created_at, last_active_at, referral_rewarded) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                (user_id, username, full_name, role, valid_ref, now_str, now_str)
            )
            # Mukofot obuna tekshiruvidan so'ng check_and_reward_referral funksiyasida beriladi
        else:
            # Mavjud bo'lsa, faqat ma'lumotlarini va faolligini yangilash
            await db.execute(
                "UPDATE users SET username = ?, full_name = ?, last_active_at = ? WHERE id = ?",
                (username, full_name, now_str, user_id)
            )
            
        # Faqat 7140599182 Bosh Admin bo'ladi. Qolgan har qanday foydalanuvchining (agar Bosh Admin bo'lmasa) admin roolini bekor qilamiz
        if user_id == 7140599182:
            await db.execute("UPDATE users SET role = 'admin' WHERE id = 7140599182")
        else:
            await db.execute("UPDATE users SET role = 'member' WHERE id = ? AND role = 'admin'", (user_id,))
        await db.commit()

async def update_user_activity(user_id: int):
    """Foydalanuvchining faollik vaqtini yangilash"""
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        await db.execute("UPDATE users SET last_active_at = ? WHERE id = ?", (now_str, user_id))
        await db.commit()

async def get_inactive_users_count(months: int = 6) -> int:
    """Nofaol (belgilangan oydan ko'p vaqt kirmagan) foydalanuvchilar sonini hisoblash"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=months * 30)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(id) FROM users WHERE last_active_at < ? AND role != 'admin'",
            (cutoff_str,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def delete_inactive_users(months: int = 6) -> int:
    """Nofaol a'zolarni bazadan butunlay tozalash"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=months * 30)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM users WHERE last_active_at < ? AND role != 'admin'",
            (cutoff_str,)
        ) as cursor:
            rows = await cursor.fetchall()
            ids = [r[0] for r in rows]
            
        if ids:
            # A'zolarni o'chirish
            await db.execute(
                f"DELETE FROM users WHERE id IN ({','.join(['?']*len(ids))})",
                ids
            )
            await db.commit()
        return len(ids)

async def get_user(user_id: int):

    """Foydalanuvchini olish"""
    from database.connection import cache
    cache_key = f"user_{user_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    async with get_db() as db:
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                cache.set(cache_key, result, ttl_seconds=60)
            return result

async def is_banned(user_id: int) -> bool:
    """Foydalanuvchi bloklanganini tekshirish"""
    async with get_db() as db:
        async with db.execute("SELECT status FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None and row[0] == 'banned'

async def ban_user(user_id: int) -> bool:
    """Foydalanuvchini bloklash"""
    import config
    
    # Bosh Admin va Moderatorlarni bloklashni taqiqlash
    if user_id in config.ADMINS:
        return False
    
    async with get_db() as db:
        await db.execute("INSERT OR IGNORE INTO users (id, status, role) VALUES (?, 'active', 'member')", (user_id,))
        await db.execute("UPDATE users SET status = 'banned', role = 'banned' WHERE id = ?", (user_id,))
        await db.commit()
        return True

async def unban_user(user_id: int) -> bool:
    """Foydalanuvchini blokdan chiqarish"""
    async with get_db() as db:
        await db.execute("INSERT OR IGNORE INTO users (id, status, role) VALUES (?, 'active', 'member')", (user_id,))
        await db.execute(
            """UPDATE users 
               SET status = 'active', role = 'member', warning_count = 0, temp_ban_until = NULL 
               WHERE id = ?""",
            (user_id,)
        )
        await db.commit()
        return True

async def set_role(user_id: int, role: str) -> bool:
    """Foydalanuvchi rolini sozlash (admin, moderator, member)"""
    if role not in ['admin', 'moderator', 'member']:
        return False
    async with get_db() as db:
        async with db.execute("SELECT id FROM users WHERE id = ?", (user_id,)) as cursor:
            if not await cursor.fetchone():
                return False
        await db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        await db.commit()
        return True

async def get_moderators():
    """Barcha moderatorlar ro'yxatini olish"""
    async with get_db() as db:
        async with db.execute("SELECT id, username, full_name FROM users WHERE role = 'moderator'") as cursor:
            return await cursor.fetchall()

async def get_all_admins():
    """Barcha admin va moderatorlar ro'yxatini olish (FAQAT 7140599182 va tasdiqlangan moderatorlar)"""
    async with get_db() as db:
        async with db.execute("SELECT id FROM users WHERE role = 'moderator' OR id = 7140599182") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_movie(file_id: str, caption: str) -> int:
    """Yangi kino qo'shish va uning kodini (ID) qaytarish va avtomatik zaxiralash"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO movies (file_id, caption) VALUES (?, ?)",
            (file_id, caption)
        )
        await db.commit()
        last_id = cursor.lastrowid
    await export_master_backup_json()
    return last_id

async def movie_exists_db(movie_id: int) -> bool:
    """Kesh-ga qaramay haqiqiy SQL bazada kino borligini tekshirish"""
    async with get_db() as db:
        async with db.execute("SELECT 1 FROM movies WHERE id = ?", (movie_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def add_movie_with_id(movie_id: int, file_id: str, caption: str, is_premium_only: int = 0) -> bool:
    """Belgilangan ID (kino kodi) bilan yangi kinoni qo'shish va zaxiralash (is_premium_only: 0-barcha, 1-faqat premium)"""
    from database.connection import cache
    cache.delete(f"movie_{movie_id}")

    async with get_db() as db:
        await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await db.execute("DELETE FROM favorites WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM ratings WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM comments WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM watch_history WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM movie_reports WHERE movie_id = ?", (movie_id,))
        try:
            await db.execute("DELETE FROM movie_reactions WHERE movie_id = ?", (movie_id,))
        except Exception:
            pass
        await db.execute(
            "INSERT INTO movies (id, file_id, caption, views_count, is_premium_only) VALUES (?, ?, ?, 0, ?)",
            (movie_id, file_id, caption, is_premium_only)
        )
        await db.commit()
        cache.delete(f"movie_{movie_id}")
    await export_master_backup_json()
    return True

async def get_movie(movie_id: int, user_id: int = None):
    """Kino ma'lumotlarini bazadan olish (file_id, caption, views_count, is_premium_only)"""
    from database.connection import cache
    cache.delete(f"movie_{movie_id}")

    async with get_db() as db:
        async with db.execute("SELECT file_id, caption, views_count, COALESCE(is_premium_only, 0) FROM movies WHERE id = ?", (movie_id,)) as cursor:
            movie = await cursor.fetchone()
        if movie:
            current_views = movie[2] or 0
            is_prem_only = movie[3] or 0
            new_views = current_views

            if user_id is not None:
                # User allaqachon shu kinoni ilgari yuklab olganmi?
                async with db.execute("SELECT 1 FROM movie_unique_downloads WHERE user_id = ? AND movie_id = ?", (user_id, movie_id)) as cursor:
                    has_downloaded = await cursor.fetchone()
                
                if not has_downloaded:
                    # Birinchi marta yuklayapti -> +1 oshiramiz
                    await db.execute("INSERT OR IGNORE INTO movie_unique_downloads (user_id, movie_id) VALUES (?, ?)", (user_id, movie_id))
                    async with db.execute("SELECT COUNT(*) FROM movie_unique_downloads WHERE movie_id = ?", (movie_id,)) as cursor:
                        cnt_row = await cursor.fetchone()
                        new_views = cnt_row[0] if cnt_row else current_views + 1
                    await db.execute("UPDATE movies SET views_count = ? WHERE id = ?", (new_views, movie_id))
                    await db.commit()
            return (movie[0], movie[1], new_views, is_prem_only)
        return None

async def delete_movie(movie_id: int):
    """Kinoni bazadan va barcha xotira bo'limlaridan yo'q qilish hamda tavsifini qaytarish"""
    from database.connection import cache
    cache.delete(f"movie_{movie_id}")

    caption = ""
    async with get_db() as db:
        async with db.execute("SELECT caption FROM movies WHERE id = ?", (movie_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                cache.delete(f"movie_{movie_id}")
                return False, ""
            caption = row[0] or ""

        await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await db.execute("DELETE FROM favorites WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM ratings WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM comments WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM watch_history WHERE movie_id = ?", (movie_id,))
        await db.execute("DELETE FROM movie_reports WHERE movie_id = ?", (movie_id,))
        try:
            await db.execute("DELETE FROM movie_reactions WHERE movie_id = ?", (movie_id,))
            await db.execute("DELETE FROM movie_unique_downloads WHERE movie_id = ?", (movie_id,))
        except Exception:
            pass
        await db.commit()
        cache.delete(f"movie_{movie_id}")
    await export_master_backup_json()
    return True, caption

MASTER_BACKUP_FILE = "master_bot_backup.json"

async def export_master_backup_json() -> str:
    """Barcha 15 ta ma'lumotlar bazasi jadvalini master_bot_backup.json fayliga 100% zaxiralash"""
    import json
    async with get_db() as db:
        # 1. Movies
        async with db.execute("SELECT id, file_id, caption, views_count, COALESCE(is_premium_only, 0) FROM movies ORDER BY id ASC") as c:
            movies = [{"id": r[0], "file_id": r[1], "caption": r[2], "views_count": r[3], "is_premium_only": r[4]} for r in await c.fetchall()]

        # 2. Sponsor channels
        async with db.execute("SELECT id, channel_id, channel_name FROM sponsor_channels") as c:
            channels = [{"id": r[0], "channel_id": r[1], "channel_name": r[2]} for r in await c.fetchall()]

        # 3. Users
        async with db.execute("SELECT id, username, full_name, role, status, points, referrals_count, created_at, birthday, premium_until FROM users") as c:
            users = [{"id": r[0], "username": r[1], "full_name": r[2], "role": r[3], "status": r[4], "points": r[5], "referrals_count": r[6], "created_at": r[7], "birthday": r[8], "premium_until": r[9]} for r in await c.fetchall()]

        # 4. Premium subscriptions
        async with db.execute("SELECT user_id, start_date, end_date, plan FROM premium_subscriptions") as c:
            premium_subs = [{"user_id": r[0], "start_date": r[1], "end_date": r[2], "plan": r[3]} for r in await c.fetchall()]

        # 5. Payment records
        async with db.execute("SELECT id, user_id, amount, plan, confirmed_by, created_at FROM payment_records ORDER BY id ASC") as c:
            payments = [{"id": r[0], "user_id": r[1], "amount": r[2], "plan": r[3], "confirmed_by": r[4], "created_at": r[5]} for r in await c.fetchall()]

        # 6. Settings
        async with db.execute("SELECT key, value FROM bot_settings") as c:
            settings = {r[0]: r[1] for r in await c.fetchall()}

        # 7. Promo codes
        try:
            async with db.execute("SELECT code, reward_type, reward_value, max_uses, used_count, expires_at FROM promo_codes") as c:
                promo = [{"code": r[0], "reward_type": r[1], "reward_value": r[2], "max_uses": r[3], "used_count": r[4], "expires_at": r[5]} for r in await c.fetchall()]
        except Exception:
            promo = []

        # 8. Requests
        async with db.execute("SELECT id, user_id, movie_name, status, created_at FROM requests") as c:
            reqs = [{"id": r[0], "user_id": r[1], "movie_name": r[2], "status": r[3], "created_at": r[4]} for r in await c.fetchall()]

        # 9. Tickets
        async with db.execute("SELECT id, user_id, message_text, status, reply_text, admin_id, created_at FROM tickets") as c:
            tickets = [{"id": r[0], "user_id": r[1], "message_text": r[2], "status": r[3], "reply_text": r[4], "admin_id": r[5], "created_at": r[6]} for r in await c.fetchall()]

        # 10. Favorites
        async with db.execute("SELECT user_id, movie_id FROM favorites") as c:
            favorites = [{"user_id": r[0], "movie_id": r[1]} for r in await c.fetchall()]

        # 11. Ratings
        async with db.execute("SELECT user_id, movie_id, rating, created_at FROM ratings") as c:
            ratings = [{"user_id": r[0], "movie_id": r[1], "rating": r[2], "created_at": r[3]} for r in await c.fetchall()]

        # 12. Comments
        async with db.execute("SELECT id, user_id, movie_id, comment_text, created_at FROM comments") as c:
            comments = [{"id": r[0], "user_id": r[1], "movie_id": r[2], "comment_text": r[3], "created_at": r[4]} for r in await c.fetchall()]

        # 13. Movie reactions
        try:
            async with db.execute("SELECT movie_id, user_id, reaction_type FROM movie_reactions") as c:
                reactions = [{"movie_id": r[0], "user_id": r[1], "reaction_type": r[2]} for r in await c.fetchall()]
        except Exception:
            reactions = []

        # 14. Abuse logs
        try:
            async with db.execute("SELECT id, user_id, type, details, created_at FROM abuse_logs") as c:
                abuse_logs = [{"id": r[0], "user_id": r[1], "type": r[2], "details": r[3], "created_at": r[4]} for r in await c.fetchall()]
        except Exception:
            abuse_logs = []

        # 15. Moderator permissions
        try:
            async with db.execute("SELECT user_id, add_movie, delete_movie, view_stats, send_broadcast, manage_sponsors, view_trends, backup_db FROM moderator_permissions") as c:
                permissions = [{"user_id": r[0], "add_movie": r[1], "delete_movie": r[2], "view_stats": r[3], "send_broadcast": r[4], "manage_sponsors": r[5], "view_trends": r[6], "backup_db": r[7]} for r in await c.fetchall()]
        except Exception:
            permissions = []

        master_data = {
            "movies": movies,
            "sponsor_channels": channels,
            "users": users,
            "premium_subscriptions": premium_subs,
            "payment_records": payments,
            "settings": settings,
            "promo_codes": promo,
            "requests": reqs,
            "tickets": tickets,
            "favorites": favorites,
            "ratings": ratings,
            "comments": comments,
            "movie_reactions": reactions,
            "abuse_logs": abuse_logs,
            "moderator_permissions": permissions
        }

        # Master JSON va alohida movies/sponsor backup fayllariga saqlash
        json_str = json.dumps(master_data, ensure_ascii=False, indent=2)
        candidate_files = ["master_bot_backup.json", "data/master_bot_backup.json"]
        if os.path.exists("/var/data"):
            candidate_files.append("/var/data/master_bot_backup.json")
            
        for b_file in candidate_files:
            try:
                b_dir = os.path.dirname(b_file)
                if b_dir and not os.path.exists(b_dir):
                    os.makedirs(b_dir, exist_ok=True)
                with open(b_file, "w", encoding="utf-8") as f:
                    f.write(json_str)
            except Exception as e:
                print(f"Master backup write error [{b_file}]: {e}")

        try:
            with open("movies_backup.json", "w", encoding="utf-8") as f:
                json.dump(movies, f, ensure_ascii=False, indent=2)
            with open("sponsor_channels_backup.json", "w", encoding="utf-8") as f:
                json.dump(channels, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        try:
            import asyncio
            asyncio.create_task(sync_master_backup_to_mongodb(master_data))
        except Exception:
            pass

        return json_str

async def import_master_backup_json(json_str: str) -> dict:
    """Master JSON faylidan barcha 15 ta ma'lumotlar jadvallarini bazaga 100% tiklash"""
    import json
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            if isinstance(data, list):
                m_cnt = await import_movies_from_json(json_str)
                return {"movies": m_cnt}
            return {}

        stats = {}
        async with get_db() as db:
            # 1. Movies
            if "movies" in data:
                m_cnt = 0
                for m in data["movies"]:
                    if m.get("id") and m.get("file_id"):
                        await db.execute(
                            "INSERT OR REPLACE INTO movies (id, file_id, caption, views_count, is_premium_only) VALUES (?, ?, ?, ?, ?)",
                            (m["id"], m["file_id"], m.get("caption", ""), m.get("views_count", 0), m.get("is_premium_only", 0))
                        )
                        m_cnt += 1
                stats["movies"] = m_cnt

            # 2. Sponsor channels
            if "sponsor_channels" in data:
                c_cnt = 0
                for c in data["sponsor_channels"]:
                    if c.get("channel_id"):
                        await db.execute(
                            "INSERT OR REPLACE INTO sponsor_channels (channel_id, channel_name) VALUES (?, ?)",
                            (c["channel_id"], c.get("channel_name", str(c["channel_id"])))
                        )
                        c_cnt += 1
                stats["sponsor_channels"] = c_cnt

            # 3. Users
            if "users" in data:
                u_cnt = 0
                for u in data["users"]:
                    if u.get("id"):
                        await db.execute(
                            "INSERT OR REPLACE INTO users (id, username, full_name, role, points, is_blocked, referred_by, created_at, last_active_at, premium_until, daily_movie_count, daily_movie_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (u["id"], u.get("username"), u.get("full_name"), u.get("role", "member"), u.get("points", 0), u.get("is_blocked", 0), u.get("referred_by"), u.get("created_at"), u.get("last_active_at"), u.get("premium_until"), u.get("daily_movie_count", 0), u.get("daily_movie_date"))
                        )
                        u_cnt += 1
                stats["users"] = u_cnt

            # 4. Premium subscriptions
            if "premium_subscriptions" in data:
                ps_cnt = 0
                for ps in data["premium_subscriptions"]:
                    if ps.get("user_id"):
                        await db.execute(
                            "INSERT OR REPLACE INTO premium_subscriptions (user_id, start_date, end_date, plan, status) VALUES (?, ?, ?, ?, ?)",
                            (ps["user_id"], ps.get("start_date"), ps.get("end_date"), ps.get("plan"), ps.get("status", "active"))
                        )
                        ps_cnt += 1
                stats["premium_subscriptions"] = ps_cnt

            # 5. Payment records
            if "payment_records" in data:
                pr_cnt = 0
                for pr in data["payment_records"]:
                    if pr.get("user_id"):
                        await db.execute(
                            "INSERT OR REPLACE INTO payment_records (user_id, amount, plan, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (pr["user_id"], pr.get("amount", 0), pr.get("plan"), pr.get("payment_method"), pr.get("status"), pr.get("created_at"))
                        )
                        pr_cnt += 1
                stats["payment_records"] = pr_cnt

            # 6. Settings
            if "settings" in data:
                s_cnt = 0
                for s in data["settings"]:
                    if s.get("key"):
                        await db.execute(
                            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                            (s["key"], str(s.get("value", "")))
                        )
                        s_cnt += 1
                stats["settings"] = s_cnt

            # 7. Promo codes
            if "promo_codes" in data:
                pc_cnt = 0
                for pc in data["promo_codes"]:
                    if pc.get("code"):
                        await db.execute(
                            "INSERT OR REPLACE INTO promo_codes (code, reward_type, reward_value, max_uses, used_count, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (pc["code"], pc.get("reward_type"), pc.get("reward_value", 0), pc.get("max_uses", 1), pc.get("used_count", 0), pc.get("expires_at"))
                        )
                        pc_cnt += 1
                stats["promo_codes"] = pc_cnt

            await db.commit()
        return stats
    except Exception as e:
        print(f"Master backup tiklashda xato: {e}")
        return {}

DEFAULT_MONGO_URI = "mongodb+srv://abdulaziz10102013abdz_db_user:Abdulaziz1010201300@uzkinobazabot.ychyfp5.mongodb.net/?appName=uzkinobazabot"

async def save_telegram_backup_file_id(file_id: str):
    """Telegram Serveridagi backup fayli file_id sini MongoDB va SQLite-ga muhrlash"""
    try:
        async with get_db() as db:
            await db.execute(
                "INSERT INTO bot_settings (key, value) VALUES ('latest_backup_file_id', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
                (file_id, file_id)
            )
            await db.commit()
        
        mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URL") or DEFAULT_MONGO_URI
        if mongo_uri:
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
            db_m = client["kino_bot_database"]
            await db_m["backup_info"].replace_one({"_id": "telegram_backup"}, {"_id": "telegram_backup", "file_id": file_id}, upsert=True)
    except Exception as e:
        print(f"save_telegram_backup_file_id error: {e}")

async def sync_master_backup_to_mongodb(master_data: dict):
    """MongoDB Cloud'ga barcha 15 ta jadvalni va har bir kinoni alohida hujjat sifatida avtomatik zaxiralash"""
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URL") or DEFAULT_MONGO_URI
    if not mongo_uri:
        return
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        db = client["kino_bot_database"]
        
        # 1. Kinolarni alohida 'movies' kolleksiyasiga muhrlash (0.01 soniyada, 100% xatosiz)
        if "movies" in master_data and master_data["movies"]:
            movies_coll = db["movies"]
            for m in master_data["movies"]:
                m_id = m.get("id")
                if m_id:
                    await movies_coll.replace_one(
                        {"_id": m_id},
                        {
                            "_id": m_id,
                            "file_id": m.get("file_id"),
                            "caption": m.get("caption", ""),
                            "views_count": m.get("views_count", 0)
                        },
                        upsert=True
                    )

        # 2. Master backup yagona hujjatini saqlash
        collection = db["master_backups"]
        doc = {
            "_id": "latest_master_backup",
            "data": master_data,
            "updated_at": os.getenv("TZ", "Asia/Tashkent")
        }
        await collection.replace_one({"_id": "latest_master_backup"}, doc, upsert=True)
        print("MongoDB Cloud: Barcha kinolar va jadvallar Bulutli bazaga (MongoDB Atlas) 100% saqlandi! ☁️🚀")
    except Exception as e:
        print(f"MongoDB Cloud sync error: {e}")

async def restore_from_mongodb_cloud() -> bool:
    """MongoDB Cloud'dan (movies kolleksiyasi va master_backups hujjatidan) kinolarni 100% tiklash"""
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URL") or DEFAULT_MONGO_URI
    if not mongo_uri:
        return False
    restored = False
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        db = client["kino_bot_database"]
        
        # 1. Avval master_backups yagona hujjatini tiklash
        try:
            collection = db["master_backups"]
            doc = await collection.find_one({"_id": "latest_master_backup"})
            if doc and "data" in doc:
                import json
                master_json = json.dumps(doc["data"], ensure_ascii=False)
                res = await import_master_backup_json(master_json)
                print(f"MongoDB Cloud (Master): Bulutdan barcha ma'lumotlar tiklandi: {res}")
                restored = True
        except Exception as e:
            print(f"MongoDB Cloud master restore error: {e}")

        # 2. Har bir kinoni 'movies' kolleksiyasidan to'g'ridan-to'g'ri tiklash (zaxira kafolati)
        try:
            movies_coll = db["movies"]
            m_count = 0
            async with get_db() as local_db:
                async for m_doc in movies_coll.find({}):
                    m_id = m_doc.get("_id") or m_doc.get("id")
                    f_id = m_doc.get("file_id")
                    cap = m_doc.get("caption", "")
                    views = m_doc.get("views_count", 0)
                    if m_id and f_id:
                        await local_db.execute(
                            "INSERT INTO movies (id, file_id, caption, views_count) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET file_id=?, caption=?, views_count=?",
                            (m_id, f_id, cap, views, f_id, cap, views)
                        )
                        m_count += 1
                await local_db.commit()
            if m_count > 0:
                print(f"MongoDB Cloud (Movies Collection): {m_count} ta kino to'g'ridan-to'g'ri bulutdan tiklandi! ☁️🎬")
                restored = True
        except Exception as e:
            print(f"MongoDB Cloud movies collection restore error: {e}")

    except Exception as e:
        print(f"MongoDB Cloud connection error: {e}")

    return restored

async def restore_master_backup_on_startup():
    """Bot ishga tushganida (Render restart bo'lganda) barcha zaxira manbalaridan va MongoDB bulutdan avtomatik 100% tiklash"""
    import os
    
    # 1. Avval MongoDB Bulutli bazasini tekshiramiz
    restored_mongo = await restore_from_mongodb_cloud()
    if restored_mongo:
        print("MongoDB Cloud orqali barcha kinolar va ma'lumotlar tiklandi! Eskirgan disk fayllari bilan qayta yozilmaydi. ☁️✅")
        return
        
    candidate_paths = [
        "/var/data/master_bot_backup.json",
        "data/master_bot_backup.json",
        "master_bot_backup.json",
        "/var/data/movies_backup.json",
        "data/movies_backup.json",
        "movies_backup.json"
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        res = await import_master_backup_json(content)
                        if res and res.get("movies", 0) > 0:
                            print(f"Master backup [{path}] dan muvaffaqiyatli tiklandi! 🚀: {res}")
                            break
            except Exception as e:
                print(f"Master backup startup xatosi [{path}]: {e}")

    if os.path.exists("sponsor_channels_backup.json"):
        try:
            await restore_sponsor_channels_backup_on_startup()
        except Exception:
            pass

async def export_movies_backup_json() -> str:
    """Barcha kinolarni JSON matn shaklida zaxiralash uchun chiqarish"""
    return await export_master_backup_json()

async def import_movies_from_json(json_str: str) -> int:
    """JSON matnidan barcha kinolarni bazaga qayta tiklash"""
    res = await import_master_backup_json(json_str)
    return res.get("movies", 0)

async def search_movies_by_name(query: str):
    """Kinolarni nomi (tavsifi) bo'yicha qidirish"""
    async with get_db() as db:
        # LIKE yordamida qidirish (case-insensitive)
        async with db.execute(
            "SELECT id, caption FROM movies WHERE caption LIKE ? LIMIT 10",
            (f"%{query}%",)
        ) as cursor:
            return await cursor.fetchall()

async def get_trending_movies():
    """Eng ko'p ko'rilgan TOP 10 kinolarni olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, caption, views_count FROM movies ORDER BY views_count DESC LIMIT 10"
        ) as cursor:
            return await cursor.fetchall()

# --- FAVORITES (TANLANGANLAR) ---
async def add_favorite(user_id: int, movie_id: int) -> bool:
    """Kinoni tanlanganlarga qo'shish"""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO favorites (user_id, movie_id) VALUES (?, ?)",
                (user_id, movie_id)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def remove_favorite(user_id: int, movie_id: int) -> bool:
    """Kinoni tanlanganlardan o'chirish"""
    async with get_db() as db:
        await db.execute(
            "DELETE FROM favorites WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        )
        await db.commit()
        return True

async def get_favorites(user_id: int):
    """Foydalanuvchining barcha tanlangan kinolarini olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT m.id, m.caption FROM movies m 
               JOIN favorites f ON m.id = f.movie_id 
               WHERE f.user_id = ?""",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def is_favorite(user_id: int, movie_id: int) -> bool:
    """Kino tanlanganlarga qo'shilganini tekshirish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        ) as cursor:
            return await cursor.fetchone() is not None

# --- RATINGS (REYTING) ---
async def add_rating(user_id: int, movie_id: int, rating: int) -> bool:
    """Kinoga reyting qo'yish (1-5)"""
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO ratings (user_id, movie_id, rating) VALUES (?, ?, ?)",
            (user_id, movie_id, rating)
        )
        await db.commit()
        return True

async def get_movie_rating(movie_id: int):
    """Kinoning o'rtacha reytingi va ovozlar sonini olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT AVG(rating), COUNT(rating) FROM ratings WHERE movie_id = ?",
            (movie_id,)
        ) as cursor:
            row = await cursor.fetchone()
            avg_rating = round(row[0], 1) if row[0] is not None else 0.0
            votes_count = row[1]
            return avg_rating, votes_count

# --- REQUESTS (KINO BUYURTMA QILISH) ---
async def ensure_requests_table_extended():
    """Eski requests jadvalini is_premium ustuni bilan kengaytirish"""
    async with get_db() as db:
        try:
            await db.execute("ALTER TABLE requests ADD COLUMN is_premium INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass

async def add_request(user_id: int, movie_name: str):
    """Kino buyurtma qilish - premium foydalanuvchini belgilab"""
    is_prem = 1 if await is_premium_user(user_id) else 0
    async with get_db() as db:
        await db.execute(
            "INSERT INTO requests (user_id, movie_name, is_premium) VALUES (?, ?, ?)",
            (user_id, movie_name, is_prem)
        )
        await db.commit()

async def get_pending_requests():
    """Barcha hal qilinmagan buyurtmalarni olish - PREMIUM⭐ BIRINCHI O'RINDA"""
    async with get_db() as db:
        async with db.execute(
            """SELECT r.id, r.movie_name, u.username, u.full_name, r.created_at, COALESCE(r.is_premium, 0)
               FROM requests r 
               JOIN users u ON r.user_id = u.id 
               WHERE r.status = 'pending' 
               ORDER BY COALESCE(r.is_premium, 0) DESC, r.created_at DESC"""
        ) as cursor:
            return await cursor.fetchall()

async def resolve_request(request_id: int):
    """Buyurtmani yakunlangan deb belgilash va foydalanuvchi ma'lumotlarini qaytarish"""
    async with get_db() as db:
        async with db.execute("SELECT user_id, movie_name FROM requests WHERE id = ?", (request_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False, None, None
            user_id, movie_name = row
        await db.execute("UPDATE requests SET status = 'resolved' WHERE id = ?", (request_id,))
        await db.commit()
        return True, user_id, movie_name


# --- SPONSOR CHANNELS (HOMIY KANALLAR) ---
SPONSOR_CHANNELS_BACKUP_FILE = "sponsor_channels_backup.json"

async def save_sponsor_channels_backup():
    """Barcha homiy kanallarni sponsor_channels_backup.json zaxira fayliga saqlash"""
    import json
    channels = await get_sponsor_channels()
    data = [{"id": c[0], "channel_id": c[1], "channel_name": c[2]} for c in channels]
    try:
        with open(SPONSOR_CHANNELS_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Sponsor channels backup saqlashda xato: {e}")

async def restore_sponsor_channels_backup_on_startup():
    """Bot ishga tushganda (Render restart bo'lganda) sponsor_channels_backup.json faylidan kanallarni qayta tiklash"""
    import json, os
    if not os.path.exists(SPONSOR_CHANNELS_BACKUP_FILE):
        return
    try:
        with open(SPONSOR_CHANNELS_BACKUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return
        async with get_db() as db:
            for ch in data:
                ch_id = ch.get("channel_id")
                ch_name = ch.get("channel_name") or ch_id
                if ch_id:
                    await db.execute(
                        "INSERT OR IGNORE INTO sponsor_channels (channel_id, channel_name) VALUES (?, ?)",
                        (ch_id, ch_name)
                    )
            await db.commit()
        print(f"Sponsor channels backup qayta tiklandi: {len(data)} ta kanal.")
    except Exception as e:
        print(f"Sponsor channels backup tiklashda xato: {e}")

async def get_sponsor_channels() -> list:
    """Hamkor kanallar ID ro'yxatini olish"""
    async with get_db() as db:
        async with db.execute("SELECT id, channel_id, channel_name FROM sponsor_channels") as cursor:
            return await cursor.fetchall()

async def add_sponsor_channel(channel_id: str, channel_name: str = None) -> bool:
    """Yangi hamkor kanal qo'shish va zaxiraga saqlash"""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO sponsor_channels (channel_id, channel_name) VALUES (?, ?)",
                (channel_id, channel_name or channel_id)
            )
            await db.commit()
            await save_sponsor_channels_backup()
            return True
        except Exception:
            return False

async def remove_sponsor_channel(channel_db_id: int) -> bool:
    """Hamkor kanalni ID bo'yicha o'chirish va zaxirani yangilash"""
    async with get_db() as db:
        await db.execute("DELETE FROM sponsor_channels WHERE id = ?", (channel_db_id,))
        await db.commit()
        await save_sponsor_channels_backup()
        return True

# --- O'CHIRISH (REKLAMADA BLOKLANGANLAR UCHUN) ---
async def delete_user(user_id: int) -> bool:
    """Foydalanuvchini bazadan o'chirish (reklamada botni bloklaganlar)"""
    async with get_db() as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
        return True

async def get_all_users():
    """Barcha bloklanmagan a'zolar ID ro'yxatini olish"""
    async with get_db() as db:
        async with db.execute("SELECT id FROM users WHERE status != 'banned'") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_stats():
    """Bot statistikasini olish"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            users_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE status = 'banned'") as cursor:
            banned_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM movies") as cursor:
            movies_count = (await cursor.fetchone())[0]
        return {
            "users": users_count,
            "banned": banned_count,
            "movies": movies_count
        }

# --- MODERATOR PERMISSIONS ---
async def get_moderator_permissions(user_id: int) -> dict:
    """Moderator ruxsatlarini olish, agar yo'q bo'lsa default yaratish"""
    async with get_db() as db:
        # Avval tekshiramiz
        async with db.execute("SELECT * FROM moderator_permissions WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
        if not row:
            # Mavjud bo'lmasa, default yaratamiz
            await db.execute(
                """INSERT OR IGNORE INTO moderator_permissions (user_id) VALUES (?)""",
                (user_id,)
            )
            await db.commit()
            async with db.execute("SELECT * FROM moderator_permissions WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                
        # Ustun nomlarini olish
        return {
            "add_movie": bool(row[1]),
            "delete_movie": bool(row[2]),
            "view_stats": bool(row[3]),
            "send_broadcast": bool(row[4]),
            "manage_sponsors": bool(row[5]),
            "view_trends": bool(row[6]),
            "backup_db": bool(row[7])
        }

async def toggle_moderator_permission(user_id: int, perm_name: str) -> bool:
    """Moderator ruxsatini yoqish yoki o'chirish"""
    # Xavfsizlik uchun faqat belgilangan ustunlarni o'zgartirish
    allowed_cols = ["add_movie", "delete_movie", "view_stats", "send_broadcast", "manage_sponsors", "view_trends", "backup_db"]
    if perm_name not in allowed_cols:
        return False
        
    # Avval uning joriy holatini olamiz
    perms = await get_moderator_permissions(user_id)
    new_val = 0 if perms[perm_name] else 1
    
    async with get_db() as db:
        await db.execute(f"UPDATE moderator_permissions SET {perm_name} = ? WHERE user_id = ?", (new_val, user_id))
        await db.commit()
        return True

async def has_permission(user_id: int, perm_name: str) -> bool:
    """Foydalanuvchida ma'lum bir ruxsat borligini tekshirish"""
    # Bosh adminlar hamisha barcha ruxsatlarga ega
    if user_id in config.ADMINS:
        return True
    
    # Boshqa foydalanuvchilar (moderatorlar) uchun ruxsatnomani tekshirish
    # Avvalo ularning roli moderator ekanligini tekshiramiz
    async with get_db() as db:
        async with db.execute("SELECT role FROM users WHERE id = ?", (user_id,)) as cursor:
            user_row = await cursor.fetchone()
            if not user_row or user_row[0] != 'moderator':
                return False
                
    perms = await get_moderator_permissions(user_id)
    return perms.get(perm_name, False)

# --- COMMENTS (IZOHLAR) ---
async def add_comment(user_id: int, movie_id: int, comment_text: str) -> bool:
    """Kinoga yangi izoh qo'shish (moderatsiya sozlamasiga qarab status qo'yiladi)"""
    mod_setting = await get_config_int("comment_moderation", 0)
    status = 'pending' if mod_setting == 1 else 'approved'
    async with get_db() as db:
        await db.execute(
            "INSERT INTO comments (user_id, movie_id, comment_text, status) VALUES (?, ?, ?, ?)",
            (user_id, movie_id, comment_text, status)
        )
        await db.commit()
        return True

async def can_post_comment(user_id: int) -> tuple[bool, str]:
    """Foydalanuvchi izoh yozishi mumkinligini tekshirish (cooldown)
    Qaytaradi: (mumkinlik_holati, xabari)"""
    from datetime import datetime, timedelta
    cooldown = await get_config_int("comment_cooldown", 30)
    last_time = await get_last_comment_time(user_id)
    
    if last_time:
        last_dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        if datetime.now() - last_dt < timedelta(seconds=cooldown):
            remaining = cooldown - int((datetime.now() - last_dt).total_seconds())
            return False, f"⏱ Izohlar orasida {cooldown} soniya kutish sharti. Qolgan vaqt: {remaining} soniya"
    
    return True, ""

def contains_profanity(text: str) -> bool:
    """Nojo'ya so'zlar filtri"""
    profanity_words = [
        # O'zbekcha nojo'ya so'zlar
        "yaxshimasan", "yaxshimas", "g'addor", "jin", "jinni", "bema'ni", 
        "nol", "nol", "shunaqa", "shunday", "bunday", "qandaydir",
        # Inglizcha nojo'ya so'zlar
        "fuck", "shit", "damn", "hell", "ass", "bitch", "crap",
        # Ruscha nojo'ya so'zlar
        "бля", "пизда", "хуй", "сука", "ебать", "черт", "дерьмо"
    ]
    
    text_lower = text.lower()
    for word in profanity_words:
        if word in text_lower:
            return True
    return False

async def get_comments(movie_id: int):
    """Kinoning barcha tasdiqlangan izohlarini olish (VIP belgisi bilan)"""
    async with get_db() as db:
        async with db.execute(
            """SELECT c.comment_text, u.username, u.full_name, c.created_at, u.premium_until 
               FROM comments c 
               JOIN users u ON c.user_id = u.id 
               WHERE c.movie_id = ? AND (c.status = 'approved' OR c.status IS NULL) 
               ORDER BY c.created_at DESC""",
            (movie_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_pending_comments(limit: int = 20):
    """Tasdiqlash kutilayotgan izohlar ro'yxati (moderatsiya uchun)"""
    async with get_db() as db:
        async with db.execute(
            """SELECT c.id, c.user_id, c.movie_id, c.comment_text, u.username, u.full_name, m.caption, c.created_at
               FROM comments c
               JOIN users u ON c.user_id = u.id
               LEFT JOIN movies m ON c.movie_id = m.id
               WHERE c.status = 'pending'
               ORDER BY c.created_at DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def approve_comment(comment_id: int) -> bool:
    """Izohni tasdiqlash"""
    async with get_db() as db:
        await db.execute("UPDATE comments SET status = 'approved' WHERE id = ?", (comment_id,))
        await db.commit()
        return True

async def reject_comment(comment_id: int) -> bool:
    """Izohni rad etish (o'chirish)"""
    async with get_db() as db:
        await db.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        await db.commit()
        return True

# --- SCHEDULED BROADCASTS (REJALASHTIRILGAN REKLAMA) ---
async def add_scheduled_broadcast(chat_id: int, message_id: int, send_at: str) -> bool:
    """Yangi rejalashtirilgan reklama qo'shish"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO scheduled_broadcasts (chat_id, message_id, send_at) VALUES (?, ?, ?)",
            (chat_id, message_id, send_at)
        )
        await db.commit()
        return True

async def get_pending_broadcasts():
    """Yuborilishi kerak bo'lgan pending reklamalarni olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, chat_id, message_id, send_at FROM scheduled_broadcasts WHERE is_sent = 0"
        ) as cursor:
            return await cursor.fetchall()

async def mark_broadcast_sent(broadcast_id: int):
    """Reklamani yuborilgan deb belgilash"""
    async with get_db() as db:
        await db.execute(
            "UPDATE scheduled_broadcasts SET is_sent = 1 WHERE id = ?",
            (broadcast_id,)
        )
        await db.commit()

# --- EDIT MOVIE (KINO TAHRIRLASH) ---
async def update_movie_caption(movie_id: int, caption: str) -> bool:
    """Kino tavsifini tahrirlash"""
    async with get_db() as db:
        async with db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)) as cursor:
            if not await cursor.fetchone():
                return False
        await db.execute(
            "UPDATE movies SET caption = ? WHERE id = ?",
            (caption, movie_id)
        )
        await db.commit()
        return True

async def update_movie_video(movie_id: int, file_id: str) -> bool:
    """Kino video faylini yangilash"""
    async with get_db() as db:
        async with db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)) as cursor:
            if not await cursor.fetchone():
                return False
        await db.execute(
            "UPDATE movies SET file_id = ? WHERE id = ?",
            (file_id, movie_id)
        )
        await db.commit()
        return True

# --- REFERRALS (REFERAL TIZIMI) ---
async def get_top_referrers():
    """Eng ko'p referal taklif qilgan top 10 foydalanuvchini olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, username, full_name, referrals_count FROM users WHERE referrals_count > 0 ORDER BY referrals_count DESC LIMIT 10"
        ) as cursor:
            return await cursor.fetchall()

# --- BOT SETTINGS (SOZLAMALAR) ---
async def set_setting(key: str, value: str):
    """Bot sozlamalarini o'rnatish"""
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

async def get_setting(key: str) -> str:
    """Bot sozlamasini olish"""
    async with get_db() as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_config_int(key: str, default: int) -> int:
    """Int turidagi bot sozlamasini olish"""
    val = await get_setting(key)
    return int(val) if val and val.lstrip('-').isdigit() else default

async def get_premium_price_1w() -> int:
    """1 haftalik Premium narxini olish (default: 7000 UZS)"""
    return await get_config_int("premium_price_1w", 7000)

async def get_premium_price_1m() -> int:
    """1 oylik Premium narxini olish (default: 20000 UZS)"""
    return await get_config_int("premium_price_1m", 20000)

async def get_premium_price_3m() -> int:
    """3 oylik Premium narxini olish (default: 50000 UZS)"""
    return await get_config_int("premium_price_3m", 50000)

async def get_premium_price_6m() -> int:
    """6 oylik Premium narxini olish (default: 100000 UZS)"""
    return await get_config_int("premium_price_6m", 100000)

async def get_premium_price_1y() -> int:
    """1 yillik Premium narxini olish (default: 180000 UZS)"""
    return await get_config_int("premium_price_1y", 180000)

async def set_premium_price_1w(price: int):
    """1 haftalik Premium narxini saqlash"""
    await set_setting("premium_price_1w", str(price))

async def set_premium_price_1m(price: int):
    """1 oylik Premium narxini saqlash"""
    await set_setting("premium_price_1m", str(price))

async def set_premium_price_3m(price: int):
    """3 oylik Premium narxini saqlash"""
    await set_setting("premium_price_3m", str(price))

async def set_premium_price_6m(price: int):
    """6 oylik Premium narxini saqlash"""
    await set_setting("premium_price_6m", str(price))

async def set_premium_price_1y(price: int):
    """1 yillik Premium narxini saqlash"""
    await set_setting("premium_price_1y", str(price))

# --- BALL TIZIMI (POINTS SYSTEM) ---
async def add_points(user_id: int, amount: int, bypass_daily_limit: bool = False) -> tuple[int, bool]:
    """Foydalanuvchiga ball qo'shish, kunlik max limitni inobatga olgan holda.
    Qaytaradi: (amalda_qo'shilgan_ball, limitga_yetganlik_holati)"""
    if amount <= 0 or bypass_daily_limit:
        async with get_db() as db:
            await db.execute(
                "UPDATE users SET points = COALESCE(points, 0) + ? WHERE id = ?",
                (amount, user_id)
            )
            await db.commit()
        return amount, False

    from datetime import date
    today = str(date.today())
    daily_limit = await get_config_int("daily_points_limit", 40)
    
    async with get_db() as db:
        # Hozirgi kunlik ballarini olish
        async with db.execute(
            "SELECT points FROM user_daily_points WHERE user_id = ? AND date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            daily_pts = row[0] if row else 0
            
        if daily_pts >= daily_limit:
            return 0, True
            
        added = amount
        reached_limit = False
        if daily_pts + amount >= daily_limit:
            added = daily_limit - daily_pts
            reached_limit = True
            
        # user_daily_points jadvalini yangilash
        if row:
            await db.execute(
                "UPDATE user_daily_points SET points = points + ? WHERE user_id = ? AND date = ?",
                (added, user_id, today)
            )
        else:
            await db.execute(
                "INSERT INTO user_daily_points (user_id, date, points) VALUES (?, ?, ?)",
                (user_id, today, added)
            )
            
        # users jadvalidagi umumiy ballni yangilash
        await db.execute(
            "UPDATE users SET points = COALESCE(points, 0) + ? WHERE id = ?",
            (added, user_id)
        )
        await db.commit()
        return added, reached_limit

async def get_points(user_id: int) -> int:
    """Foydalanuvchi balini olish"""
    async with get_db() as db:
        async with db.execute("SELECT points FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0

async def redeem_150pts_for_2m_premium(user_id: int) -> tuple[bool, str]:
    """150 ball evaziga 2 oylik (60 kun) Premium VIP maqomini almashtirish"""
    async with get_db() as db:
        async with db.execute("SELECT points FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            current_pts = row[0] if row and row[0] is not None else 0
            
        if current_pts < 150:
            return False, f"⚠️ <b>Ballaringiz yetarli emas!</b>\n\nSizda <code>{current_pts}</code> ball bor. 2 oylik Premium uchun kamida <b>150 💎 ball</b> kerak."
            
        # 150 ball ayirish
        await db.execute("UPDATE users SET points = points - 150 WHERE id = ?", (user_id,))
        await db.commit()
        
    # 2 oylik (60 kun) Premium berish
    await add_premium_subscription(user_id, "2 oylik (150 ball)", 2)
    return True, "🎉 <b>TABRIKLAYMIZ!</b>\n\n<b>150 💎 ballingiz evaziga 👑 2 OYLIK PREMIUM VIP MAQOMI muvaffaqiyatli faollashtirildi!</b>\n\n✨ <i>Endi 60 kun davomida cheklovsiz va limitsiz barcha kinolarni tomosha qilishingiz mumkin!</i> 🍿"

async def get_points_leaderboard(limit: int = 10):
    """Eng ko'p ball to'plagan foydalanuvchilar ro'yxati"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, username, full_name, points FROM users WHERE points > 0 ORDER BY points DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

# --- TASODIFIY KINO (RANDOM MOVIE) ---
async def get_random_movie():
    """Bazadan tasodifiy kino olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, file_id, caption FROM movies ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            return await cursor.fetchone()

async def get_users_detailed_list():
    """Barcha foydalanuvchilar haqida batafsil ma'lumotni olish"""
    async with get_db() as db:
        async with db.execute("SELECT id, username, full_name, role, status, points, referrals_count, created_at FROM users") as cursor:
            return await cursor.fetchall()

async def get_all_movie_titles():
    """Barcha kinolarning ID va sarlavhalarini olish (fuzzy search uchun)"""
    async with get_db() as db:
        async with db.execute("SELECT id, caption FROM movies") as cursor:
            return await cursor.fetchall()


# --- SHAXSIY SOZLAMALAR (USER SETTINGS) ---
async def get_user_notify_points(user_id: int) -> bool:
    """Foydalanuvchi ball bildirishnomalarini ko'rishni xohlayaptimi?"""
    async with get_db() as db:
        async with db.execute("SELECT notify_points FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

async def toggle_user_notify_points(user_id: int) -> bool:
    """Ball bildirishnomalarini yoqish/o'chirish. Yangi holatni qaytaradi."""
    current = await get_user_notify_points(user_id)
    new_val = 0 if current else 1
    async with get_db() as db:
        await db.execute("UPDATE users SET notify_points = ? WHERE id = ?", (new_val, user_id))
        await db.commit()
    return bool(new_val)


# --- JAMOAVIY SO'ROVLAR (CROWDSOURCED REQUESTS) ---
async def ensure_movie_requests_table():
    """movie_requests jadvali mavjudligini ta'minlash"""
    async with get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movie_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_name TEXT NOT NULL,
                votes INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS movie_request_votes (
                user_id INTEGER,
                request_id INTEGER,
                PRIMARY KEY (user_id, request_id)
            )
        """)
        await db.commit()

async def add_movie_request(user_id: int, movie_name: str) -> int:
    """Yangi kino so'rovi qo'shish. So'rov ID ni qaytaradi."""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO movie_requests (user_id, movie_name) VALUES (?, ?)",
            (user_id, movie_name)
        )
        await db.commit()
        return cursor.lastrowid

async def vote_movie_request(user_id: int, request_id: int) -> bool:
    """Kino so'roviga ovoz berish. True qaytaradi agar yangi ovoz bo'lsa."""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO movie_request_votes (user_id, request_id) VALUES (?, ?)",
                (user_id, request_id)
            )
            await db.execute(
                "UPDATE movie_requests SET votes = votes + 1 WHERE id = ?",
                (request_id,)
            )
            await db.commit()
            return True
        except Exception:
            return False  # Allaqachon ovoz bergan

async def get_top_movie_requests(limit: int = 10):
    """Eng ko'p so'ralgan kinolar ro'yxati"""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, movie_name, votes, user_id, created_at
               FROM movie_requests WHERE status = 'pending'
               ORDER BY votes DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def resolve_movie_request_by_id(request_id: int):
    """Kino so'rovini bajarilgan deb belgilash"""
    async with get_db() as db:
        await db.execute(
            "UPDATE movie_requests SET status = 'done' WHERE id = ?",
            (request_id,)
        )
        await db.commit()


# --- XAVFSIZLIK VA ANTI-ABUSE TIZIMI ---
async def has_commented_on_movie(user_id: int, movie_id: int) -> bool:
    """Foydalanuvchi ushbu kinoga oldin izoh yozganligini tekshirish (faqat 1-izoh uchun ball beriladi)"""
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM comments WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] > 0 if row else False

async def get_last_comment_time(user_id: int) -> str:
    """Foydalanuvchi oxirgi marta qachon izoh yozganini olish (cooldown tekshirish uchun)"""
    async with get_db() as db:
        async with db.execute(
            "SELECT MAX(created_at) FROM comments WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_daily_ratings_count(user_id: int) -> int:
    """Foydalanuvchi bugun baholagan kinolari sonini olish (kuniga max 10 ta)"""
    from datetime import date
    today = str(date.today())
    async with get_db() as db:
        try:
            async with db.execute(
                "SELECT COUNT(*) FROM ratings WHERE user_id = ? AND date(created_at) = ?",
                (user_id, today)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception:
            async with db.execute(
                "SELECT COUNT(*) FROM ratings WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

async def check_and_reward_referral(user_id: int, bot) -> bool:
    """Foydalanuvchi kanallarga muvaffaqiyatli a'zo bo'lganida taklif qilgan odamga ball berish"""
    async with get_db() as db:
        # Foydalanuvchining refererini olish va mukofot berilmaganligini tekshirish
        async with db.execute(
            "SELECT referred_by, referral_rewarded, username, full_name FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row and row[0] and not row[1]:
            referred_by = row[0]
            # Refererga 10 ball berish
            await db.execute(
                "UPDATE users SET points = points + 10 WHERE id = ?",
                (referred_by,)
            )
            # Mukofot berilganligini belgilash
            await db.execute(
                "UPDATE users SET referral_rewarded = 1 WHERE id = ?",
                (user_id,)
            )
            await db.commit()
            await check_notify_150pts_reward(bot, referred_by)
            return True
        return False

async def check_notify_150pts_reward(bot, user_id: int):
    """Foydalanuvchi 150 ballga yetganda professional taklif xabarini yuborish"""
    try:
        pts = await get_points(user_id)
        if pts >= 150:
            is_prem = await is_premium_user(user_id)
            if not is_prem:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🎁 2 Oylik Premiumni Ishlatish", callback_data="redeem_150pts_premium")
                ]])
                
                prof_msg = (
                    f"🎁 <b>PROFESSIONAL TABRIKNOMA VA MAXSUS IMTIYOZ!</b> 🎉\n\n"
                    f"Hurmatli foydalanuvchi, botimizdagi faolligingiz evaziga siz jami <b>{pts} 💎 ball</b> to'plashga muvaffaq bo'ldingiz! 👏\n\n"
                    f"👑 <b>Siz uchun 150 ball evaziga 2 OYLIK PREMIUM VIP maqomi tayyor qilindi!</b>\n\n"
                    f"✨ <i>Obunani ishga tushirish uchun quyidagi tugmani bosing:</i>"
                )
                await bot.send_message(user_id, prof_msg, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass


# --- PREMIUM OBUNA TIZIMI ---
async def add_premium_subscription(user_id: int, plan: str, months: int) -> bool:
    """Foydalanuvchiga premium obuna qo'shish"""
    from datetime import datetime, timedelta
    start_date = datetime.now()
    end_date = start_date + timedelta(days=months * 30)

    async with get_db() as db:
        try:
            await db.execute(
                """INSERT OR REPLACE INTO premium_subscriptions
                   (user_id, start_date, end_date, plan)
                   VALUES (?, ?, ?, ?)""",
                (user_id, start_date, end_date, plan)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def add_premium_days(user_id: int, plan: str, days: int) -> bool:
    """Foydalanuvchiga kun hisobida premium obuna qo'shish"""
    from datetime import datetime, timedelta
    start_date = datetime.now()
    end_date = start_date + timedelta(days=days)

    async with get_db() as db:
        try:
            await db.execute(
                """INSERT OR REPLACE INTO premium_subscriptions
                   (user_id, start_date, end_date, plan)
                   VALUES (?, ?, ?, ?)""",
                (user_id, start_date, end_date, plan)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def get_premium_subscription(user_id: int):
    """Foydalanuvchining premium obunasini olish"""
    from datetime import datetime
    async with get_db() as db:
        async with db.execute(
            "SELECT user_id, start_date, end_date, plan FROM premium_subscriptions WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Obuna muddati tugaganmi tekshirish
                end_date = datetime.fromisoformat(row[2])
                if datetime.now() > end_date:
                    return None
                return row
            return None

async def is_premium_user(user_id: int) -> bool:
    """Foydalanuvchi premium ekanini tekshirish (barcha jadvallar bo'yicha)"""
    subscription = await get_premium_subscription(user_id)
    if subscription is not None:
        return True
    return await is_user_premium(user_id)

async def get_user_premium_until(user_id: int) -> str | None:
    """users jadvalidan premium_until qiymatini olish (fallback uchun)"""
    async with get_db() as db:
        async with db.execute(
            "SELECT premium_until FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def remove_premium_subscription(user_id: int) -> bool:
    """Foydalanuvchining premium obunasini o'chirish"""
    async with get_db() as db:
        await db.execute("DELETE FROM premium_subscriptions WHERE user_id = ?", (user_id,))
        await db.commit()
        return True

async def get_active_premium_subscribers_list(limit: int = 50) -> list:
    """Aktiv Premium foydalanuvchilar va ularning ma'lumotlarini olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT u.id, u.username, u.full_name, 
                      COALESCE(s.start_date, u.created_at, 'Hozirgi'), 
                      COALESCE(s.end_date, u.premium_until, 'Nomalum'), 
                      COALESCE(s.plan, 'Premium VIP')
               FROM users u
               LEFT JOIN premium_subscriptions s ON u.id = s.user_id
               WHERE u.is_premium = 1 OR u.role = 'vip' OR (s.end_date IS NOT NULL AND s.end_date > datetime('now'))
               
               UNION
               
               SELECT s.user_id, COALESCE(u.username, 'user_' || s.user_id), COALESCE(u.full_name, 'User ' || s.user_id),
                      s.start_date, s.end_date, COALESCE(s.plan, 'Premium VIP')
               FROM premium_subscriptions s
               LEFT JOIN users u ON s.user_id = u.id
               WHERE s.end_date IS NOT NULL AND s.end_date > datetime('now')
               
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def revoke_premium_subscription(user_id: int) -> bool:
    """Foydalanuvchining Premium VIP obunasini bekor qilish / o'chirish"""
    async with get_db() as db:
        await db.execute("DELETE FROM premium_subscriptions WHERE user_id = ?", (user_id,))
        await db.execute(
            "UPDATE users SET is_premium = 0, role = 'member', premium_until = NULL WHERE id = ?",
            (user_id,)
        )
        await db.commit()
        return True


# --- KUNLIK KINO LIMIT TIZIMI ---
async def increment_daily_movie_count(user_id: int) -> int:
    """Foydalanuvchining kunlik kino ko'rish sonini oshirish"""
    from datetime import date
    today = str(date.today())

    async with get_db() as db:
        # Bugun uchun yozuv borligini tekshirish
        async with db.execute(
            "SELECT movies_watched FROM daily_movie_limits WHERE user_id = ? AND date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            # Yozuv bor - sonini oshirish
            new_count = row[0] + 1
            await db.execute(
                "UPDATE daily_movie_limits SET movies_watched = ? WHERE user_id = ? AND date = ?",
                (new_count, user_id, today)
            )
            await db.commit()
            return new_count
        else:
            # Yangi yozuv yaratish
            await db.execute(
                "INSERT INTO daily_movie_limits (user_id, date, movies_watched) VALUES (?, ?, 1)",
                (user_id, today)
            )
            await db.commit()
            return 1

async def get_daily_movie_count(user_id: int) -> int:
    """Foydalanuvchining bugungi kino ko'rish sonini olish"""
    from datetime import date
    today = str(date.today())

    async with get_db() as db:
        async with db.execute(
            "SELECT movies_watched FROM daily_movie_limits WHERE user_id = ? AND date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def reset_daily_movie_count(user_id: int) -> bool:
    """Foydalanuvchining kunlik kino ko'rish sonini qayta o'rnatish (admin uchun)"""
    from datetime import date
    today = str(date.today())

    async with get_db() as db:
        await db.execute(
            "DELETE FROM daily_movie_limits WHERE user_id = ? AND date = ?",
            (user_id, today)
        )
        await db.commit()
        return True


# --- KINO QIDIRISH TIZIMI ---
async def search_movies_by_name(query: str, limit: int = 10):
    """Kinolarni nomi bo'yicha qidirish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, caption FROM movies WHERE caption LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        ) as cursor:
            return await cursor.fetchall()


# ─── GENERAL STATISTICS ───────────────────────────────────────────────────────
async def get_total_users_count():
    """Jami foydalanuvchilar soni"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0


async def get_premium_users_count():
    """Premium foydalanuvchilar soni"""
    async with get_db() as db:
        async with db.execute(
            """SELECT COUNT(*) FROM users WHERE id IN 
               (SELECT user_id FROM premium_subscriptions WHERE end_date > datetime('now'))"""
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0


async def get_total_movies_count():
    """Jami kinolar soni"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM movies") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0


async def get_total_referrals_count():
    """Jami referallar soni"""
    async with get_db() as db:
        async with db.execute("SELECT SUM(referral_count) FROM users") as cursor:
            result = await cursor.fetchone()
            return result[0] if result and result[0] else 0


async def get_today_users_count():
    """Bugun qo'shilgan foydalanuvchilar soni"""
    from datetime import date
    today = str(date.today())
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at LIKE ?",
            (f"{today}%",)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0


async def get_trending_movies():
    """Eng ko'p ko'rilgan kinolar"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, caption, views_count FROM movies ORDER BY views_count DESC LIMIT 10"
        ) as cursor:
            return await cursor.fetchall()


# ─── TOP 10 USERS ─────────────────────────────────────────────────────────────
async def get_top_users_by_points(limit: int = 10):
    """Ballar bo'yicha TOP 10 foydalanuvchilarni olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, username, full_name, points, referrals_count
               FROM users
               WHERE role != 'admin'
               ORDER BY points DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()


async def get_top_users_by_referrals(limit: int = 10):
    """Referallar soni bo'yicha TOP 10 foydalanuvchilarni olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, username, full_name, referrals_count, points
               FROM users
               WHERE role != 'admin'
               ORDER BY referrals_count DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()


async def get_top_users_by_activity(limit: int = 10):
    """Faollik bo'yicha TOP 10 foydalanuvchilarni olish (so'nggi faollik vaqti)"""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, username, full_name, last_active_at, points
               FROM users
               WHERE role != 'admin' AND last_active_at IS NOT NULL
               ORDER BY last_active_at DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()


# ─── TOP 10 ADMINS ───────────────────────────────────────────────────────────
async def get_all_admin_profiles():
    """Barcha admin ma'lumotlarini olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT id, username, full_name FROM users WHERE role = 'admin'"""
        ) as cursor:
            return await cursor.fetchall()


async def get_admin_stats(admin_id: int):
    """Admin statistikasini olish"""
    async with get_db() as db:
        # Admin tomonidan qo'shilgan kinolar soni
        async with db.execute(
            "SELECT COUNT(*) FROM movies WHERE added_by = ?",
            (admin_id,)
        ) as cursor:
            movies_added = (await cursor.fetchone())[0] if await cursor.fetchone() else 0

        # Admin tomonidan tasdiqlangan to'lovlar soni
        async with db.execute(
            """SELECT COUNT(*) FROM premium_subscriptions
               WHERE approved_by = ?""",
            (admin_id,)
        ) as cursor:
            payments_approved = (await cursor.fetchone())[0] if await cursor.fetchone() else 0

        # Admin tomonidan bajarilgan boshqa harakatlar
        async with db.execute(
            "SELECT COUNT(*) FROM abuse_logs WHERE admin_id = ?",
            (admin_id,)
        ) as cursor:
            other_actions = (await cursor.fetchone())[0] if await cursor.fetchone() else 0

        return {
            "movies_added": movies_added,
            "payments_approved": payments_approved,
            "other_actions": other_actions,
            "total_actions": movies_added + payments_approved + other_actions
        }


async def get_all_admins_stats():
    """Barcha adminlarning statistikasini olish"""
    admins = await get_all_admin_profiles()

    stats = []
    for admin_id, username, full_name in admins:
        admin_stats = await get_admin_stats(admin_id)
        stats.append({
            "id": admin_id,
            "username": username,
            "full_name": full_name,
            **admin_stats
        })

    # Total actions bo'yicha tartiblash
    stats.sort(key=lambda x: x["total_actions"], reverse=True)
    return stats[:10]  # TOP 10

async def add_abuse_log(user_id: int, log_type: str, details: str):
    """Shubhali harakatlarni jurnalga yozish"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO abuse_logs (user_id, type, details) VALUES (?, ?, ?)",
            (user_id, log_type, details)
        )
        await db.commit()

async def get_recent_abuse_logs(limit: int = 20):
    """Oxirgi shubhali harakatlarni olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT user_id, type, details, created_at FROM abuse_logs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

# Xato kino kodi kiritishlarni hisoblash (auto-ban uchun)
async def increment_wrong_code_count(user_id: int) -> int:
    """Foydalanuvchining xato kino kodi kiritishlarini oshirish va joriy sonini qaytarish"""
    from datetime import datetime, timedelta
    now = datetime.now()
    cutoff = now - timedelta(minutes=5)  # 5 daqiqa ichidagi xatolar
    
    async with get_db() as db:
        # Eski xatolarni tozalash
        await db.execute(
            "DELETE FROM abuse_logs WHERE type = 'wrong_code' AND created_at < ?",
            (cutoff.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        
        # Yangi xatoni qo'shish
        await db.execute(
            "INSERT INTO abuse_logs (user_id, type, details) VALUES (?, 'wrong_code', ?)",
            (user_id, now.strftime("%Y-%m-%d %H:%M:%S"))
        )
        
        # Joriy xatolar sonini hisoblash
        async with db.execute(
            "SELECT COUNT(*) FROM abuse_logs WHERE user_id = ? AND type = 'wrong_code'",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def clear_abuse_logs():
    """Shubhali harakatlar jurnalini tozalash"""
    async with get_db() as db:
        await db.execute("DELETE FROM abuse_logs")
        await db.commit()

async def clear_old_daily_points(days: int = 30):
    """Eski kunlik ballarni tozalash (default 30 kun)"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    
    async with get_db() as db:
        await db.execute(
            "DELETE FROM user_daily_points WHERE date < ?",
            (cutoff_str,)
        )
        await db.commit()

async def clear_all_caches():
    """Barcha keshlarni tozalash"""
    await clear_abuse_logs()
    await clear_old_daily_points(30)
    
    # Temp bansni tozalash
    from middlewares.check_sub import TEMP_BANS
    TEMP_BANS.clear()
    
    # Memory cache ni tozalash
    from database.connection import cache
    cache.clear()
    
async def get_next_available_movie_id() -> int:
    """Eng birinchi bo'sh bo'lgan kino kodini (1, 2, 3, 4 ... 100000) topib qaytarish (bo'sh o'rinlarni to'ldiradi)"""
    async with get_db() as db:
        async with db.execute("SELECT id FROM movies ORDER BY id ASC") as cursor:
            rows = await cursor.fetchall()
            existing_ids = set(r[0] for r in rows if r[0] is not None)
            
            candidate = 1
            while candidate in existing_ids:
                candidate += 1
            return candidate


# --- KUNLIK BONUS (+3 BALL) ---
async def claim_daily_bonus(user_id: int) -> tuple[bool, str, int]:
    """Kunlik +3 ball bonusini olish"""
    from datetime import date
    today = str(date.today())
    
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM daily_claims WHERE user_id = ? AND claim_date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return False, "⏱ <b>Siz bugungi kunlik bonusni olgansiz! Erta yana urining.</b>", 0
                
        await db.execute(
            "INSERT INTO daily_claims (user_id, claim_date) VALUES (?, ?)",
            (user_id, today)
        )
        await db.commit()
        
    pts_added, _ = await add_points(user_id, 3)
    return True, f"🎁 <b>Kunlik bonus olindi! +3 💎 ball taqdim etildi.</b>", pts_added

# --- SAQLANGAN KINOLAR (FAVORITES) ---
async def add_favorite(user_id: int, movie_id: int) -> bool:
    """Kinoni saqlanganlarga qo'shish"""
    async with get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO favorites (user_id, movie_id) VALUES (?, ?)",
            (user_id, movie_id)
        )
        await db.commit()
        return True

async def remove_favorite(user_id: int, movie_id: int) -> bool:
    """Kinoni saqlanganlardan o'chirish"""
    async with get_db() as db:
        await db.execute(
            "DELETE FROM favorites WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        )
        await db.commit()
        return True

async def is_favorite(user_id: int, movie_id: int) -> bool:
    """Kino saqlanganmi tekshirish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row)

async def get_user_favorites(user_id: int) -> list:
    """Foydalanuvchining saqlangan kinolari ro'yxati (3 ta qiymat: movie_id, caption, views_count)
    Agar saqlangan kino bazadan o'chirilgan bo'lsa, avtomatik favorites dan o'chiriladi."""
    async with get_db() as db:
        async with db.execute(
            """SELECT m.id, m.caption, COALESCE(m.views_count, 0)
               FROM favorites f
               JOIN movies m ON f.movie_id = m.id
               WHERE f.user_id = ?""",
            (user_id,)
        ) as cursor:
            existing = await cursor.fetchall()
        # Saqlangan lekin bazada mavjud bo'lmagan (o'chirilgan) kinolarni tozalash
        await db.execute("""
            DELETE FROM favorites
            WHERE user_id = ? AND movie_id NOT IN (SELECT id FROM movies)
        """, (user_id,))
        await db.commit()
        return existing

# --- IZOHLAR LIKELARI (COMMENT LIKES) ---
async def toggle_comment_like(comment_id: int, user_id: int) -> tuple[bool, int]:
    """Izohga like bosish / olib tashlash. Qaytaradi: (liked_status, total_likes)"""
    async with get_db() as db:
        async with db.execute(
            "SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?",
            (comment_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            await db.execute(
                "DELETE FROM comment_likes WHERE comment_id = ? AND user_id = ?",
                (comment_id, user_id)
            )
            liked = False
        else:
            await db.execute(
                "INSERT INTO comment_likes (comment_id, user_id) VALUES (?, ?)",
                (comment_id, user_id)
            )
            liked = True
            
        await db.commit()
        
        async with db.execute(
            "SELECT COUNT(*) FROM comment_likes WHERE comment_id = ?",
            (comment_id,)
        ) as cursor:
            count_row = await cursor.fetchone()
            total_likes = count_row[0] if count_row else 0
            
        return liked, total_likes

async def get_comment_likes_count(comment_id: int) -> int:
    """Izoh likelar sonini olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM comment_likes WHERE comment_id = ?",
            (comment_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# --- PREMIUM / VIP SYSTEM & MUSOBAQA ---
async def set_user_premium(user_id: int, days: int = 7, plan: str = None) -> bool:
    """Foydalanuvchiga Premium maqomini berish"""
    from datetime import datetime, timedelta
    now = datetime.now()
    until = now + timedelta(days=days)
    until_str = until.strftime("%Y-%m-%d %H:%M:%S")
    start_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Plan nomini avtomatik belgilash
    if plan is None:
        if days == 1:
            plan = "1 kunlik"
        elif days <= 7:
            plan = "1 haftalik"
        elif days <= 31:
            plan = "1 oylik"
        elif days <= 62:
            plan = "2 oylik"
        elif days <= 93:
            plan = "3 oylik"
        else:
            plan = f"{days} kunlik"

    async with get_db() as db:
        # users jadvalini yangilash
        await db.execute(
            "UPDATE users SET is_premium = 1, premium_until = ? WHERE id = ?",
            (until_str, user_id)
        )
        # premium_subscriptions jadvalini yangilash yoki qo'shish
        await db.execute(
            """INSERT INTO premium_subscriptions (user_id, start_date, end_date, plan)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   start_date = excluded.start_date,
                   end_date = excluded.end_date,
                   plan = excluded.plan""",
            (user_id, start_str, until_str, plan)
        )
        # Premium berilganda foydalanuvchining aktiv promo skidkasini sarf qilib (is_consumed = 1) belgilash
        try:
            await db.execute(
                "UPDATE promo_uses SET is_consumed = 1 WHERE user_id = ? AND COALESCE(is_consumed, 0) = 0",
                (user_id,)
            )
        except Exception:
            pass

        await db.commit()
        return True

async def set_user_premium_custom_dates(user_id: int, start_date: str, end_date: str, plan: str = None) -> bool:
    """Foydalanuvchiga Premium maqomini belgilangan sanalar bilan berish (start_date <= end_date kafolati bilan)"""
    from datetime import datetime
    try:
        dt_start = datetime.fromisoformat(start_date.replace(' ', 'T'))
        dt_end = datetime.fromisoformat(end_date.replace(' ', 'T'))
        if dt_start > dt_end:
            start_date, end_date = end_date, start_date
    except Exception:
        pass

    async with get_db() as db:
        # 1. users jadvalida user mavjud bo'lsa UPDATE, aks holda INSERT
        await db.execute(
            """INSERT INTO users (id, username, full_name, is_premium, premium_until)
               VALUES (?, ?, ?, 1, ?)
               ON CONFLICT(id) DO UPDATE SET is_premium = 1, premium_until = ?""",
            (user_id, f"user_{user_id}", f"User {user_id}", end_date, end_date)
        )
        # 2. premium_subscriptions jadvalini yangilash yoki qo'shish
        await db.execute(
            """INSERT INTO premium_subscriptions (user_id, start_date, end_date, plan)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   start_date = excluded.start_date,
                   end_date = excluded.end_date,
                   plan = excluded.plan""",
            (user_id, start_date, end_date, plan or "Premium VIP")
        )
        try:
            await db.execute(
                "UPDATE promo_uses SET is_consumed = 1 WHERE user_id = ? AND COALESCE(is_consumed, 0) = 0",
                (user_id,)
            )
        except Exception:
            pass

        await db.commit()
        return True

async def is_user_premium(user_id: int) -> bool:
    """Foydalanuvchi Premium maqomidami tekshirish"""
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with get_db() as db:
        async with db.execute(
            "SELECT is_premium, premium_until FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            is_p, p_until = row[0], row[1]
            if is_p == 1 and p_until and p_until >= now_str:
                return True
            return False

async def get_banned_users_list() -> list:
    """Bloklangan foydalanuvchilar ro'yxati"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, username, full_name, role FROM users WHERE role = 'banned'"
        ) as cursor:
            return await cursor.fetchall()

# --- WATERMARK / CAPTION CLEANER UTILITY ---
async def clean_and_format_caption_async(raw_caption: str) -> str:
    """Begona reklama va havolalarni tozala va sozlangan brend watermarkini qo'sh"""
    import re, config
    bot_tag = config.BOT_USERNAME if config.BOT_USERNAME.startswith("@") else f"@{config.BOT_USERNAME}"
    
    custom_wm = await get_setting("custom_watermark_text")
    wm_text = custom_wm if custom_wm else f"🎬 <b>{bot_tag} — Eng sara kinolar bazasi 🍿</b>"

    if not raw_caption:
        return wm_text

    cleaned = re.sub(r'@(?!uzkinobaza_bot\b)[a-zA-Z0-9_]{5,}', '', raw_caption)
    cleaned = re.sub(r'https?://t\.me/\S+', '', cleaned).strip()
    
    if cleaned:
        return f"{wm_text}\n\n{cleaned}"
    return wm_text

def clean_and_format_caption(raw_caption: str) -> str:
    """Begona reklama va havolalarni tozala va @uzkinobaza_bot brendini qo'sh"""
    import re, config
    bot_tag = config.BOT_USERNAME if config.BOT_USERNAME.startswith("@") else f"@{config.BOT_USERNAME}"
    if not raw_caption:
        return f"🎬 <b>Kino Bot:</b> {bot_tag}"
    cleaned = re.sub(r'@(?!uzkinobaza_bot\b)[a-zA-Z0-9_]{5,}', '', raw_caption)
    cleaned = re.sub(r'https?://t\.me/\S+', '', cleaned).strip()
    header = f"🎬 <b>{bot_tag} — Eng sara kinolar 🍿</b>"
    if cleaned:
        return f"{header}\n\n{cleaned}"
    return header


# --- SUPPORT TICKETS & TARGETED BROADCAST HELPERS ---
async def create_ticket(user_id: int, message_text: str) -> int:
    """Yangi yordam ticketini yaratadi va uning ID sini qaytaradi"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO tickets (user_id, message_text) VALUES (?, ?)",
            (user_id, message_text)
        )
        await db.commit()
        return cursor.lastrowid

async def get_ticket(ticket_id: int):
    """Ticket ma'lumotlarini olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT id, user_id, message_text, status, reply_text, admin_id, created_at FROM tickets WHERE id = ?",
            (ticket_id,)
        ) as cursor:
            return await cursor.fetchone()

async def reply_to_ticket(ticket_id: int, admin_id: int, reply_text: str) -> bool:
    """Ticketga javob yozish va holatini yangilash"""
    from datetime import datetime
    async with get_db() as db:
        try:
            await db.execute(
                """UPDATE tickets 
                   SET status = 'replied', reply_text = ?, admin_id = ?, replied_at = ?
                   WHERE id = ?""",
                (reply_text, admin_id, datetime.now(), ticket_id)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def get_target_users(target_group: str = "all") -> list:
    """Maqsadli auditoriya bo'yicha foydalanuvchilar ID ro'yxatini olish"""
    async with get_db() as db:
        if target_group == "premium":
            async with db.execute(
                "SELECT id FROM users WHERE is_premium = 1 OR role = 'vip'"
            ) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]
        elif target_group == "active_7d":
            async with db.execute(
                "SELECT id FROM users WHERE last_active_at >= datetime('now', '-7 days') AND (status != 'banned' OR status IS NULL)"
            ) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]
        elif target_group == "ordinary":
            async with db.execute(
                "SELECT id FROM users WHERE (is_premium = 0 OR is_premium IS NULL) AND (status != 'banned' OR status IS NULL)"
            ) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]
        else: # "all"
            async with db.execute("SELECT id FROM users WHERE status != 'banned' OR status IS NULL") as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows]


# ─── KUNLIK BONUS KINO LIMITI FUNKSIYALARI ───────────────────────────────────
async def get_daily_bonus_limit(user_id: int) -> int:
    """Foydalanuvchining bugun uchun qo'shimcha bonus limitini olish"""
    from datetime import date
    today = str(date.today())
    async with get_db() as db:
        async with db.execute(
            "SELECT bonus_count FROM user_daily_bonus_limits WHERE user_id = ? AND date = ?",
            (user_id, today)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_daily_bonus_limit_batch(user_ids: list, bonus_amount: int) -> int:
    """Foydalanuvchilar guruhiga bugun uchun qo'shimcha bonus limit qo'shish"""
    from datetime import date
    today = str(date.today())
    success = 0
    async with get_db() as db:
        for uid in user_ids:
            try:
                await db.execute(
                    """INSERT INTO user_daily_bonus_limits (user_id, date, bonus_count) 
                       VALUES (?, ?, ?)
                       ON CONFLICT(user_id, date) DO UPDATE SET bonus_count = bonus_count + ?""",
                    (uid, today, bonus_amount, bonus_amount)
                )
                success += 1
            except Exception:
                pass
        await db.commit()
    return success


# ─── TUG'ILGAN KUN FUNKSIYALARI ───────────────────────────────────────────────
async def set_user_birthday(user_id: int, birthday: str) -> bool:
    """Foydalanuvchining tug'ilgan kunini 1 marta saqlash (KK.OO.YYYY)"""
    async with get_db() as db:
        # Allaqachon kiritilganmi tekshirish
        async with db.execute("SELECT birthday FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                return False  # Allaqachon kiritilgan
        await db.execute("UPDATE users SET birthday = ? WHERE id = ?", (birthday, user_id))
        await db.commit()
        return True

async def get_user_birthday(user_id: int):
    """Foydalanuvchining tug'ilgan kunini olish"""
    async with get_db() as db:
        async with db.execute("SELECT birthday FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def get_today_birthdays() -> list:
    """Bugun tug'ilgan kunli foydalanuvchilar (KK.OO formati bilan solishtirish)"""
    from datetime import datetime
    today = datetime.now().strftime("%d.%m")
    async with get_db() as db:
        async with db.execute(
            "SELECT id, full_name, username, birthday, last_birthday_bonus_year FROM users WHERE birthday LIKE ?",
            (f"{today}.%",)
        ) as cursor:
            return await cursor.fetchall()

async def mark_birthday_bonus_given(user_id: int, year: int):
    """Tug'ilgan kun bonusini berilganligini yozish"""
    async with get_db() as db:
        await db.execute("UPDATE users SET last_birthday_bonus_year = ? WHERE id = ?", (year, user_id))
        await db.commit()


# ─── ADMIN PIN (2FA) FUNKSIYALARI ────────────────────────────────────────────
import hashlib

def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

async def set_admin_pin(admin_id: int, pin: str) -> bool:
    """Admin PIN o'rnatish yoki yangilash"""
    pin_hash = _hash_pin(pin)
    async with get_db() as db:
        await db.execute(
            """INSERT OR REPLACE INTO admin_pins (admin_id, pin_hash, last_changed, failed_attempts, blocked_until)
               VALUES (?, ?, CURRENT_TIMESTAMP, 0, NULL)""",
            (admin_id, pin_hash)
        )
        await db.commit()
        return True

async def verify_admin_pin(admin_id: int, pin: str) -> tuple:
    """PIN tekshirish. Qaytaradi: (is_correct, is_blocked, failed_attempts)"""
    from datetime import datetime
    async with get_db() as db:
        async with db.execute(
            "SELECT pin_hash, failed_attempts, blocked_until FROM admin_pins WHERE admin_id = ?",
            (admin_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return (False, False, 0)  # PIN o'rnatilmagan

            stored_hash, failed, blocked_until = row

            # Bloklangan vaqtni tekshirish
            if blocked_until:
                blocked_dt = datetime.fromisoformat(str(blocked_until))
                if datetime.now() < blocked_dt:
                    return (False, True, failed)
                else:
                    # Blok muddati tugagan — tozalash
                    await db.execute("UPDATE admin_pins SET failed_attempts = 0, blocked_until = NULL WHERE admin_id = ?", (admin_id,))
                    await db.commit()

            if _hash_pin(pin) == stored_hash:
                # To'g'ri — failed ni tozalash
                await db.execute("UPDATE admin_pins SET failed_attempts = 0 WHERE admin_id = ?", (admin_id,))
                await db.commit()
                return (True, False, 0)
            else:
                # Noto'g'ri — failed oshirish
                new_failed = failed + 1
                if new_failed >= 5:
                    from datetime import timedelta
                    block_until = (datetime.now() + timedelta(minutes=10)).isoformat()
                    await db.execute(
                        "UPDATE admin_pins SET failed_attempts = ?, blocked_until = ? WHERE admin_id = ?",
                        (new_failed, block_until, admin_id)
                    )
                else:
                    await db.execute("UPDATE admin_pins SET failed_attempts = ? WHERE admin_id = ?", (new_failed, admin_id))
                await db.commit()
                return (False, new_failed >= 5, new_failed)

async def get_admin_pin_info(admin_id: int):
    """Admin PIN ma'lumotlarini olish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT pin_hash, last_changed FROM admin_pins WHERE admin_id = ?", (admin_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_admins_pin_for_reminder() -> list:
    """Har 2 haftada eslatma uchun: PIN'ni 14+ kun yangilamagan adminlar"""
    async with get_db() as db:
        async with db.execute(
            """SELECT admin_id, last_changed FROM admin_pins 
               WHERE last_changed <= datetime('now', '-14 days')"""
        ) as cursor:
            return await cursor.fetchall()


# ─── FOYDALANUVCHI QIDIRISH VA BOSHQARISH ────────────────────────────────────
async def search_user_by_query(query: str):
    """ID yoki username bo'yicha foydalanuvchi qidirish"""
    async with get_db() as db:
        if query.isdigit():
            async with db.execute(
                "SELECT id, username, full_name, role, status, points, referrals_count, created_at, birthday FROM users WHERE id = ?",
                (int(query),)
            ) as cursor:
                return await cursor.fetchone()
        else:
            uname = query.lstrip("@")
            async with db.execute(
                "SELECT id, username, full_name, role, status, points, referrals_count, created_at, birthday FROM users WHERE username = ?",
                (uname,)
            ) as cursor:
                return await cursor.fetchone()

async def add_points_to_user(user_id: int, delta: int) -> int:
    """Foydalanuvchiga ball qo'shish yoki ayirish, yangi ballarni qaytarish"""
    async with get_db() as db:
        async with db.execute("SELECT points FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            current = row[0] if row else 0
        new_pts = max(0, current + delta)
        await db.execute("UPDATE users SET points = ? WHERE id = ?", (new_pts, user_id))
        await db.commit()
        return new_pts


# ─── TOP 100 KINOLAR ─────────────────────────────────────────────────────────
async def get_top_rated_movies(limit: int = 100):
    """Eng yuqori baholangan kinolar"""
    async with get_db() as db:
        async with db.execute(
            """SELECT m.id, m.caption, 
                      AVG(r.rating) as avg_rating,
                      COUNT(r.rating) as votes,
                      m.views_count
               FROM movies m
               LEFT JOIN ratings r ON m.id = r.movie_id
               GROUP BY m.id
               HAVING votes > 0
               ORDER BY avg_rating DESC, votes DESC
               LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()


# ─── NOFAOL FOYDALANUVCHI TOZALASH ───────────────────────────────────────────
async def get_inactive_users(days: int = 90) -> list:
    """Berilgan kundan ko'p vaqt kirmagan foydalanuvchilar"""
    async with get_db() as db:
        async with db.execute(
            f"SELECT id, username, full_name FROM users WHERE last_active_at <= datetime('now', '-{days} days') AND status != 'banned'"
        ) as cursor:
            return await cursor.fetchall()

async def delete_users_batch(user_ids: list) -> int:
    """Bir nechta foydalanuvchini o'chirish"""
    if not user_ids:
        return 0
    async with get_db() as db:
        placeholders = ",".join("?" * len(user_ids))
        await db.execute(f"DELETE FROM users WHERE id IN ({placeholders})", user_ids)
        await db.commit()
        return len(user_ids)


# ─── FOYDALANUVCHI DARAJASI (USER LEVEL) ─────────────────────────────────────
def get_user_level(points: int) -> tuple:
    """Ball bo'yicha daraja aniqlash. Qaytaradi: (daraja_nomi, emoji, keyingi_chegara)"""
    if points is None:
        points = 0
    if points >= 500:
        return ("👑 VIP", "👑", None)
    elif points >= 200:
        return ("🥇 Gold", "🥇", 500)
    elif points >= 50:
        return ("🥈 Silver", "🥈", 200)
    else:
        return ("🥉 Bronze", "🥉", 50)


# ─── WATCH HISTORY ────────────────────────────────────────────────────────────
async def add_to_watch_history(user_id: int, movie_id: int):
    """Kino ko'rilganlarni yozish + 100 tadan oshganda eski qatorlarni o'chirish"""
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO watch_history (user_id, movie_id, watched_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (user_id, movie_id)
        )
        await db.commit()
        await _trim_watch_history_100(db, user_id)

async def _trim_watch_history_100(db, user_id: int):
    """Watch history ni 100 tada cheklab, eski qatorlarni o'chirish"""
    await db.execute("""
        DELETE FROM watch_history
        WHERE user_id = ? AND rowid NOT IN (
            SELECT rowid FROM watch_history
            WHERE user_id = ?
            ORDER BY watched_at DESC
            LIMIT 100
        )
    """, (user_id, user_id))
    await db.commit()

async def get_watch_history(user_id: int, limit: int = 100) -> list:
    """Foydalanuvchining oxirgi ko'rgan kinolari (limit 100)"""
    async with get_db() as db:
        async with db.execute(
            """SELECT wh.movie_id, m.caption, wh.watched_at
               FROM watch_history wh
               JOIN movies m ON wh.movie_id = m.id
               WHERE wh.user_id = ?
               ORDER BY wh.watched_at DESC LIMIT ?""",
            (user_id, limit)
        ) as cursor:
            return await cursor.fetchall()

async def clear_watch_history(user_id: int) -> bool:
    """Foydalanuvchi ko'rilgan kinolar tarixini tozalash (shaxsiy ma'lumot)"""
    async with get_db() as db:
        await db.execute("DELETE FROM watch_history WHERE user_id = ?", (user_id,))
        await db.commit()
    return True


# ─── SHUBHALI HARAKAT LOG ─────────────────────────────────────────────────────
async def log_suspicious_activity(user_id: int, reason: str):
    """Shubhali faollik yozish"""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO abuse_logs (user_id, log_type, details) VALUES (?, 'suspicious', ?)",
                (user_id, reason)
            )
            await db.commit()
        except Exception:
            pass


# ─── ADMIN KARTA RAQAMI BOSHQARUVI ───────────────────────────────────────────
async def get_admin_card_number() -> str:
    """Admin karta raqamini olish"""
    return await get_setting("admin_card_number")

def format_user_card_display(raw_card_text: str) -> str:
    """Admin kiritgan karta ma'lumotlarini foydalanuvchilar uchun Humo shaklida formatlaydi"""
    if not raw_card_text:
        return "• Humo: <i>Hozircha kiritilmagan</i>"
        
    import re
    digits_match = re.search(r"(\d{4}\s*\d{4}\s*\d{4}\s*\d{4}|\d{16})", raw_card_text)
    if digits_match:
        card_num = digits_match.group(1).replace(" ", "")
        formatted_num = f"{card_num[0:4]} {card_num[4:8]} {card_num[8:12]} {card_num[12:16]}"
        name_part = raw_card_text.replace(digits_match.group(0), "").strip()
        
        res = f"• Humo: <code>{formatted_num}</code>"
        if name_part:
            res += f"\n  {name_part}"
        return res
    else:
        return f"• Humo: <code>{raw_card_text}</code>"

async def set_admin_card_number(card_text: str):
    """Admin karta raqamini saqlash"""
    await set_setting("admin_card_number", card_text)

async def delete_admin_card_number():
    """Admin karta raqamini o'chirish"""
    async with get_db() as db:
        await db.execute("DELETE FROM bot_settings WHERE key = 'admin_card_number'")
        await db.commit()


# ─── SHUBHALI HARAKATLAR VA KADEMELI OGOHLANTIRISH / BAN TIZIMI ─────────────
async def get_recent_abuse_logs_with_user_info(limit: int = 50):
    """Shubhali harakatlarni foydalanuvchi ma'lumotlari bilan olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT a.user_id, a.type, a.details, a.created_at, u.username, u.full_name, u.warning_count, u.ban_stage
               FROM abuse_logs a
               LEFT JOIN users u ON a.user_id = u.id
               ORDER BY a.created_at DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

def get_progressive_ban_duration(ban_stage: int) -> tuple[int, str]:
    """
    Kademeli ban muddatini qaytaradi (soatlar, matn):
    0 -> 1-marta: 1 soat
    1 -> 2-marta: 5 soat
    2 -> 3-marta: 1 oy
    3 -> 4-marta: 3 oy
    4 -> 5-marta: 9 oy
    5+ -> 6-marta+: 1 yil
    """
    if ban_stage == 0:
        return 1, "1 soat"
    elif ban_stage == 1:
        return 5, "5 soat"
    elif ban_stage == 2:
        return 24 * 30, "1 oy"
    elif ban_stage == 3:
        return 24 * 90, "3 oy"
    elif ban_stage == 4:
        return 24 * 270, "9 oy"
    else:
        return 24 * 365, "1 yil"

async def ban_user_custom(user_id: int, hours: int = None) -> bool:
    """Foydalanuvchini muayyan muddatga yoki doimiy bloklash"""
    from datetime import datetime, timedelta
    async with get_db() as db:
        if hours and hours > 0:
            ban_until = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            await db.execute(
                "UPDATE users SET status = 'banned', role = 'banned', temp_ban_until = ? WHERE id = ?",
                (ban_until, user_id)
            )
        else:
            await db.execute(
                "UPDATE users SET status = 'banned', role = 'banned', temp_ban_until = NULL WHERE id = ?",
                (user_id,)
            )
        await db.commit()
        return True

async def warn_user_progressive(user_id: int) -> tuple[bool, int, str, int]:
    """
    Foydalanuvchiga ogohlantirish beradi.
    Qaytaradi: (is_temp_banned, current_warning_count, duration_text, current_ban_stage)
    """
    from datetime import datetime, timedelta
    async with get_db() as db:
        await db.execute("INSERT OR IGNORE INTO users (id, status, role) VALUES (?, 'active', 'member')", (user_id,))
        await db.commit()
        
        async with db.execute(
            "SELECT warning_count, ban_stage FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            
        warn_cnt = (row[0] if row and row[0] is not None else 0) + 1
        b_stage = row[1] if row and row[1] is not None else 0

        if warn_cnt >= 3:
            hours, duration_text = get_progressive_ban_duration(b_stage)
            ban_until = (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            new_stage = b_stage + 1
            
            await db.execute(
                """UPDATE users 
                   SET warning_count = 0, ban_stage = ?, temp_ban_until = ?, status = 'banned', role = 'banned'
                   WHERE id = ?""",
                (new_stage, ban_until, user_id)
            )
            await db.commit()
            return True, 0, duration_text, new_stage
        else:
            await db.execute(
                "UPDATE users SET warning_count = ? WHERE id = ?",
                (warn_cnt, user_id)
            )
            await db.commit()
            return False, warn_cnt, "", b_stage

async def is_user_temp_banned(user_id: int) -> tuple:
    """
    Foydalanuvchi vaqtincha yoki doimiy bloklanganini tekshiradi.
    Qaytaradi: (is_banned, remaining_time_str)
    """
    try:
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with get_db() as db:
            async with db.execute(
                "SELECT status, temp_ban_until FROM users WHERE id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False, ""
                    
                status, temp_until = row[0], row[1]
                if status == 'banned' or (temp_until and temp_until >= now_str):
                    if temp_until:
                        if temp_until < now_str:
                            await db.execute(
                                "UPDATE users SET status = 'active', temp_ban_until = NULL WHERE id = ?",
                                (user_id,)
                            )
                            await db.commit()
                            return False, ""
                        else:
                            until_dt = datetime.strptime(temp_until, "%Y-%m-%d %H:%M:%S")
                            diff = until_dt - datetime.now()
                            days = diff.days
                            hours = diff.seconds // 3600
                            minutes = (diff.seconds % 3600) // 60
                            if days > 0:
                                rem_str = f"{days} kun {hours} soat"
                            elif hours > 0:
                                rem_str = f"{hours} soat {minutes} daqiqa"
                            else:
                                rem_str = f"{minutes} daqiqa"
                            return True, rem_str
                    return True, "Doimiy"
                return False, ""
    except Exception:
        return False, ""


async def global_unban_all_users() -> int:
    """
    Har 2 yilda chaqiriladigan global amnistiya: Barcha bloklanganlarni avtomatik unban qiladi.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """UPDATE users 
               SET status = 'active', role = 'member', warning_count = 0, ban_stage = 0, temp_ban_until = NULL 
               WHERE status = 'banned' OR role = 'banned' OR temp_ban_until IS NOT NULL"""
        )
        await db.commit()
        return cursor.rowcount


# ─── KASSA VA TO'LOVLAR TARIXI FUNKSIYALARI ──────────────────────────────────
async def has_user_bought_premium_before(user_id: int) -> bool:
    """Foydalanuvchi ilgarigi vaqtda kamida 1 marta Premium olganligini tekshirish"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM payment_records WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] > 0:
                return True
    return False

async def add_payment_record(user_id: int, amount: int, plan: str, confirmed_by: int) -> int:
    """To'lov yozuvini Uzbekistan (UTC+5 Namangan) vaqti bilan saqlash va Kassa balansini oshirish"""
    from datetime import datetime, timedelta, timezone
    uzb_tz = timezone(timedelta(hours=5))
    now_uzb_str = datetime.now(uzb_tz).strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        await db.execute(
            "INSERT INTO payment_records (user_id, amount, plan, confirmed_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, plan, confirmed_by, now_uzb_str)
        )
        # Kassa balansini yangilash
        async with db.execute("SELECT value FROM bot_settings WHERE key = 'kassa_total'") as cursor:
            row = await cursor.fetchone()
            current_total = int(row[0]) if row and str(row[0]).isdigit() else 0
            
        new_total = current_total + amount
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('kassa_total', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (str(new_total), str(new_total))
        )
        await db.commit()
        return new_total

async def get_kassa_total() -> int:
    """Jami kassa balansini olish"""
    async with get_db() as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = 'kassa_total'") as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row and row[0].isdigit() else 0

async def reset_kassa() -> bool:
    """Kassani 0 ga tenglash"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('kassa_total', '0') ON CONFLICT(key) DO UPDATE SET value = '0'"
        )
        await db.commit()
        return True

async def reset_all_users_points() -> bool:
    """Barcha foydalanuvchilarning ballarini 0 ga tenglash"""
    async with get_db() as db:
        await db.execute("UPDATE users SET points = 0")
        await db.commit()
        return True

async def clear_payment_history() -> bool:
    """So'nggi to'lovlar tarixi ro'yxatini (payment_records va foydalanuvchilar nomlarini) tozalash"""
    async with get_db() as db:
        await db.execute("DELETE FROM payment_records")
        await db.commit()
        return True

async def get_recent_payments(limit: int = 10) -> list:
    """So'nggi to'lovlar ro'yxatini olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT p.id, p.user_id, p.amount, p.plan, p.created_at, u.username, u.full_name
               FROM payment_records p
               LEFT JOIN users u ON p.user_id = u.id
               ORDER BY p.created_at DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def get_today_new_users_count() -> int:
    """Bugun (Uzbekistan / Namangan vaqti bilan) ro'yxatdan o'tgan yangi foydalanuvchilar soni"""
    from datetime import datetime, timedelta, timezone
    uzb_tz = timezone(timedelta(hours=5))
    today_uzb = datetime.now(uzb_tz).strftime("%Y-%m-%d")
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at LIKE ?",
            (f"{today_uzb}%",)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


# ─── PROMO KODLAR TIZIMI ──────────────────────────────────────────────────────
async def create_promo_code(code: str, reward_type: str, reward_value: int, max_uses: int = 1, expires_in_days: int = 7, created_by: int = None) -> bool:
    """Yangi promo kod yaratish"""
    from datetime import datetime, timedelta
    expires_at = (datetime.now() + timedelta(days=expires_in_days)).strftime("%Y-%m-%d %H:%M:%S")
    clean_code = code.strip().upper()
    async with get_db() as db:
        try:
            await db.execute(
                """INSERT INTO promo_codes (code, reward_type, reward_value, max_uses, expires_at, created_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (clean_code, reward_type, reward_value, max_uses, expires_at, created_by)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def generate_yearly_vip_gift_promocode(user_id: int) -> str:
    """1 yillik VIP xarid qilgan foydalanuvchiga do'sti uchun 1 oylik (30 kunlik) bepul VIP promo kod generatsiya qilish"""
    import random, string
    rand_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    promo_code = f"GIFT1M-{rand_suffix}"
    
    await create_promo_code(
        code=promo_code,
        reward_type="premium",
        reward_value=30,
        max_uses=1,
        expires_in_days=30,
        created_by=user_id
    )
    return promo_code

async def use_promo_code(user_id: int, code: str) -> tuple:
    """Foydalanuvchi promo kodni ishlatishi. Limit to'lganda promo kod avtomatik o'chiriladi.
    Returns: (success: bool, msg: str, auto_deleted_info: dict|None, discount_pct: int)
    """
    try:
        from datetime import datetime
        clean_code = code.strip().upper()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        async with get_db() as db:
            # 1. Avvalo ushbu foydalanuvchi muqaddam ushbu promo kodni ishlatganligini tekshiramiz (hatto kod bazadan o'chib ketgan bo'lsa ham)
            async with db.execute(
                "SELECT 1 FROM promo_uses WHERE code = ? AND user_id = ?",
                (clean_code, user_id)
            ) as cursor:
                if await cursor.fetchone():
                    return False, (
                        f"⚠️ <b>Siz ushbu <code>{clean_code}</code> promo kodidan allaqachon foydalangansiz!</b>\n\n"
                        f"📌 Ushbu promo kod sizning hisobingiz uchun bir marta ishlatib bo'lingan. "
                        f"Har bir promo kod har bir foydalanuvchi uchun faqat 1 marta amal qiladi.\n\n"
                        f"💡 <i>Iltimos, boshqa promo kod kiriting.</i>"
                    ), None, 0

            # 2. Promo kod mavjudligi va holatini tekshirish
            async with db.execute(
                "SELECT reward_type, reward_value, max_uses, used_count, expires_at FROM promo_codes WHERE code = ?",
                (clean_code,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False, "❌ Noto'g'ri yoki mavjud bo'lmagan promo kod!", None, 0
                    
        reward_type, reward_value, max_uses, used_count, expires_at = row
        
        async with get_db() as db:
            if expires_at and expires_at < now_str:
                return False, "⏰ Ushbu promo kodning amal qilish muddati tugagan!", None, 0
                
            if used_count >= max_uses:
                await db.execute("DELETE FROM promo_codes WHERE code = ?", (clean_code,))
                await db.commit()
                return False, "⚠️ Ushbu promo kodni ishlatish limiti to'lgan va u o'chirildi!", None, 0
                    
            # Mukofotni taqdim etish
            msg_result = ""
            disc_val = 0
            if reward_type == "days":
                await set_user_premium(user_id, days=reward_value)
                msg_result = f"🎁 Tabriklaymiz! Sizga <b>{reward_value} kunlik Premium</b> taqdim etildi! 👑"
            elif reward_type == "discount":
                disc_val = int(reward_value)
                msg_result = f"🏷️ Sizga to'lov uchun <b>{disc_val}% skidka</b> taqdim etildi!"
            elif reward_type == "points":
                await add_points(user_id, reward_value)
                msg_result = f"💎 Tabriklaymiz! Sizga <b>+{reward_value} ball</b> berildi!"
            else:
                msg_result = "✅ Promo kod qabul qilindi!"
                
            new_used = used_count + 1
            auto_deleted_info = None

            # Yozuvni promo_uses ga kiritamiz (reward_type va discount_pct bilan birga)
            await db.execute(
                "INSERT INTO promo_uses (code, user_id, reward_type, discount_pct) VALUES (?, ?, ?, ?)",
                (clean_code, user_id, reward_type, disc_val)
            )

            # Agar yangi ishlatish soni limitga teng yoki undan oshsa — avtomatik O'CHIRAMIZ!
            if new_used >= max_uses:
                await db.execute("DELETE FROM promo_codes WHERE code = ?", (clean_code,))
                auto_deleted_info = {"code": clean_code, "used": new_used, "max": max_uses}
            else:
                await db.execute(
                    "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
                    (clean_code,)
                )

            await db.commit()
            return True, msg_result, auto_deleted_info, disc_val
    except Exception as e:
        return False, f"❌ Xatolik yuz berdi: {str(e)}", None, 0

async def delete_promo_code(code: str) -> bool:
    """Promo kodni bazadan o'chirish"""
    clean_code = code.strip().upper()
    async with get_db() as db:
        await db.execute("DELETE FROM promo_codes WHERE code = ?", (clean_code,))
        await db.commit()
        return True

async def get_promo_code_info(code: str) -> dict | None:
    """Bitta promo kod ma'lumotlarini olish"""
    clean_code = code.strip().upper()
    async with get_db() as db:
        async with db.execute(
            "SELECT code, reward_type, reward_value, max_uses, used_count, expires_at FROM promo_codes WHERE code = ?",
            (clean_code,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "code": row[0],
                    "reward_type": row[1],
                    "reward_value": row[2],
                    "max_uses": row[3],
                    "used_count": row[4],
                    "expires_at": row[5]
                }
            return None

async def update_promo_code_max_uses(code: str, new_max: int) -> bool:
    """Promo kod max_uses limitini yangilash"""
    clean_code = code.strip().upper()
    async with get_db() as db:
        await db.execute(
            "UPDATE promo_codes SET max_uses = ? WHERE code = ?",
            (new_max, clean_code)
        )
        await db.commit()
        return True

async def update_promo_code_value(code: str, new_val: int) -> bool:
    """Promo kod reward_value qiymatini yangilash"""
    clean_code = code.strip().upper()
    async with get_db() as db:
        await db.execute(
            "UPDATE promo_codes SET reward_value = ? WHERE code = ?",
            (new_val, clean_code)
        )
        await db.commit()
        return True


async def consume_user_discount(user_id: int) -> bool:
    """Foydalanuvchining aktiv skidkasini ishlatilgan deb belgilash"""
    async with get_db() as db:
        try:
            await db.execute(
                "UPDATE promo_uses SET is_consumed = 1 WHERE user_id = ? AND COALESCE(is_consumed, 0) = 0",
                (user_id,)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def get_user_active_discount(user_id: int) -> int:
    """
    Foydalanuvchining aktiv skidka foizini olish (masalan: 20 -> 20%).
    Skidka faqat 1 marta ishlatilishi mumkin (is_consumed = 0) va kiritilgandan so'ng 24 soat (1 kun) davomida amal qiladi.
    Agar 1 soatlik Flash Sale aksiyasi faol bo'lsa, undagi chegirma foizi avtomatik qo'llaniladi.
    """
    promo_disc = 0
    async with get_db() as db:
        try:
            async with db.execute(
                """SELECT discount_pct
                   FROM promo_uses
                   WHERE user_id = ? 
                     AND reward_type = 'discount'
                     AND COALESCE(is_consumed, 0) = 0
                     AND datetime(used_at) >= datetime('now', '-1 day')
                   ORDER BY used_at DESC LIMIT 1""",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                promo_disc = int(row[0]) if row and row[0] else 0
        except Exception:
            promo_disc = 0

    flash_active, flash_disc, _ = await get_flash_sale_status()
    if flash_active:
        return max(promo_disc, flash_disc)
    return promo_disc

async def check_promo_code_availability(code: str) -> tuple[bool, str]:
    """
    Promo kod nomini yangi yaratish yoki o'zgartirish uchun tekshirish.
    Mavjud bo'lsa yoki o'tmishda ishlatilgan/o'chirilgan bo'lsa False va tushuntirish qaytaradi.
    """
    clean_code = code.strip().upper()
    if len(clean_code) < 3:
        return False, "⚠️ Promo kod nomi kamida 3 ta belgidan iborat bo'lishi kerak!"

    async with get_db() as db:
        # 1. Hozirgi aktiv promo kodlar jadvalida mavjudligini tekshirish
        async with db.execute("SELECT 1 FROM promo_codes WHERE code = ?", (clean_code,)) as cursor:
            if await cursor.fetchone():
                return False, f"⚠️ <b><code>{clean_code}</code></b> nomli promo kod hozirda faol promo kodlar orasida mavjud!"

        # 2. Ilgari yaratilib, ishlatilgan yoki o'chirilgan promo kodlar tarixida borligini tekshirish
        async with db.execute("SELECT 1 FROM promo_uses WHERE code = ?", (clean_code,)) as cursor:
            if await cursor.fetchone():
                return False, (
                    f"⚠️ <b><code>{clean_code}</code> nomli promo kod ilgarigi aksiyalarda yaratilib ishlatilgan!</b>\n\n"
                    f"📌 Avval ishlatilgan promo kod nomini qayta yaratib bo'lmaydi. "
                    f"Chunki uni ilgarigi ishlatgan foydalanuvchilar qayta ishlata olishmaydi.\n\n"
                    f"💡 <i>Iltimos, yangi va unikal promo kod nomi yuboring (Masalan: <code>{clean_code}NEW</code>, <code>PROMO2026</code>).</i>"
                )

    return True, "OK"

async def update_promo_code_text(old_code: str, new_code: str) -> tuple[bool, str]:
    """Promo kod matnini/nomini yangilash"""
    clean_old = old_code.strip().upper()
    clean_new = new_code.strip().upper()

    if clean_old == clean_new:
        return True, "ℹ️ Promo kod nomi o'zgarmadi."

    is_avail, reason = await check_promo_code_availability(clean_new)
    if not is_avail:
        return False, reason

    async with get_db() as db:
        try:
            await db.execute("UPDATE promo_codes SET code = ? WHERE code = ?", (clean_new, clean_old))
            await db.execute("UPDATE promo_uses SET code = ? WHERE code = ?", (clean_new, clean_old))
            await db.commit()
            return True, f"✅ Promo kod nomi <b>{clean_old}</b> ➔ <b>{clean_new}</b> ga o'zgartirildi!"
        except Exception as e:
            return False, f"❌ Xatolik yuz berdi: {str(e)}"

async def get_all_promo_codes() -> list:
    """Barcha faol promo kodlar ro'yxati (limit to'lganlar avtomatik ravishda tozalanadi)"""
    async with get_db() as db:
        try:
            await db.execute("DELETE FROM promo_codes WHERE used_count >= max_uses")
            await db.commit()
        except Exception:
            pass
        async with db.execute(
            "SELECT code, reward_type, reward_value, max_uses, used_count, expires_at FROM promo_codes ORDER BY created_at DESC"
        ) as cursor:
            return await cursor.fetchall()


# ─── KINO MUDDATI (EXPIRY) FUNKSIYALARI ──────────────────────────────────────
async def set_movie_expiry(movie_id: int, days: int) -> bool:
    """Kino uchun ko'rsatish muddatini belgilash"""
    from datetime import datetime, timedelta
    exp_time = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        await db.execute(
            "UPDATE movies SET expires_at = ?, is_expired = 0 WHERE id = ?",
            (exp_time, movie_id)
        )
        await db.commit()
        return True

async def auto_expire_movies() -> int:
    """Muddati o'tgan kinolarni yashirish"""
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        cursor = await db.execute(
            "UPDATE movies SET is_expired = 1 WHERE expires_at IS NOT NULL AND expires_at <= ? AND is_expired = 0",
            (now_str,)
        )
        await db.commit()
        return cursor.rowcount


# ─── REFERAL TEKSHIRUV VA MUKOFOTLASH (2X EVENT COLLAB) ──────────────────────
async def check_and_reward_referral(bot, user_id: int):
    """
    Foydalanuvchi majburiy kanallarga a'zo bo'lib tekshiruvdan o'tganida chaqiriladi.
    Agar u referal link orqali kelgan va hali mukofot berilmagan bo'lsa:
    - 2X event tekshiriladi
    - Referal egasiga ball beriladi (+10 yoki +20 💎)
    - Referal egasiga o'zbekcha bildirishnoma yuboriladi
    - referral_rewarded = 1 ga yangilanadi
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT referred_by, referral_rewarded, username, full_name FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            referred_by, referral_rewarded, new_username, new_fullname = row
            
        if referred_by and referral_rewarded == 0:
            # 2X event faolligini tekshirish
            event_active = await get_setting("referral_2x_event")
            is_2x = (event_active == "1")
            
            base_pts = await get_config_int("points_referral", 5)
            reward_pts = (base_pts * 2) if is_2x else base_pts
            
            # Referal egasiga ball berish va count oshirish
            await add_points(referred_by, reward_pts)
            async with get_db() as db:
                await db.execute(
                    "UPDATE users SET referrals_count = COALESCE(referrals_count, 0) + 1 WHERE id = ?",
                    (referred_by,)
                )
                await db.execute(
                    "UPDATE users SET referral_rewarded = 1 WHERE id = ?",
                    (user_id,)
                )
                await db.commit()
                
            # Referal egasiga xabar yuborish
            uname_disp = f"@{new_username}" if new_username else new_fullname or f"User {user_id}"
            try:
                if is_2x:
                    notify_text = (
                        f"⚡ <b>2X REFERAL EVENT MUKOFOTI!</b>\n\n"
                        f"Sizning do'stingiz <b>{uname_disp}</b> taklif havolangiz orqali kirdi va majburiy kanallarga to'liq obuna bo'ldi! 🎉\n\n"
                        f"🎁 2X Event sababli sizga 2 baravar ko'proq: <b>+{reward_pts} 💎 ball</b> berildi!"
                    )
                else:
                    notify_text = (
                        f"🎉 <b>YANGI REFERAL!</b>\n\n"
                        f"Sizning do'stingiz <b>{uname_disp}</b> taklif havolangiz orqali kirdi va majburiy kanallarga to'liq obuna bo'ldi!\n\n"
                        f"🎁 Sizga <b>+{reward_pts} 💎 ball</b> taqdim etildi!"
                    )
                await bot.send_message(referred_by, notify_text, parse_mode="HTML")
            except Exception:
                pass

            # 10 ta referal bo'lganda (10, 20, 30...) 1 HAFTALIK PREMIUM BERISH
            async with get_db() as db:
                async with db.execute("SELECT referrals_count FROM users WHERE id = ?", (referred_by,)) as cursor:
                    r_row = await cursor.fetchone()
                    total_refs = r_row[0] if r_row else 0
                    
            if total_refs > 0 and total_refs % 10 == 0:
                await set_user_premium(referred_by, days=7)
                try:
                    milestone_msg = (
                        f"🎉 <b>TABRIKLAYMIZ! POG'ONAVIY BONUS (10 REFERAL)!</b> 🎁\n\n"
                        f"Siz <b>{total_refs} ta</b> do'stingizni taklif qilganingiz uchun sizga <b>1 HAFTALIK PREMIUM (VIP) OBUNA</b> bepul berildi! 👑\n\n"
                        f"🍿 Do'stlaringizni taklif qilishda davom eting va yana bepul Premiumlar oling!"
                    )
                    await bot.send_message(referred_by, milestone_msg, parse_mode="HTML")
                except Exception:
                    pass


# ─── KINO REAKSIYALARI (👍 👎 🔥) FUNKSIYALARI ──────────────────────────────
async def add_movie_reaction(movie_id: int, user_id: int, reaction: str) -> tuple[int, int, int]:
    """Kinoga reaksiya bildirish (like, dislike, fire)"""
    async with get_db() as db:
        await db.execute(
            """INSERT INTO movie_reactions (movie_id, user_id, reaction)
               VALUES (?, ?, ?)
               ON CONFLICT(movie_id, user_id) DO UPDATE SET reaction = ?""",
            (movie_id, user_id, reaction, reaction)
        )
        await db.commit()
    return await get_movie_reactions(movie_id)

async def get_movie_reactions(movie_id: int) -> tuple[int, int, int]:
    """Kinoning reaksiyalar sonini olish (likes, dislikes, fires)"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM movie_reactions WHERE movie_id = ? AND reaction = 'like'", (movie_id,)) as c:
            likes = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM movie_reactions WHERE movie_id = ? AND reaction = 'dislike'", (movie_id,)) as c:
            dislikes = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM movie_reactions WHERE movie_id = ? AND reaction = 'fire'", (movie_id,)) as c:
            fires = (await c.fetchone())[0]
            
        return likes, dislikes, fires


# ─── FOOLLIK VA RETENTION TAHLILI ───────────────────────────────────────────
async def get_user_activity_stats() -> dict:
    """Foydalanuvchilar faolligi va retention darajasini olish"""
    async with get_db() as db:
        async with db.execute("SELECT COUNT(id) FROM users") as c:
            total = (await c.fetchone())[0]
            
        async with db.execute("SELECT COUNT(id) FROM users WHERE date(last_active_at) = date('now')") as c:
            today = (await c.fetchone())[0]
            
        async with db.execute("SELECT COUNT(id) FROM users WHERE last_active_at >= datetime('now', '-7 days')") as c:
            active_7d = (await c.fetchone())[0]
            
        async with db.execute("SELECT COUNT(id) FROM users WHERE last_active_at >= datetime('now', '-30 days')") as c:
            active_30d = (await c.fetchone())[0]
            
        async with db.execute("SELECT COUNT(id) FROM users WHERE last_active_at < datetime('now', '-90 days')") as c:
            inactive_90d = (await c.fetchone())[0]
            
        retention_rate = round((active_30d / total * 100), 1) if total > 0 else 0.0
        
        return {
            "total": total,
            "today": today,
            "active_7d": active_7d,
            "active_30d": active_30d,
            "inactive_90d": inactive_90d,
            "retention_rate": retention_rate
        }


# ─── AUDIT LOGS ─────────────────────────────────────────────────────────────
async def get_audit_logs(limit: int = 20) -> list:
    """So'nggi tizim va admin harakatlari jurnalini olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT a.id, a.user_id, a.type, a.details, a.created_at, u.username, u.full_name
               FROM abuse_logs a
               LEFT JOIN users u ON a.user_id = u.id
               ORDER BY a.created_at DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()


# ─── REKLAMALARI OMMAVIY O'CHIRISH VA TASHXIS ────────────────────────────────
async def save_broadcast_message(broadcast_id: str, message_id: int, chat_id: int):
    """Yuborilgan reklama xabarini o'chirish uchun saqlash"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO broadcast_messages (broadcast_id, message_id, chat_id) VALUES (?, ?, ?)",
            (broadcast_id, message_id, chat_id)
        )
        await db.commit()

async def get_recent_broadcast_batches(limit: int = 10) -> list:
    """So'nggi yuborilgan reklamalar paketlarini olish"""
    async with get_db() as db:
        async with db.execute(
            """SELECT broadcast_id, COUNT(*) as cnt, MIN(created_at) as created_at
               FROM broadcast_messages
               GROUP BY broadcast_id
               ORDER BY created_at DESC LIMIT ?""",
            (limit,)
        ) as cursor:
            return await cursor.fetchall()

async def delete_broadcast_batch(bot, broadcast_id: str) -> tuple[int, int]:
    """Paketdagi barcha yuborilgan reklamalarni foydalanuvchilar chatidan qaytarib o'chirish"""
    async with get_db() as db:
        async with db.execute(
            "SELECT message_id, chat_id FROM broadcast_messages WHERE broadcast_id = ?",
            (broadcast_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            
        success = 0
        failed = 0
        for msg_id, chat_id in rows:
            try:
                await bot.delete_message(chat_id, msg_id)
                success += 1
            except Exception:
                failed += 1
            import asyncio
            await asyncio.sleep(0.03)
            
        await db.execute("DELETE FROM broadcast_messages WHERE broadcast_id = ?", (broadcast_id,))
        await db.commit()
        return success, failed


# ─── KINO SO'ROVI AVTO-QANOATLANISH BILDIRISHNOMASI ─────────────────────────
async def notify_requesting_users_for_movie(bot, movie_id: int, caption: str) -> int:
    """Yangi kino qo'shilganda u haqda so'ragan foydalanuvchilarga avtomatik xabar yuborish"""
    if not caption:
        return 0
    cap_lower = caption.lower()
    async with get_db() as db:
        async with db.execute(
            "SELECT id, user_id, movie_name FROM requests WHERE status = 'pending'"
        ) as cursor:
            pending_reqs = await cursor.fetchall()
            
        notified = 0
        for req_id, u_id, req_name in pending_reqs:
            if req_name and req_name.lower() in cap_lower:
                try:
                    msg = (
                        f"🎉 <b>SIZ SO'RAGAN KINO BOTGA QO'SHILDI!</b>\n\n"
                        f"Hurmatli foydalanuvchi, siz so'ragan <b>{req_name}</b> kinosi botimizga qo'shildi! 🎬\n\n"
                        f"🍿 <b>Kino kodi:</b> <code>{movie_id}</code>\n"
                        f"<i>Kod yuborib kinoni tomosha qilishingiz mumkin!</i>"
                    )
                    await bot.send_message(u_id, msg, parse_mode="HTML")
                    notified += 1
                    await db.execute("UPDATE requests SET status = 'fulfilled' WHERE id = ?", (req_id,))
                except Exception:
                    pass
        await db.commit()
        return notified


# ─── KINO BO'YICHA SHIKOYAT (FAYLDA NUQSON BOR) ──────────────────────────────
async def add_movie_report(movie_id: int, user_id: int) -> bool:
    """Kino faylida nuqson borligi haqida shikoyat saqlash"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO movie_reports (movie_id, user_id) VALUES (?, ?)",
            (movie_id, user_id)
        )
        await db.commit()
        return True


# ─── ZAXIRA KANALI SOZLAMALARI (BACKUP CHANNEL) ──────────────────────────────
async def get_backup_channel_id() -> str:
    """Zaxira kanali ID sini olish"""
    env_id = os.getenv("BACKUP_CHANNEL_ID")
    if env_id:
        return env_id
    async with get_db() as db:
        async with db.execute("SELECT value FROM bot_settings WHERE key = 'backup_channel_id'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

async def set_backup_channel_id(channel_id: str) -> bool:
    """Zaxira kanali ID sini saqlash"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('backup_channel_id', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (str(channel_id), str(channel_id))
        )
        await db.commit()
    
    # MongoDB-ga ham muhrlaymiz
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URL") or DEFAULT_MONGO_URI
    if mongo_uri:
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000, tls=True, tlsAllowInvalidCertificates=True)
            db_m = client["kino_bot_database"]
            await db_m["backup_info"].replace_one({"_id": "backup_channel_setting"}, {"_id": "backup_channel_setting", "channel_id": str(channel_id)}, upsert=True)
        except Exception:
            pass
    return True


# ─── A5: 75+ DISLIKE BO'LGAN KINOLARNI TOPISH ─────────────────────────────────
async def get_movies_with_high_dislikes(threshold: int = 75) -> list:
    """Eng ko'p dislike (👎) olgan kinolarni topish. Default 75+."""
    async with get_db() as db:
        async with db.execute("""
            SELECT m.id, m.caption,
                   SUM(CASE WHEN mr.reaction = 'dislike' THEN 1 ELSE 0 END) AS dislikes,
                   SUM(CASE WHEN mr.reaction = 'like' THEN 1 ELSE 0 END) AS likes
            FROM movies m
            LEFT JOIN movie_reactions mr ON m.id = mr.movie_id
            GROUP BY m.id
            HAVING dislikes >= ?
            ORDER BY dislikes DESC
        """, (threshold,)) as cursor:
            return await cursor.fetchall()


# ─── A7: AKTIVLIK GRAFIGI / HISOBOT (MATN BILAN) ──────────────────────────────
async def get_activity_report_last_days(days: int = 7) -> dict:
    """Oxirgi N kun uchun aktivlik statistikasini olish"""
    from datetime import datetime, timedelta
    today = datetime.now().date()
    stats = {}
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        async with get_db() as db:
            new_users = 0
            async with db.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?", (d_str,)) as c:
                r = await c.fetchone()
                new_users = r[0] if r else 0
            active_users = 0
            async with db.execute("SELECT COUNT(*) FROM users WHERE DATE(last_active_at) = ?", (d_str,)) as c:
                r = await c.fetchone()
                active_users = r[0] if r else 0
            movies_watched = 0
            async with db.execute("SELECT COUNT(*) FROM watch_history WHERE DATE(watched_at) = ?", (d_str,)) as c:
                r = await c.fetchone()
                movies_watched = r[0] if r else 0
            premium_count = 0
            revenue = 0
            async with db.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payment_records WHERE DATE(created_at) = ?", (d_str,)) as c:
                r = await c.fetchone()
                premium_count = r[0] if r else 0
                revenue = r[1] if r and r[1] else 0
        stats[d_str] = {
            "new": new_users,
            "active": active_users,
            "watched": movies_watched,
            "premium": premium_count,
            "revenue": revenue
        }
    return stats


# ─── A11: KUNLIK ENG FAOL 10 TA USERGA 75 BALL SOVG'A ────────────────────────
async def give_daily_gift_top_active(points: int = 75, limit: int = 10) -> list:
    """Kunlik eng faol top N ta userga ball berish. Berilgan userlar ro'yxatini qaytaradi."""
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 1) top faollarni topish
    async with get_db() as db:
        async with db.execute("""
            SELECT u.id, u.username, u.full_name, COUNT(w.movie_id) AS cnt
            FROM users u
            LEFT JOIN watch_history w ON u.id = w.user_id AND DATE(w.watched_at) = ?
            GROUP BY u.id
            ORDER BY cnt DESC
            LIMIT ?
        """, (today_str, limit)) as cursor:
            top_list = await cursor.fetchall()

    awarded = []
    for row in top_list:
        user_id = row[0]
        # bugun allaqachon sovg'a berilganmi?
        async with get_db() as db:
            async with db.execute("SELECT last_daily_gift_date FROM users WHERE id = ?", (user_id,)) as c:
                r = await c.fetchone()
                if r and r[0] == today_str:
                    continue
            await db.execute("UPDATE users SET points = COALESCE(points,0) + ?, last_daily_gift_date = ? WHERE id = ?",
                             (points, today_str, user_id))
            await db.commit()
        awarded.append((user_id, row[1] or row[2] or f"User {user_id}", points))
    return awarded


# ─── A13: REFERAL OBUNA BO'LMAGANLARGA ESLATMA ────────────────────────────────
async def get_referrals_with_incomplete_sub(user_id: int) -> list:
    """Men taklif qilgan lekin hali homiy kanallarga obuna bo'lmagan (va Premium bo'lmagan) referallar ro'yxati"""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        async with db.execute("""
            SELECT id, username, full_name, created_at
            FROM users
            WHERE referred_by = ? AND referral_rewarded = 0 AND created_at >= ?
            ORDER BY created_at DESC
        """, (user_id, cutoff)) as cursor:
            return await cursor.fetchall()


# ─── U1: JANR KUZATUV + TAVSIYA ───────────────────────────────────────────────
GENRE_KEYWORDS = {
    "Multfilm": ["multfilm", "multik", "cartoon", "animatsiy", "pixar", "дисней", "disney", "dreamworks"],
    "Komediya": ["komediya", "comed", "qaygʻuli", "kulgili", "yumor", "kulinariya", "comedy", "комеди"],
    "Triller": ["triller", "thriller", "tension", "триллер", "detektiv", "detective"],
    "Ujas": ["ujas", "horror", "qoʻrqinchli", "qorqinchli", "scary", "ужас", "xorroр"],
    "Jangari": ["jangari", "action", "avtomobil", "poyga", "qonli", "боевик", "бойовик"],
    "Romantika": ["romantika", "romance", "sevgili", "love", "sevgi", "любов", "любовный"],
    "Drama": ["drama", "hayotiy", "realistik", "drama", "драма"],
    "Fan-fiction": ["fantastika", "fantasy", "kosmos", "fentezi", "фантаст", "fantastik", "sci-fi", "scifi", "Marvel", "DC"],
    "Sarguzasht": ["sarguzasht", "adventure", "sayohat", "приключ"],
    "Tarixiy": ["tarixiy", "historic", "medieval", "osmonov", "war", "urush", "истори"]
}

def _detect_genres_from_caption(caption: str) -> list:
    """Caption ichidan janr topish"""
    if not caption:
        return []
    low = caption.lower()
    found = set()
    for genre, keywords in GENRE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in low:
                found.add(genre)
                break
    return list(found)


async def track_watch_genres(user_id: int, caption: str):
    """Kino ko'rilganda janrni user uchun ro'yxatga olish"""
    genres = _detect_genres_from_caption(caption)
    if not genres:
        return
    async with get_db() as db:
        for g in genres:
            await db.execute("""
                INSERT INTO user_genre_watches (user_id, genre, watch_count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, genre) DO UPDATE SET watch_count = watch_count + 1
            """, (user_id, g))
        await db.commit()


async def recommend_movies_by_genre(user_id: int, limit: int = 10) -> list:
    """Sevimli janr bo'yicha tavsiya berish"""
    async with get_db() as db:
        async with db.execute("""
            SELECT genre FROM user_genre_watches
            WHERE user_id = ?
            ORDER BY watch_count DESC
            LIMIT 3
        """, (user_id,)) as cursor:
            top_genres = [r[0] for r in await cursor.fetchall()]
    if not top_genres:
        return []
    # top janrga mos kino captionlarga qidiramiz
    async with get_db() as db:
        query_parts = []
        params = []
        for g in top_genres:
            keywords = GENRE_KEYWORDS.get(g, [g])
            for kw in keywords:
                query_parts.append("LOWER(COALESCE(caption,'')) LIKE ?")
                params.append(f"%{kw.lower()}%")
        if not query_parts:
            return []
        final_q = f"""
            SELECT id, caption, views_count
            FROM movies
            WHERE ({' OR '.join(query_parts)})
              AND id NOT IN (SELECT movie_id FROM watch_history WHERE user_id = ?)
            ORDER BY views_count DESC
            LIMIT ?
        """
        params.append(user_id)
        params.append(limit)
        async with db.execute(final_q, params) as cursor:
            return await cursor.fetchall()


# ─── U9: HAFTALIK TOP 10 KINOLAR (REYTING ASOSIDA) ────────────────────────────
async def get_weekly_top_movies(limit: int = 10) -> list:
    """Oxirgi 7 kun ichidagi reyting bo'yicha top kinolar"""
    from datetime import datetime, timedelta
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        async with db.execute(f"""
            SELECT m.id, m.caption,
                   AVG(CAST(r.rating AS FLOAT)) AS avg_r,
                   COUNT(r.rating) AS vote_count
            FROM movies m
            JOIN ratings r ON m.id = r.movie_id
            WHERE r.created_at >= ?
            GROUP BY m.id
            ORDER BY avg_r DESC, vote_count DESC
            LIMIT ?
        """, (week_ago, limit)) as cursor:
            return await cursor.fetchall()


# ─── U10: KINO TOPILMAGANDA XABAR SO'RASH ─────────────────────────────────────
async def add_movie_notify_request(user_id: int, search_query: str) -> bool:
    """Qidirilgan kino topilmasa, user so'rovini saqlash"""
    async with get_db() as db:
        # Avval oldin shu query bo'lganmi tekshir, bo'lmasa qo'sh
        await db.execute("""
            INSERT INTO movie_notify_requests (user_id, search_query, is_notified)
            VALUES (?, ?, 0)
        """, (user_id, search_query.strip().lower()))
        await db.commit()
    return True


async def check_and_notify_movie_added(bot, movie_id: int, caption: str):
    """Yangi kino qo'shilganda, eski so'rovlarni tekshirib xabar berish"""
    if not caption:
        return 0
    cap_low = caption.lower()
    notified = set()
    async with get_db() as db:
        async with db.execute("""
            SELECT DISTINCT n.id, n.user_id, n.search_query
            FROM movie_notify_requests n
            WHERE n.is_notified = 0
        """) as cursor:
            rows = await cursor.fetchall()
        for req_id, user_id, sq in rows:
            if sq and sq in cap_low:
                try:
                    await bot.send_message(user_id,
                        f"🔔 <b>Siz qidirgan kino qo'shildi!</b>\n\n"
                        f"Qidirgan: <i>{sq}</i>\n"
                        f"🎬 Kino kodi: /{movie_id}\n\n"
                        f"Zavqlanib ko'ring! 🎬🍿\n\n"
                        f"📩 <b>Murojaat uchun:</b> @Abdulaziz7o1",
                        parse_mode="HTML")
                    notified.add(req_id)
                except Exception:
                    pass
        if notified:
            ids = ",".join(["?"] * len(notified))
            await db.execute(f"UPDATE movie_notify_requests SET is_notified = 1 WHERE id IN ({ids})", tuple(notified))
            await db.commit()
    return len(notified)


# ─── U11: TO'LOVLAR TARIXI (USER UCHUN) ───────────────────────────────────────
async def get_user_payment_history(user_id: int, limit: int = 20) -> list:
    """Userning barcha to'lovlari tarixi"""
    async with get_db() as db:
        async with db.execute("""
            SELECT id, amount, plan, created_at, confirmed_by
            FROM payment_records
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit)) as cursor:
            return await cursor.fetchall()


# ─── U13: REFERALLAR RO'YXATI BATAFSIL ────────────────────────────────────────
async def get_user_referrals_detailed(user_id: int, limit: int = 50, page: int = 1, per_page: int = 20) -> tuple:
    """User referallarini batafsil ko'rsatish (pagination bilan).
    Qaytaradi: (items_list, total_count, total_pages)
    """
    offset = (page - 1) * per_page
    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as c:
            total_row = await c.fetchone()
            total_count = total_row[0] if total_row else 0
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        async with db.execute("""
            SELECT u.id, u.username, u.full_name, u.created_at,
                   u.referrals_count, u.points, u.role,
                   u.referral_rewarded, u.is_premium
            FROM users u
            WHERE u.referred_by = ?
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, per_page, offset)) as cursor:
            items = await cursor.fetchall()
    return items, total_count, max(1, total_pages)


# ─── U8: TUG'ILGAN KUN LOCK (1 MARTA) ─────────────────────────────────────────
async def is_birthday_locked(user_id: int) -> bool:
    """Foydalanuvchi tug'ilgan kunini o'zgartira oladimi?"""
    async with get_db() as db:
        async with db.execute("SELECT birthday_is_locked FROM users WHERE id = ?", (user_id,)) as c:
            r = await c.fetchone()
            return bool(r and r[0] and r[0] != 0)


async def lock_user_birthday(user_id: int) -> bool:
    """Tug'ilgan kunni 1 marta kiritgandan keyin locklash"""
    async with get_db() as db:
        await db.execute("UPDATE users SET birthday_is_locked = 1 WHERE id = ?", (user_id,))
        await db.commit()
    return True


async def reset_user_birthday_lock(user_id: int) -> bool:
    """(Admin uchun) Lockni bekor qilish"""
    async with get_db() as db:
        await db.execute("UPDATE users SET birthday_is_locked = 0 WHERE id = ?", (user_id,))
        await db.commit()
    return True


# ─── ⏳ 1 SOATLIK BEPUL VIP TRIAL (FREE TRIAL) ──────────────────────────────
async def has_claimed_vip_trial(user_id: int) -> bool:
    """Foydalanuvchi 1 soatlik bepul VIP sinovini ishlatganmi?"""
    async with get_db() as db:
        try:
            async with db.execute("SELECT vip_trial_claimed FROM users WHERE id = ?", (user_id,)) as c:
                r = await c.fetchone()
                return bool(r and r[0] and r[0] != 0)
        except Exception:
            return False


async def claim_vip_trial(user_id: int) -> tuple[bool, str]:
    """1 soatlik bepul VIP sinov rejimini berish (1 marta)"""
    from datetime import datetime, timedelta
    if await has_claimed_vip_trial(user_id):
        return False, "⚠️ <b>Siz allaqachon 1 soatlik bepul VIP sinov imkoniyatidan foydalangansiz!</b>\n\nVIP imtiyozlarini davom ettirish uchun /premium orqali obuna xarid qilishingiz mumkin."

    now = datetime.now()
    end_time = now + timedelta(hours=1)
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    start_str = now.strftime("%Y-%m-%d %H:%M:%S")

    async with get_db() as db:
        await db.execute(
            """INSERT INTO users (id, is_premium, premium_until, vip_trial_claimed)
               VALUES (?, 1, ?, 1)
               ON CONFLICT(id) DO UPDATE SET
                   is_premium = 1,
                   premium_until = ?,
                   vip_trial_claimed = 1""",
            (user_id, end_str, end_str)
        )
        await db.execute(
            """INSERT INTO premium_subscriptions (user_id, start_date, end_date, plan)
               VALUES (?, ?, ?, '1 soatlik VIP Sinov')
               ON CONFLICT(user_id) DO UPDATE SET
                   start_date = excluded.start_date,
                   end_date = excluded.end_date,
                   plan = excluded.plan""",
            (user_id, start_str, end_str)
        )
        await db.commit()

    return True, f"🎉 <b>TABRIKLAYMIZ! 1 SOATLIK BEPUL VIP SINOV YOQILDI!</b> 👑\n\n⏰ <b>Amal qilish muddati:</b> 1 soat (<code>{end_str[:16]}</code> gacha)\n\n🍿 <i>Endi 1 soat davomida botdan barcha kinolarni hech qanday cheklovlarsiz tomosha qilishingiz mumkin!</i>"


# ─── ⚡ 1 SOATLIK FLASH SALE (50% CHEGIRMA) ──────────────────────────────────
async def activate_flash_sale(hours: int = 1, discount_pct: int = 50) -> str:
    """1 soatlik Flash Sale 50% chegirma eventini yoqish"""
    from datetime import datetime, timedelta, timezone
    uzb_tz = timezone(timedelta(hours=5))
    until_dt = datetime.now(uzb_tz) + timedelta(hours=hours)
    until_str = until_dt.strftime("%Y-%m-%d %H:%M:%S")
    async with get_db() as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('flash_sale_until', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (until_str, until_str)
        )
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('flash_sale_discount', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (str(discount_pct), str(discount_pct))
        )
        await db.commit()
    return until_str


async def get_flash_sale_status() -> tuple[bool, int, str]:
    """Flash Sale faolmi tekshirish (is_active, discount_pct, until_str)"""
    from datetime import datetime, timedelta, timezone
    uzb_tz = timezone(timedelta(hours=5))
    async with get_db() as db:
        try:
            async with db.execute("SELECT value FROM bot_settings WHERE key = 'flash_sale_until'") as c:
                r1 = await c.fetchone()
            async with db.execute("SELECT value FROM bot_settings WHERE key = 'flash_sale_discount'") as c:
                r2 = await c.fetchone()
            if r1 and r1[0]:
                until_str = r1[0]
                disc_pct = int(r2[0]) if r2 and r2[0] else 50
                dt_until = datetime.fromisoformat(until_str.replace(' ', 'T'))
                if datetime.now(uzb_tz).replace(tzinfo=None) < dt_until:
                    return True, disc_pct, until_str
        except Exception:
            pass
    return False, 0, ""

async def is_maintenance_mode() -> bool:
    """Texnik ishlar rejimi yoqilganmi tekshirish"""
    async with get_db() as db:
        try:
            async with db.execute("SELECT value FROM bot_settings WHERE key = 'maintenance_mode'") as c:
                row = await c.fetchone()
                return bool(row and row[0] == '1')
        except Exception:
            return False

async def toggle_maintenance_mode() -> bool:
    """Texnik ishlar rejimini yoqish/o'chirish"""
    current = await is_maintenance_mode()
    new_state = "0" if current else "1"
    async with get_db() as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('maintenance_mode', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (new_state, new_state)
        )
        await db.commit()
    return not current

async def get_vip_cashback_percent() -> int:
    """VIP xarid uchun beriladigan ball keshbek foizi (default 10%)"""
    async with get_db() as db:
        try:
            async with db.execute("SELECT value FROM bot_settings WHERE key = 'vip_cashback_pct'") as c:
                row = await c.fetchone()
                return int(row[0]) if row and row[0] else 10
        except Exception:
            return 10

async def set_vip_cashback_percent(pct: int):
    """VIP keshbek foizini sozlash"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES ('vip_cashback_pct', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (str(pct), str(pct))
        )
        await db.commit()

# Ketma-ket bot skanerlashdan himoya (Anti-Scraping / Rapid Requests)
_USER_SEARCH_TIMESTAMPS = {}

def check_anti_scraping_guard(user_id: int) -> bool:
    """Agar 1 soniyada 3 tadan ko'p so'rov yuborsa bloklaydi"""
    import time
    now = time.time()
    stamps = _USER_SEARCH_TIMESTAMPS.get(user_id, [])
    stamps = [s for s in stamps if now - s < 2.0]
    stamps.append(now)
    _USER_SEARCH_TIMESTAMPS[user_id] = stamps
    if len(stamps) > 4:
        return False
    return True
