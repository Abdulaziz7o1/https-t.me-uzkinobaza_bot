import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from aiohttp import ClientTimeout, TCPConnector

import config
from database.connection import init_db
from handlers import user, admin, join_request, payment
from middlewares.check_sub import CheckSubMiddleware, StateCancelMiddleware, AntiFloodMiddleware

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

async def backup_scheduler(bot: Bot):
    """Har 24 soatda ma'lumotlar bazasini adminlarga zaxira nusxasi sifatida jo'natadi"""
    # 24 soat kutish (86400 soniya)
    while True:
        await asyncio.sleep(86400)
        logging.info("Avtomatik ma'lumotlar bazasi zaxiralanmoqda...")
        if os.path.exists("kino_bot.db"):
            file = FSInputFile("kino_bot.db")
            for admin_id in config.ADMINS:
                try:
                    await bot.send_document(
                        chat_id=admin_id,
                        document=file,
                        caption="💾 <b>Kunlik avtomatik zaxira nusxasi (Backup)</b>"
                    )
                except Exception as e:
                    logging.error(f"Zaxira nusxasini admin {admin_id} ga yuborishda xato: {e}")

async def broadcast_scheduler(bot: Bot):
    """Har 60 soniyada rejalashtirilgan reklamalarni tekshiradi va yuboradi"""
    from datetime import datetime
    import database.requests as db_req
    
    while True:
        await asyncio.sleep(60)
        try:
            pending = await db_req.get_pending_broadcasts()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for bid, chat_id, message_id, send_at in pending:
                if send_at <= now_str:
                    logging.info(f"Rejalashtirilgan reklama yuborilmoqda: ID {bid}")
                    
                    users = await db_req.get_all_users()
                    success_count = 0
                    failed_count = 0
                    
                    for user_id in users:
                        try:
                            await bot.copy_message(
                                chat_id=user_id,
                                from_chat_id=chat_id,
                                message_id=message_id
                            )
                            success_count += 1
                            await asyncio.sleep(0.05) # Rate limiting
                        except Exception:
                            failed_count += 1
                            
                    # Kanallarga ham yuborish
                    try:
                        db_channels = await db_req.get_sponsor_channels()
                        all_ch = list(config.CHANNELS) + [c[1] for c in db_channels]
                        for ch in all_ch:
                            try:
                                await bot.copy_message(
                                    chat_id=ch,
                                    from_chat_id=chat_id,
                                    message_id=message_id
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass

                    await db_req.mark_broadcast_sent(bid)
                    logging.info(f"Rejalashtirilgan reklama yuborildi: {success_count} ta, xato: {failed_count} ta")
                    
                    for admin_id in config.ADMINS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"📅 <b>Rejalashtirilgan reklama muvaffaqiyatli yuborildi!</b>\n\n"
                                f"✅ Yuborildi: {success_count} ta\n"
                                f"❌ Yuborilmagan: {failed_count} ta"
                            )
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Rejalashtirilgan reklama schedulerida xato: {e}")

async def daily_movie_scheduler(bot: Bot):
    """Har kuni soat 09:00 (Tashkent vaqti)da avtomatik Kun Kinosini yuboradi"""
    from datetime import datetime, timedelta, timezone
    import database.requests as db_req
    
    uzb_tz = timezone(timedelta(hours=5))
    while True:
        await asyncio.sleep(60)
        try:
            now = datetime.now(uzb_tz)
            if now.hour == 9:
                today_movie = await db_req.get_today_daily_movie()
                if not today_movie:
                    logging.info("Avtomatik Kun Kinosi yuborilmoqda...")
                    movie = await db_req.get_random_movie()
                    if movie:
                        movie_id, file_id, caption = movie
                        await db_req.set_today_daily_movie(movie_id)
                        
                        users = await db_req.get_all_users()
                        success = 0
                        for uid in users:
                            try:
                                cap = f"☀️ <b>Bugungi Kun Kinosi</b>\n\n{caption or ''}\n\n🎬 Kino kodi: <code>{movie_id}</code>\n🤖 {config.BOT_USERNAME}"
                                await bot.send_video(uid, file_id, caption=cap, parse_mode="HTML")
                                success += 1
                                await asyncio.sleep(0.05) # Rate limit
                            except Exception:
                                pass
                        logging.info(f"Avtomatik Kun Kinosi {success} ta foydalanuvchiga yuborildi.")
        except Exception as e:
            logging.error(f"Kun Kinosi schedulerida xato: {e}")

async def biweekly_premium_scheduler(bot: Bot):
    """Har 14 kunda Top 3 ta foydalanuvchiga 1 haftalik Premium taqdim etadi"""
    from datetime import datetime, timedelta
    import database.requests as db_req
    
    while True:
        await asyncio.sleep(3600)
        try:
            last_run = await db_req.get_setting("last_biweekly_premium_run")
            now = datetime.now()
            
            should_run = False
            if not last_run:
                should_run = True
            else:
                last_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                if now - last_dt >= timedelta(days=14):
                    should_run = True
                    
            if should_run:
                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                await db_req.set_setting("last_biweekly_premium_run", now_str)
                
                top_users = await db_req.get_points_leaderboard(3)
                if top_users:
                    logging.info("Har 2 haftalik Top 3 Premium mukofotlari berilmoqda...")
                    winners_txt = ""
                    for rank, (uid, username, full_name, pts) in enumerate(top_users, 1):
                        await db_req.set_user_premium(uid, days=7)
                        uname = f"@{username}" if username else full_name or str(uid)
                        winners_txt += f"{rank}-o'rin: {uname} ({pts} 💎)\n"
                        
                        try:
                            await bot.send_message(
                                uid,
                                f"🎉 <b>TABRIKLAYMIZ!</b>\n\n"
                                f"👑 Siz 2 haftalik ballar musobaqasida <b>{rank}-o'rinni</b> egallaganingiz uchun sizga <b>1 HAFTALIK PREMIUM (VIP) MAQOMI</b> taqdim etildi!\n\n"
                                f"🍿 Maroqli tomosha tilaymiz!",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
                            
                    for admin_id in config.ADMINS:
                        try:
                            await bot.send_message(
                                admin_id,
                                f"🏆 <b>Har 2 haftalik Top 3 Premium g'oliblari aniqlandi:</b>\n\n{winners_txt}\n"
                                f"G'oliblarga 1 haftalik Premium avtomatik berildi! ✅",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Bi-weekly Premium scheduler xatosi: {e}")

async def birthday_scheduler(bot: Bot):
    """Har kuni soat 09:00 da bugun tug'ilgan kunli a'zolarga +50 ball va 1 kun VIP beradi"""
    from datetime import datetime, timedelta, timezone
    import database.requests as db_req
    
    uzb_tz = timezone(timedelta(hours=5))
    while True:
        await asyncio.sleep(600)  # Har 10 daqiqada tekshirish
        try:
            now = datetime.now(uzb_tz)
            if now.hour == 9:
                curr_year = now.year
                today_bdays = await db_req.get_today_birthdays()
                
                for uid, full_name, username, birthday, last_given_year in today_bdays:
                    if birthday == "BLOCKED_UNDERAGE":
                        continue
                    if last_given_year and last_given_year == curr_year:
                        continue
                        
                    await db_req.add_points(uid, 50)
                    await db_req.set_user_premium(uid, days=1)
                    await db_req.mark_birthday_bonus_given(uid, curr_year)
                    
                    try:
                        msg = (
                            f"🎉 <b>TUG'ILGAN KUNINGIZ MUBORAK BO'LSIN!</b> 🎂\n\n"
                            f"Kino Bot jamoasi sizni bugungi shukrona kuningiz bilan samimiy muborakbod etadi!\n\n"
                            f"🎁 <b>Sizga berilgan sovg'alar:</b>\n"
                            f"  • <b>+50 💎 ball</b>\n"
                            f"  • <b>👑 1 kunlik VIP maqomi</b>\n\n"
                            f"🍿 Kuningiz maroqli o'tsin!"
                        )
                        await bot.send_message(uid, msg, parse_mode="HTML")
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Birthday scheduler xatosi: {e}")

async def admin_pin_reminder_scheduler(bot: Bot):
    """Har 2 haftada (14 kun) adminlarga 2FA PIN yangilash eslatmasi yuboradi"""
    import database.requests as db_req
    while True:
        await asyncio.sleep(86400) # Kuniga 1 marta
        try:
            admins_to_remind = await db_req.get_admins_pin_for_reminder()
            for admin_id, last_changed in admins_to_remind:
                try:
                    msg = (
                        f"🔐 <b>XAVFSIZLIK OGOHLANTIRISHI:</b>\n\n"
                        f"Admin PIN-kodingiz 14 kundan ortiq vaqt davomida yangilanmadi.\n"
                        f"Bot xavfsizligini ta'minlash uchun <code>/setpin</code> buyrug'i orqali kodingizni yangilashingiz tavsiya etiladi."
                    )
                    await bot.send_message(admin_id, msg, parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Admin PIN reminder scheduler xatosi: {e}")

async def inactive_cleanup_reminder_scheduler(bot: Bot):
    """Har 90 kunda (3 oyda) adminlarga nofaol foydalanuvchilarni tozalash eslatmasi yuboradi"""
    from datetime import datetime, timedelta
    import database.requests as db_req
    
    while True:
        await asyncio.sleep(86400)
        try:
            last_run = await db_req.get_setting("last_inactive_cleanup_check")
            now = datetime.now()
            
            should_run = False
            if not last_run:
                should_run = True
            else:
                last_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                if now - last_dt >= timedelta(days=90):
                    should_run = True
                    
            if should_run:
                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                await db_req.set_setting("last_inactive_cleanup_check", now_str)
                
                inactives = await db_req.get_inactive_users(days=90)
                if inactives:
                    for admin_id in config.ADMINS:
                        try:
                            msg = (
                                f"🧹 <b>NOFAOL FOYDALANUVCHILARNI TOZALASH (3 OY):</b>\n\n"
                                f"Oxirgi 90 kun ichida botga kirmagan <b>{len(inactives)} ta</b> foydalanuvchi mavjud.\n"
                                f"Ularni o'chirib bazani tozalash uchun <code>/cleanup_inactive</code> buyrug'ini yuboring."
                            )
                            await bot.send_message(admin_id, msg, parse_mode="HTML")
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Inactive cleanup reminder xatosi: {e}")

async def biyearly_global_unban_scheduler(bot: Bot):
    """Har 2 yilda (730 kun) barcha bloklanganlarni avtomatik unban qiladi (Global amnistiya)"""
    from datetime import datetime, timedelta
    import database.requests as db_req
    
    while True:
        await asyncio.sleep(86400) # Kuniga 1 marta
        try:
            last_run = await db_req.get_setting("last_biyearly_global_unban")
            now = datetime.now()
            
            should_run = False
            if not last_run:
                await db_req.set_setting("last_biyearly_global_unban", now.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                last_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                if now - last_dt >= timedelta(days=730):
                    should_run = True
                    
            if should_run:
                now_str = now.strftime("%Y-%m-%d %H:%M:%S")
                await db_req.set_setting("last_biyearly_global_unban", now_str)
                
                unbanned_cnt = await db_req.global_unban_all_users()
                if unbanned_cnt > 0:
                    for admin_id in config.ADMINS:
                        try:
                            msg = (
                                f"🔓 <b>2 YILLIK GLOBAL AMNISTIYA:</b>\n\n"
                                f"Barcha bloklangan foydalanuvchilar (<b>{unbanned_cnt} ta</b>) avtomatik ravishda blokdan chiqarildi va ogohlantirishlari tozalandi! ✅"
                            )
                            await bot.send_message(admin_id, msg, parse_mode="HTML")
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Bi-yearly global unban scheduler xatosi: {e}")

async def daily_kassa_report_scheduler(bot: Bot):
    """Har kuni soat 09:00 (O'zbekiston / Namangan vaqti) da adminlarga 2 ta alohida xabar yuboradi:
       1) Yangi foydalanuvchilar hisoboti
       2) Kassa hisoboti (ostida Kassani 0 ga tenglash tugmasi bilan)
    """
    from datetime import datetime, timedelta, timezone
    import database.requests as db_req
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    uzb_tz = timezone(timedelta(hours=5))
    while True:
        await asyncio.sleep(60) # Har 1 daqiqada tekshirish
        try:
            now = datetime.now(uzb_tz)
            if now.hour == 9:
                today_str = now.strftime("%Y-%m-%d")
                last_sent = await db_req.get_setting("last_daily_kassa_report_date")
                
                if last_sent != today_str:
                    await db_req.set_setting("last_daily_kassa_report_date", today_str)
                    
                    new_users = await db_req.get_today_new_users_count()
                    kassa_total = await db_req.get_kassa_total()
                    
                    msg1 = (
                        f"📊 <b>KUNLIK YANGI FOYDALANUVCHILAR HISOBOTI (09:00):</b>\n\n"
                        f"📥 Bugun botga <b>{new_users} ta</b> yangi foydalanuvchi qo'shildi!"
                    )
                    
                    kb = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="♻️ Kassani 0 ga tenglash", callback_data="kassa_reset_confirm")
                    ]])
                    
                    msg2 = (
                        f"💰 <b>KUNLIK KASSA HISOBOTI (09:00):</b>\n\n"
                        f"💵 <b>Hozirgi Kassa Balansi:</b> <code>{kassa_total:,} UZS</code>\n\n"
                        f"<i>Kassani 0 ga tenglash uchun quyidagi tugmani bosing:</i>"
                    )
                    
                    for admin_id in config.ADMINS:
                        try:
                            # 1-xabar: Yangi foydalanuvchilar
                            await bot.send_message(admin_id, msg1, parse_mode="HTML")
                            # 2-xabar: Kassa va 0 ga tenglash tugmasi
                            await bot.send_message(admin_id, msg2, parse_mode="HTML", reply_markup=kb)
                        except Exception:
                            pass
        except Exception as e:
            logging.error(f"Daily Kassa Report scheduler xatosi: {e}")

async def auto_expire_movies_scheduler(bot: Bot):
    """Har kuni soat 03:00 da ko'rsatish muddati tugagan kinolarni avtomatik yashiradi"""
    from datetime import datetime
    import database.requests as db_req
    
    while True:
        await asyncio.sleep(3600)
        try:
            now = datetime.now()
            if now.hour == 3:
                expired_cnt = await db_req.auto_expire_movies()
                if expired_cnt > 0:
                    logging.info(f"Muddati o'tgan {expired_cnt} ta kino avtomatik yashirildi.")
        except Exception as e:
            logging.error(f"Auto Expire Movies scheduler xatosi: {e}")

async def on_startup(bot: Bot):
    """Bot ishga tushganda bajariladigan amallar"""
    logging.info("Bot ishga tushmoqda...")
    # Baza jadvallarini tekshirish/yaratish
    await init_db()
    import database.requests as db_req
    await db_req.ensure_movie_requests_table()
    
    # Avtomatik vazifalarni ishga tushirish (Background tasks)
    asyncio.create_task(backup_scheduler(bot))
    asyncio.create_task(broadcast_scheduler(bot))
    asyncio.create_task(daily_movie_scheduler(bot))
    asyncio.create_task(biweekly_premium_scheduler(bot))
    asyncio.create_task(birthday_scheduler(bot))
    asyncio.create_task(admin_pin_reminder_scheduler(bot))
    asyncio.create_task(inactive_cleanup_reminder_scheduler(bot))
    asyncio.create_task(biyearly_global_unban_scheduler(bot))
    asyncio.create_task(daily_kassa_report_scheduler(bot))
    try:
        await db_req.restore_master_backup_on_startup()
    except Exception as e:
        logging.warning(f"Master backup tiklashda xato: {e}")
    logging.info("Barcha schedulerlar va 24/7 Render Keep-Alive Auto-Ping muvaffaqiyatli ishga tushdi.")

async def restore_movies_backup_on_startup(bot: Bot):
    """Server qayta ishga tushganida bazada kinolar 0 ta bo'lsa, zaxiradan avtomatik 100% tiklaydi"""
    try:
        import database.requests as db_req
        count = await db_req.get_total_movies_count()
        if count > 0:
            return
            
        logging.info("Bazada kinolar 0 ta. Avtomatik zaxiradan tiklash boshlandi...")
        if os.path.exists("movies_backup.json"):
            with open("movies_backup.json", "r", encoding="utf-8") as f:
                content = f.read()
                restored = await db_req.import_movies_from_json(content)
                if restored > 0:
                    logging.info(f"Zaxiradan {restored} ta kino avtomatik tiklandi! 🚀")
    except Exception as e:
        logging.warning(f"Zaxiradan tiklashda ogohlantirish: {e}")

async def start_health_web_server():
    """Render.com Free Web Service uchun port va ping tinglovchi ($0/month BEPUL tarif uchun)"""
    try:
        from aiohttp import web
        import os
        port = os.getenv("PORT")
        if port:
            app = web.Application()
            async def health_check(request):
                return web.Response(text="Kino Bot is running!")
            app.router.add_get("/", health_check)
            app.router.add_get("/health", health_check)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", int(port))
            await site.start()
            logging.info(f"Render Free Web Server {port}-portda ishga tushdi! 🚀")
    except Exception as e:
        logging.warning(f"Web serverni ishga tushirishda ogohlantirish: {e}")

async def keep_alive_self_ping():
    """Render Free Web Service 15 daqiqada uyquga ketmasligi uchun har 2 daqiqada uzluksiz ping yuborish"""
    await asyncio.sleep(10)
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://uzkinobaza-bot.onrender.com/health")
    root_url = "https://uzkinobaza-bot.onrender.com/"
    local_port = os.getenv("PORT")
    
    import aiohttp
    from aiohttp import ClientTimeout
    
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(render_url, timeout=ClientTimeout(total=10)) as resp:
                    logging.info(f"Keep-Alive ping /health: {resp.status}")
                async with session.get(root_url, timeout=ClientTimeout(total=10)) as resp:
                    logging.info(f"Keep-Alive ping /: {resp.status}")
        except Exception as e:
            if local_port:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://127.0.0.1:{local_port}/health", timeout=ClientTimeout(total=5)) as resp:
                            logging.info(f"Local Keep-Alive ping: {resp.status}")
                except Exception:
                    pass
        await asyncio.sleep(120)

async def main():
    # Database yaratish va sozlash
    await init_db()
    
    # Web serverni Render Free uchun ishga tushirish
    await start_health_web_server()
    
    # Bot obyektini yaratish with proxy support
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiohttp_socks import ProxyConnector
    
    if config.PROXY_URL:
        logging.info(f"Proxy ishlatilmoqda: {config.PROXY_URL}")
        try:
            proxy_connector = ProxyConnector.from_url(config.PROXY_URL)
            session = AiohttpSession(connector=proxy_connector)
            bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
                session=session
            )
        except Exception as e:
            logging.error(f"Proxy ulanish xatosi: {e}")
            logging.info("Proxysiz urinish...")
            bot = Bot(
                token=config.BOT_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
    else:
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
    
    # Dispatcher yaratish
    dp = Dispatcher()
    
    # Start up hookni ulash
    dp.startup.register(on_startup)
    
    # Middleware'larni ulash (Faqat xabarlar uchun obunani tekshirish)
    dp.message.outer_middleware(StateCancelMiddleware())
    dp.message.outer_middleware(AntiFloodMiddleware())
    dp.message.middleware(CheckSubMiddleware())
    
    # Routerlarni ulash
    # Eslatma: admin router user routerdan oldin qo'shilishi kerak,
    # chunki admin komandalari birinchi tekshiriladi.
    dp.include_router(admin.router)
    dp.include_router(join_request.router)
    dp.include_router(user.router)
    dp.include_router(payment.router)
    
    # Delete webhook and start polling cleanly
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    await asyncio.sleep(2)
    logging.info("Bot polling ishga tushmoqda...")
    while True:
        try:
            await dp.start_polling(bot, handle_signals=False)
            break
        except Exception as e:
            if "Conflict" in str(e) or "terminated by other getUpdates" in str(e) or "TelegramConflictError" in type(e).__name__:
                logging.warning(f"TelegramConflictError (eski jarayon to'xtamoqda). 5 soniyada qayta ulanadi: {e}")
                await asyncio.sleep(5)
            else:
                logging.error(f"Polling xatosi: {e}")
                await asyncio.sleep(5)
    
    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi!")
