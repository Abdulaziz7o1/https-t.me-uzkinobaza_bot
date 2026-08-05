import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultCachedVideo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
from database import requests as db_req
from keyboards.reply import get_admin_menu, get_user_menu, get_moderator_menu
from keyboards.inline import get_subscription_keyboard, get_movie_action_keyboard, get_rating_keyboard, get_comments_keyboard

router = Router()

USER_MENU_BUTTONS = [
    "🔍 Kino qidirish", "Kino qidirish 🔍", "Kino qidirish",
    "Tanlanganlar ⭐️", "Saqlanganlar ⭐️", "⭐️ Saqlanganlar", "Tanlanganlar", "Saqlanganlar",
    "Tasodifiy Kino 🎲", "Tasodifiy Kino",
    "Kino so'rash 🎬", "Kino so'rash 📥", "Kino so'rash",
    "💎 Mening Ballarim", "Mening Ballarim 💎", "Mening Ballarim", "Ballar 💎",
    "🏆 Reytinglar", "Reytinglar 🏆", "Reytinglar",
    "👥 Referal", "Referal 👥", "Takliflar (Referal) 👥", "Referal",
    "🗳️ Kino so'rovlari", "Kino so'rovlari 📥", "Kino so'rovlari 🗳️", "Kino so'rovlari",
    "⚙️ Sozlamalar", "Sozlamalar ⚙️", "Sozlamalar",
    "🎁 Kunlik Bonus", "Kunlik Bonus 🎁", "Kunlik Bonus",
    "👑 Profilim", "Profilim 👑", "Profilim",
    "🔝 TOP Kinolar", "TOP Kinolar 🔝", "TOP Kinolar",
    "🎂 Tug'ilgan Kun", "Tug'ilgan Kun 🎂", "Tug'ilgan Kun",
    "🆘 Yordam / Murojaat", "Yordam / Murojaat 🆘", "Yordam / Murojaat", "Yordam"
]

class UserStates(StatesGroup):
    waiting_for_request_name = State()
    waiting_for_comment = State()
    waiting_for_movie_search = State()
    waiting_for_movie_request = State()
    waiting_for_support_ticket = State()
    waiting_for_birthday = State()
    waiting_for_payment_receipt = State()
    waiting_for_promo_code_input = State()

# ─── START ────────────────────────────────────────────────────────────────────
async def execute_start_logic(message: Message, state: FSMContext):
    """Start logikasini bajarish (umumiy funksiya)"""
    # HAMMA STATE'LARNI TO'LALIK TOZALASH
    await state.clear()

    user_id = message.from_user.id
    user = message.from_user
    name_to_show = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

    # Referal kodini tekshirish
    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1:
        start_arg = args[1]
        if start_arg.isdigit():
            referred_id = int(start_arg)

            # Referal hisoblash faqat boshqa user uchun (o'z-o'ziga emas)
            if referred_id != user_id:
                existing_user = await db_req.get_user(user_id)
                if not existing_user:
                    referred_by = referred_id

    await db_req.add_user(user_id, user.username or "", user.full_name, referred_by)

    db_admins = await db_req.get_all_admins()
    if user_id in config.ADMINS:
        await message.answer(
            f"👋 <b>Assalomu alaykum, Bosh Admin {name_to_show}!</b>\n\n"
            f"🛠 <b>Bot boshqaruv paneliga xush kelibsiz.</b>\n"
            f"Quyidagi menyudan foydalanib botni boshqarishingiz mumkin:",
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )
    elif user_id in db_admins:
        await message.answer(
            f"👋 <b>Assalomu alaykum, Moderator {name_to_show}!</b>\n\n"
            f"🛠 <b>Moderator paneliga xush kelibsiz.</b>\n"
            f"Quyidagi menyudan foydalanib botni boshqarishingiz mumkin:",
            parse_mode="HTML",
            reply_markup=get_moderator_menu()
        )
    else:
        await message.answer(
            f"👋 <b>Assalomu alaykum, {name_to_show}!</b>\n\n"
            f"🍿 <b>Kino botiga xush kelibsiz!</b>\n\n"
            f"🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n"
            f"⚡ Quyidagi menyudan foydalaning:",
            parse_mode="HTML",
            reply_markup=get_user_menu()
        )

@router.message(CommandStart(), StateFilter("*"))
@router.message(Command("start"), StateFilter("*"))
async def cmd_start(message: Message, state: FSMContext):
    """Start komandasi - umumiy start logikasini chaqirish"""
    await execute_start_logic(message, state)

    # ── Deep link: /start movie_42 ──────────────────────────────────────────
    # Do'stdan ulashilgan havola orqali kelgan bo'lsa, kinoni darhol yuboramiz
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("movie_"):
        raw_id = args[1][len("movie_"):]
        if raw_id.isdigit():
            movie_id = int(raw_id)
            user_id = message.from_user.id

            is_premium = await db_req.is_premium_user(user_id)
            if not is_premium:
                daily_count = await db_req.get_daily_movie_count(user_id)
                bonus_limit = await db_req.get_daily_bonus_limit(user_id)
                max_allowed = 3 + bonus_limit
                if daily_count >= max_allowed:
                    await message.answer(
                        f"⚠️ <b>Kunlik limit tugadi!</b>\n\n"
                        f"Siz bugun {max_allowed} ta kino ko'rishingiz mumkin edi.\n"
                        f"Premium obuna olish uchun /premium buyrug'ini yozing.",
                        parse_mode="HTML"
                    )
                    return

            movie = await db_req.get_movie(movie_id)
            if movie:
                if not is_premium:
                    await db_req.increment_daily_movie_count(user_id)

                await db_req.add_to_watch_history(user_id, movie_id)

                file_id, caption = movie
                avg_rating, votes = await db_req.get_movie_rating(movie_id)
                is_fav = await db_req.is_favorite(user_id, movie_id)
                rating_stars = "⭐" * round(avg_rating) if avg_rating else ""
                cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿"
                if avg_rating > 0:
                    cap += f"\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}"
                cap += f"\n\n🤖 {config.BOT_USERNAME}"
                await message.answer_video(
                    video=file_id,
                    caption=cap,
                    parse_mode="HTML",
                    protect_content=True,
                    reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating)
                )
            else:
                await message.answer(f"❌ <b>{movie_id}</b> kodli kino topilmadi.", parse_mode="HTML")


@router.message(F.text == "🚀 Boshlash")
async def btn_start(message: Message, state: FSMContext):
    """Boshlash tugmasi - start logikasini chaqirish"""
    # State tozalash
    await state.clear()

    user_id = message.from_user.id
    user = message.from_user
    name_to_show = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'

    # Userni bazaga qo'shish
    await db_req.add_user(user_id, user.username, user.first_name)

    # Obuna tekshirish
    db_admins = await db_req.get_all_admins()
    if user_id in config.ADMINS or user_id in db_admins:
        await message.answer(
            f"👋 Assalomu alaykum, {name_to_show}!\n\n"
            f"🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n"
            f"⚡ Quyidagi menyudan foydalaning:",
            parse_mode="HTML",
            reply_markup=get_user_menu()
        )
        return

    db_channels = await db_req.get_sponsor_channels()
    all_channels = list(config.CHANNELS) + [c[1] for c in db_channels]

    if all_channels:
        channel_buttons = []
        for channel in all_channels:
            try:
                chat = await message.bot.get_chat(channel)
                channel_buttons.append([InlineKeyboardButton(text=chat.title, url=f"https://t.me/{channel}")])
            except Exception:
                channel_buttons.append([InlineKeyboardButton(text=channel, url=f"https://t.me/{channel}")])

        channel_buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])

        await message.answer(
            f"👋 Assalomu alaykum, {name_to_show}!\n\n"
            f"🎬 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=channel_buttons)
        )
    else:
        await message.answer(
            f"👋 Assalomu alaykum, {name_to_show}!\n\n"
            f"🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n"
            f"⚡ Quyidagi menyudan foydalaning:",
            parse_mode="HTML",
            reply_markup=get_user_menu()
        )

# ─── OBUNA TEKSHIRISH (Callback) ───────────────────────────────────────────────
@router.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot = callback.bot

    db_admins = await db_req.get_all_admins()
    if user_id in config.ADMINS or user_id in db_admins:
        await callback.message.edit_text("Siz adminsiz! Kino kodini yuborishingiz mumkin.")
        await callback.answer()
        return

    db_channels = await db_req.get_sponsor_channels()
    all_channels = list(config.CHANNELS) + [c[1] for c in db_channels]
    not_subscribed = []

    for channel in all_channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"Kanal tekshirishda xato ({channel}): {e}")

    if not_subscribed:
        await callback.answer("Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        return

    # Referal mukofotini tekshirish va berish (bot argument birinchi keladi)
    await db_req.check_and_reward_referral(callback.bot, user_id)

    await callback.message.edit_text(
        "✅ Rahmat! Barcha kanallarga a'zo bo'ldingiz.\n\n"
        "Endi kino kodini yuborishingiz mumkin.",
    )
    await callback.answer("Muvaffaqiyatli! ✅", show_alert=True)


# ─── KINO KODINI QIDIRISH ─────────────────────────────────────────────────────
@router.message(StateFilter(None), F.text.regexp(r"^/?\d+$"))
async def search_movie_by_code(message: Message):
    user_id = message.from_user.id
    movie_id = int(message.text.lstrip('/'))
    movie = await db_req.get_movie(movie_id)

    # Admin, Moderator va Premium foydalanuvchilar uchun kutish va limiti yo'q (0 second)
    is_premium = await db_req.is_premium_user(user_id)
    is_admin_or_mod = (user_id in config.ADMINS or user_id in await db_req.get_all_admins())
    skip_wait = is_premium or is_admin_or_mod

    if not skip_wait:
        daily_count = await db_req.get_daily_movie_count(user_id)
        bonus_limit = await db_req.get_daily_bonus_limit(user_id)
        max_allowed = 3 + bonus_limit
        if daily_count >= max_allowed:
            await message.answer(
                f"⚠️ <b>Kunlik limit tugadi!</b>\n\n"
                f"Siz bugun {max_allowed} ta kino ko'rishingiz mumkin edi.\n"
                f"Premium obuna olish uchun /premium buyrug'ini yozing.",
                parse_mode="HTML"
            )
            return

    if movie:
        # Kunlik limitni oshirish va 3 soniyalik timer (faqat bepul foydalanuvchilar uchun)
        if not skip_wait:
            await db_req.increment_daily_movie_count(user_id)
            cd_msg = await message.answer(
                "🎬 <b>Kino yuklanmoqda... (3 soniya)</b> ⏳\n\n"
                "💎 <i>Kutishni istamaysizmi? /premium olib, kutish vaqtini <b>0 soniya</b> qiling!</i> 🚀",
                parse_mode="HTML"
            )
            import asyncio
            await asyncio.sleep(3)
            try:
                await cd_msg.delete()
            except Exception:
                pass

        file_id, caption = movie
        avg_rating, votes = await db_req.get_movie_rating(movie_id)
        is_fav = await db_req.is_favorite(message.from_user.id, movie_id)
        likes, dislikes, fires = await db_req.get_movie_reactions(movie_id)

        rating_stars = "⭐" * round(avg_rating) if avg_rating else ""
        cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿"

        if avg_rating > 0:
            cap += f"\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}"
        cap += f"\n\n🤖 {config.BOT_USERNAME}"

        await message.answer_video(
            video=file_id,
            caption=cap,
            parse_mode="HTML",
            protect_content=True,
            reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating, likes, dislikes, fires)
        )
    else:
        await message.answer(
            f"❌ <b>Kino topilmadi!</b>\n\n"
            f"Kino kodi <code>{movie_id}</code> bo'yicha kino mavjud emas.\n"
            f"Iltimos, to'g'ri kino kodini kiriting yoki kino qidirishdan foydalaning.",
            parse_mode="HTML"
        )
        return

# ─── KINO REAKSIYALARI CALLBACK HANDLER (👍 👎 🔥) ────────────────────────────
@router.callback_query(F.data.startswith("react_"))
async def movie_reaction_cb(callback: CallbackQuery):
    parts = callback.data.split("_")
    movie_id = int(parts[1])
    react_type = parts[2]
    user_id = callback.from_user.id
    
    likes, dislikes, fires = await db_req.add_movie_reaction(movie_id, user_id, react_type)
    avg_rating, votes = await db_req.get_movie_rating(movie_id)
    is_fav = await db_req.is_favorite(user_id, movie_id)
    
    kb = get_movie_action_keyboard(movie_id, is_fav, avg_rating, likes, dislikes, fires)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
        
    await callback.answer(f"Reaksiyangiz saqlandi! {react_type.upper()} 👍", show_alert=False)

# ─── KINO BO'YICHA SHIKOYAT (FAYLDA NUQSON BOR ⚠️) ─────────────────────────────
@router.callback_query(F.data.startswith("report_movie_"))
async def report_movie_cb(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = callback.from_user
    
    await db_req.add_movie_report(movie_id, user_id)
    
    uname = f"@{user.username}" if user.username else user.full_name or str(user_id)
    alert_admin_msg = (
        f"⚠️ <b>KINO FAYLIDA NUQSON BOR SHIKOYATI!</b>\n\n"
        f"🎬 <b>Kino ID:</b> <code>{movie_id}</code>\n"
        f"👤 <b>Shikoyat qilgan:</b> {uname} (ID: <code>{user_id}</code>)\n"
        f"📌 <i>Ushbu kinoda ovoz yoki rasm nuqsoni borligi haqida xabar berildi.</i>"
    )
    
    for admin_id in config.ADMINS:
        try:
            await callback.bot.send_message(admin_id, alert_admin_msg, parse_mode="HTML")
        except Exception:
            pass
            
    await callback.answer("Shikoyatingiz adminga yetkazildi! Rahmat! 🙏", show_alert=True)

# ─── KINO NOMI BO'YICHA QIDIRISH ───────────────────────────────────────────────
@router.message(Command("search"))
@router.message(F.text.in_(["🔍 Kino qidirish", "Kino qidirish 🔍", "Kino qidirish"]))
async def start_movie_search(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_for_movie_search)
    await message.answer(
        "🔍 <b>Kino qidirish:</b>\n\n"
        "Qidirish uchun kino nomini yuboring:",
        parse_mode="HTML"
    )

@router.message(UserStates.waiting_for_movie_search, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def search_movie_by_name(message: Message, state: FSMContext):
    query = message.text.strip()
    await state.clear()

    if len(query) < 2:
        await message.answer("❌ Iltimos, kamida 2 ta harf kiriting!")
        return

    movies = await db_req.search_movies_by_name(query, limit=10)

    if movies:
        response = f"🔍 <b>Qidirish natijalari: \"{query}\"</b>\n\n"
        for movie_id, caption in movies:
            movie_name = caption.split('\n')[0] if caption else "Nomsiz"
            response += f"🎬 /{movie_id} — {movie_name}\n"

        await message.answer(response, parse_mode="HTML")
    else:
        await message.answer(f"❌ \"{query}\" bo'yicha kino topilmadi.", parse_mode="HTML")


# ─── PREMIUM OBUNA ─────────────────────────────────────────────────────────────
@router.message(Command("premium"))
@router.message(F.text == "/premium")
@router.message(F.text == "💎 Premium")
async def premium_info(message: Message):
    user_id = message.from_user.id
    is_premium = await db_req.is_premium_user(user_id)

    if is_premium:
        import math
        from datetime import datetime
        subscription = await db_req.get_premium_subscription(user_id)

        if subscription:
            # premium_subscriptions jadvalidan
            start_raw = subscription[1]
            end_raw   = subscription[2]
            plan      = subscription[3] or "Premium"

            try:
                start_dt = datetime.fromisoformat(start_raw.replace(" ", "T"))
                end_dt   = datetime.fromisoformat(end_raw.replace(" ", "T"))
                start_str = start_dt.strftime("%d.%m.%Y")
                end_str   = end_dt.strftime("%d.%m.%Y")
                
                diff_sec = (end_dt - datetime.now()).total_seconds()
                if diff_sec <= 0:
                    days_left_str = "0 kun"
                elif diff_sec < 86400:
                    hours_left = max(1, int(diff_sec // 3600))
                    days_left_str = f"{hours_left} soat"
                else:
                    days_cnt = math.ceil(diff_sec / 86400)
                    days_left_str = f"{days_cnt} kun"
            except Exception:
                start_str = start_raw[:10] if start_raw else "—"
                end_str   = end_raw[:10]   if end_raw   else "—"
                days_left_str = "?"
        else:
            # fallback: users.premium_until dan to'g'ridan-to'g'ri olish
            end_raw   = await db_req.get_user_premium_until(user_id)
            plan      = "Premium"
            start_str = "—"
            if end_raw:
                try:
                    end_dt  = datetime.fromisoformat(end_raw.replace(" ", "T"))
                    end_str = end_dt.strftime("%d.%m.%Y")
                    diff_sec = (end_dt - datetime.now()).total_seconds()
                    if diff_sec <= 0:
                        days_left_str = "0 kun"
                    elif diff_sec < 86400:
                        hours_left = max(1, int(diff_sec // 3600))
                        days_left_str = f"{hours_left} soat"
                    else:
                        days_cnt = math.ceil(diff_sec / 86400)
                        days_left_str = f"{days_cnt} kun"
                except Exception:
                    end_str   = end_raw[:10]
                    days_left_str = "?"
            else:
                end_str   = "Noma'lum"
                days_left_str = "?"


        await message.answer(
            f"👑 <b>Premium Obuna — Faol</b> ✅\n\n"
            f"📋 <b>Plan:</b> {plan}\n"
            f"📅 <b>Boshlangan:</b> {start_str}\n"
            f"⏳ <b>Tugaydi:</b> {end_str}\n"
            f"🕐 <b>Qolgan muddat:</b> {days_left_str}\n\n"
            f"🎁 <b>Premium imtiyozlari:</b>\n"
            f"• Kunlik limit yo'q\n"
            f"• Cheklovsiz kino ko'rish\n"
            f"• Prioritet qo'llab-quvvatlash\n\n"
            f"<i>Rahmat! Siz bizning Premium a'zomiz! 🙏</i>",
            parse_mode="HTML"
        )

    else:
        discount_pct = await db_req.get_user_active_discount(user_id)
        p_1m_base = await db_req.get_premium_price_1m()
        p_3m_base = await db_req.get_premium_price_3m()

        if discount_pct > 0:
            p_1m = int(p_1m_base * (100 - discount_pct) / 100)
            p_3m = int(p_3m_base * (100 - discount_pct) / 100)
            
            discount_hdr = f" 🔥 (<b>{discount_pct}% SKIDKA QO'LLANILDI!</b>)"
            txt_1m = f"1️⃣ <b>1 oylik:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>{p_1m:,} UZS</b>"
            txt_3m = f"2️⃣ <b>3 oylik:</b> <s>{p_3m_base:,} UZS</s> ➔ <b>{p_3m:,} UZS</b>"
            
            btn_1m = f"1️⃣ 1 oylik - {p_1m:,} UZS"
            btn_3m = f"2️⃣ 3 oylik - {p_3m:,} UZS"
        else:
            discount_hdr = ""
            txt_1m = f"1️⃣ <b>1 oylik - {p_1m_base:,} UZS</b>"
            txt_3m = f"2️⃣ <b>3 oylik - {p_3m_base:,} UZS</b>"
            
            btn_1m = f"1️⃣ 1 oylik - {p_1m_base:,} UZS"
            btn_3m = f"2️⃣ 3 oylik - {p_3m_base:,} UZS"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_1m, callback_data="premium_monthly"),
                InlineKeyboardButton(text=btn_3m, callback_data="premium_quarterly")
            ],
            [
                InlineKeyboardButton(text="🏷️ Promo kod kiritish", callback_data="user_enter_promo"),
                InlineKeyboardButton(text="📞 Manual to'lov", callback_data="premium_manual")
            ]
        ])

        await message.answer(
            f"💎 <b>Premium obuna:{discount_hdr}</b>\n\n"
            f"📋 <b>Obuna rejalari:</b>\n\n"
            f"{txt_1m}\n"
            f"{txt_3m}\n\n"
            f"🎁 <b>Premium imtiyozlari:</b>\n"
            f"• Kunlik limit yo'q\n"
            f"• Cheklovsiz kino ko'rish\n"
            f"• Prioritet qo'llab-quvvatlash\n\n"
            f"👇 <b>Plan tanlang yoki Promo kod kiriting:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

@router.callback_query(F.data == "user_enter_promo")
async def user_enter_promo_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_promo_code_input)
    await callback.message.answer(
        "🏷️ <b>Promo kodingizni kiriting:</b>\n\n"
        "<i>Promo kod orqali bepul Premium, ballar yoki to'lov uchun skidka olishingiz mumkin!</i>",
        parse_mode="HTML"
    )
    await callback.answer()

async def _notify_admin_promo_auto_deleted(bot, code_name: str, used_c: int, max_u: int):
    """Admin(lar)ga promo kod limiti to'lib avtomatik o'chirilgani haqida rasmiy xabarnoma yuborish"""
    import config
    txt = (
        f"🏛️ <b>RASMIY BILDIRISHNOMA: PROMO KOD LIMITI TUGADI</b>\n\n"
        f"📋 <b>Tafsilotlar:</b>\n"
        f"🔹 <b>Promo kod:</b> <code>{code_name}</code>\n"
        f"📊 <b>Ishlatilganlik holati:</b> {used_c}/{max_u} marta (100% to'ldi)\n"
        f"⚙️ <b>Bajarilgan chora:</b> Tizim tomonidan bazadan avtomatik va to'liq o'chirildi 🗑️\n\n"
        f"ℹ️ <i>Bot tizimi hamda xavfsizlik qoidalariga muvofiq, limiti to'liq bajarilgan promo kodlar qayta ishlatilmasligi uchun darhol tozalanadi.</i>"
    )
    for admin_id in config.ADMINS:
        try:
            await bot.send_message(admin_id, txt, parse_mode="HTML")
        except Exception:
            pass

@router.message(Command("promo"))
async def user_promo_cmd(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        code = args[1].strip()
        user_id = message.from_user.id
        success, msg, auto_del, disc_pct = await db_req.use_promo_code(user_id, code)
        if success:
            if auto_del:
                await _notify_admin_promo_auto_deleted(message.bot, auto_del["code"], auto_del["used"], auto_del["max"])
            if disc_pct == 100:
                # 100% skidka — 1 oy premium bepul beramiz
                await db_req.set_user_premium(user_id, days=30)
                await db_req.consume_user_discount(user_id)
                user_info = message.from_user
                uname = f"@{user_info.username}" if user_info.username else user_info.full_name
                p_1m_base = await db_req.get_premium_price_1m()
                await message.answer(
                    f"🎉 <b>TABRIKLAYMIZ!</b>\n\n"
                    f"🏷️ Siz kiritgan promo kod orqali sizga\n"
                    f"<b>1 oylik 👑 Premium obuna — 0 UZS</b> ga\n"
                    f"muvaffaqiyatli taqdim etildi!\n\n"
                    f"✅ <b>Obuna holati:</b> Faol (30 kun)\n"
                    f"💳 <b>To'lov summasi:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>0 UZS</b>\n\n"
                    f"📌 <i>Premium obunangiz tafsilotlarini ko'rish uchun /premium buyrug'ini yuboring.</i>\n"
                    f"🙏 <i>Botimizdan foydalanganingiz uchun rahmat!</i>",
                    parse_mode="HTML"
                )
                await _notify_admin_promo_100(message.bot, user_id, uname, code)
                return
            elif disc_pct > 0:
                p_1m_base = await db_req.get_premium_price_1m()
                p_3m_base = await db_req.get_premium_price_3m()
                p_1m = int(p_1m_base * (100 - disc_pct) / 100)
                p_3m = int(p_3m_base * (100 - disc_pct) / 100)
                msg = (
                    f"✅ <b>PROMO KOD MUVAFFAQIYATLI ISHLATILDI!</b> 🎉\n\n"
                    f"🏷️ <b>Sizga {disc_pct}% SKIDKA taqdim etildi!</b>\n\n"
                    f"💰 <b>SKIDKADAGI YANGI NARXLARINGIZ:</b>\n"
                    f"1️⃣ <b>1 oylik Premium:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>{p_1m:,} UZS</b>\n"
                    f"2️⃣ <b>3 oylik Premium:</b> <s>{p_3m_base:,} UZS</s> ➔ <b>{p_3m:,} UZS</b>\n\n"
                    f"👉 To'lovni amalga oshirish va obunani faollashtirish uchun /premium buyrug'ini yuboring!"
                )
            else:
                msg = (
                    f"✅ <b>PROMO KOD MUVAFFAQIYATLI ISHLATILDI!</b> 🎉\n\n"
                    f"{msg}\n\n"
                    f"👉 Obuna va ballaringizni tekshirish uchun /premium buyrug'ini yuboring!"
                )
        await message.answer(msg, parse_mode="HTML")
    else:
        await state.set_state(UserStates.waiting_for_promo_code_input)
        await message.answer("🏷️ <b>Promo kodingizni kiriting:</b>", parse_mode="HTML")

async def _notify_admin_promo_100(bot, user_id: int, uname: str, code: str):
    """Admin(lar)ga 100% promo kod ishlatilgani haqida xabarnoma yuborish"""
    import config
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚠️ Ogohlantirish", callback_data=f"prem_warn_{user_id}"),
            InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"prem_ban_{user_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Premiumni bekor qilish", callback_data=f"prem_remove_{user_id}")
        ]
    ])
    text = (
        f"🔔 <b>100% PROMO KOD ISHLATILDI!</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {uname} (<code>{user_id}</code>)\n"
        f"🏷️ <b>Promo kod:</b> <code>{code}</code>\n"
        f"🎁 <b>Berilgan imtiyoz:</b> 1 oylik Premium — 0 UZS\n\n"
        f"⚙️ Agar bu shubhali faoliyat bo'lsa, quyidagi tugmalar orqali chora ko'ring:"
    )
    for admin_id in config.ADMINS:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass

@router.message(UserStates.waiting_for_promo_code_input, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def user_promo_input_exec(message: Message, state: FSMContext):
    code = message.text.strip()
    await state.clear()
    user_id = message.from_user.id
    success, msg, auto_del, disc_pct = await db_req.use_promo_code(user_id, code)
    
    if success:
        if auto_del:
            await _notify_admin_promo_auto_deleted(message.bot, auto_del["code"], auto_del["used"], auto_del["max"])

        # ── 100% skidka: to'lovsiz 1 oy premium ──────────────────────────────
        if disc_pct == 100:
            await db_req.set_user_premium(user_id, days=30)
            await db_req.consume_user_discount(user_id)
            user_info = message.from_user
            uname = f"@{user_info.username}" if user_info.username else user_info.full_name
            p_1m_base = await db_req.get_premium_price_1m()
            await message.answer(
                f"🎉 <b>TABRIKLAYMIZ!</b>\n\n"
                f"🏷️ Siz kiritgan promo kod orqali sizga\n"
                f"<b>1 oylik 👑 Premium obuna — 0 UZS</b> ga\n"
                f"muvaffaqiyatli taqdim etildi!\n\n"
                f"✅ <b>Obuna holati:</b> Faol (30 kun)\n"
                f"💳 <b>To'lov summasi:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>0 UZS</b>\n\n"
                f"📌 <i>Premium obunangiz tafsilotlarini ko'rish uchun /premium buyrug'ini yuboring.</i>\n"
                f"🙏 <i>Botimizdan foydalanganingiz uchun rahmat!</i>",
                parse_mode="HTML"
            )
            await _notify_admin_promo_100(message.bot, user_id, uname, code)
            return

        # ── Oddiy skidka ──────────────────────────────────────────────────────
        if disc_pct > 0:
            p_1m_base = await db_req.get_premium_price_1m()
            p_3m_base = await db_req.get_premium_price_3m()
            p_1m = int(p_1m_base * (100 - disc_pct) / 100)
            p_3m = int(p_3m_base * (100 - disc_pct) / 100)
            
            detail_msg = (
                f"✅ <b>PROMO KOD QABUL QILINDI!</b> 🎉\n\n"
                f"🏷️ <b>Sizga to'lov uchun {disc_pct}% SKIDKA taqdim etildi!</b>\n\n"
                f"💰 <b>SKIDKADAGI YANGI NARXLARINGIZ:</b>\n"
                f"1️⃣ <b>1 oylik Premium:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>{p_1m:,} UZS</b>\n"
                f"2️⃣ <b>3 oylik Premium:</b> <s>{p_3m_base:,} UZS</s> ➔ <b>{p_3m:,} UZS</b>\n\n"
                f"📌 <i>Istalgan vaqtda qayta ko'rish uchun /premium buyrug'idan foydalanishingiz mumkin!</i>\n\n"
                f"👇 To'lov qilish uchun quyidagi obuna planlaridan birini tanlang:"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"1️⃣ 1 oylik - {p_1m:,} UZS", callback_data="premium_monthly"),
                    InlineKeyboardButton(text=f"2️⃣ 3 oylik - {p_3m:,} UZS", callback_data="premium_quarterly")
                ],
                [
                    InlineKeyboardButton(text="📞 Manual to'lov", callback_data="premium_manual")
                ]
            ])
            await message.answer(detail_msg, parse_mode="HTML", reply_markup=kb)
            return

        # ── Skidka emas (ball yoki premium) ───────────────────────────────────
        conf_msg = (
            f"✅ <b>PROMO KOD MUVAFFAQIYATLI ISHLATILDI!</b> 🎉\n\n"
            f"{msg}\n\n"
            f"📌 <i>Imtiyoz va obuna ma'lumotlarini ko'rish uchun /premium buyrug'ini yuboring.</i>"
        )
        await message.answer(conf_msg, parse_mode="HTML")
    else:
        await message.answer(f"{msg}\n\n<i>Qayta urinib ko'rish uchun /premium yoki promo kodni qayta kiriting.</i>", parse_mode="HTML")

@router.callback_query(F.data.startswith("premium_"))
async def process_premium_payment_cb(callback: CallbackQuery, state: FSMContext):
    action = callback.data # "premium_monthly", "premium_quarterly", "premium_manual"
    user_id = callback.from_user.id
    discount_pct = await db_req.get_user_active_discount(user_id)
    
    card_text = await db_req.get_admin_card_number()
    card_display = db_req.format_user_card_display(card_text)
    
    if action == "premium_monthly":
        plan_name = "1 oylik Premium"
        base_price = await db_req.get_premium_price_1m()
        days = 30
        plan_label = "1 oylik"
    elif action == "premium_quarterly":
        plan_name = "3 oylik Premium"
        base_price = await db_req.get_premium_price_3m()
        days = 90
        plan_label = "3 oylik"
    else:
        plan_name = "Premium Obuna"
        base_price = await db_req.get_premium_price_1m()
        days = 30
        plan_label = "1 oylik"

    if discount_pct > 0 and action in ["premium_monthly", "premium_quarterly"]:
        final_price = int(base_price * (100 - discount_pct) / 100)
        amount = f"{final_price:,} UZS ({discount_pct}% SKIDKA QO'LLANDI!)"
    else:
        amount = f"{base_price:,} UZS" if action != "premium_manual" else "Kelishilgan summa"

    await state.set_state(UserStates.waiting_for_payment_receipt)
    await state.update_data(payment_plan=plan_name, payment_amount=amount, payment_days=days, payment_label=plan_label)

    msg = (
        f"💳 <b>TO'LOV MA'LUMOTLARI ({plan_name}):</b>\n\n"
        f"To'lovni amalga oshirish uchun quyidagi kartaga to'lov qiling:\n\n"
        f"{card_display}\n\n"
        f"💵 <b>To'lov summasi:</b> <code>{amount}</code>\n\n"
        f"📌 <b>To'lov qilgach:</b> To'lov chekini (skrinshotini) shu yerning o'zida yuboring! To'lov tasdiqlangach Premium faollashtiriladi!"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_premium")
    ]])
    
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "back_to_premium")
async def back_to_premium_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    discount_pct = await db_req.get_user_active_discount(user_id)
    
    if discount_pct > 0:
        p_1m = int(10000 * (100 - discount_pct) / 100)
        p_3m = int(25000 * (100 - discount_pct) / 100)
        
        discount_hdr = f" 🔥 (<b>{discount_pct}% SKIDKA QO'LLANILDI!</b>)"
        txt_1m = f"1️⃣ <b>1 oylik:</b> <s>10,000 UZS</s> ➔ <b>{p_1m:,} UZS</b>"
        txt_3m = f"2️⃣ <b>3 oylik:</b> <s>25,000 UZS</s> ➔ <b>{p_3m:,} UZS</b>"
        
        btn_1m = f"1️⃣ 1 oylik - {p_1m:,} UZS"
        btn_3m = f"2️⃣ 3 oylik - {p_3m:,} UZS"
    else:
        discount_hdr = ""
        txt_1m = "1️⃣ <b>1 oylik - 10,000 UZS</b>"
        txt_3m = "2️⃣ <b>3 oylik - 25,000 UZS</b> (5,000 UZS tejang!)"
        
        btn_1m = "1️⃣ 1 oylik - 10,000 UZS"
        btn_3m = "2️⃣ 3 oylik - 25,000 UZS"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=btn_1m, callback_data="premium_monthly"),
            InlineKeyboardButton(text=btn_3m, callback_data="premium_quarterly")
        ],
        [
            InlineKeyboardButton(text="🏷️ Promo kod kiritish", callback_data="user_enter_promo"),
            InlineKeyboardButton(text="📞 Manual to'lov", callback_data="premium_manual")
        ]
    ])

    await callback.message.edit_text(
        f"💎 <b>Premium obuna:{discount_hdr}</b>\n\n"
        f"📋 <b>Obuna rejalari:</b>\n\n"
        f"{txt_1m}\n"
        f"{txt_3m}\n\n"
        f"🎁 <b>Premium imtiyozlari:</b>\n"
        f"• Kunlik limit yo'q\n"
        f"• Cheklovsiz kino ko'rish\n"
        f"• Prioritet qo'llab-quvvatlash\n\n"
        f"👇 <b>Plan tanlang yoki Promo kod kiriting:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.message(UserStates.waiting_for_payment_receipt, F.photo | F.document)
async def user_payment_receipt_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get("payment_plan", "Premium")
    amount = data.get("payment_amount", "")
    days = data.get("payment_days", 30)
    plan_label = data.get("payment_label", "1 oylik")
    
    user = message.from_user
    username_disp = f"@{user.username}" if user.username else user.full_name or str(user.id)
    
    await state.clear()
    
    # Userga bildirishnoma ("tez orada" + "tasdiqlashadi")
    await message.answer(
        "✅ <b>To'lov chekingiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        "Adminlarimiz chekni tekshirib chiqib, tez orada Premium obunangizni tasdiqlashadi. Rahmat! 🍿",
        parse_mode="HTML"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ {plan_label} Premium tasdiqlash", callback_data=f"admin_approve_prem_{user.id}_{days}")],
        [
            InlineKeyboardButton(text="❌ Xato chek", callback_data=f"admin_reject_receipt_{user.id}"),
            InlineKeyboardButton(text="⚠️ Ogohlantirish", callback_data=f"admin_warn_receipt_{user.id}")
        ],
        [InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"admin_ban_receipt_{user.id}")]
    ])
    
    # O'zbekiston vaqti (UTC+5)
    from datetime import datetime, timedelta
    uzb_now = datetime.utcnow() + timedelta(hours=5)
    formatted_time = uzb_now.strftime('%Y-%m-%d %H:%M')
    
    admin_txt = (
        f"💳 <b>YANGI TO'LOV CHEKI KELDI!</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {username_disp} (ID: <code>{user.id}</code>)\n"
        f"📋 <b>Plan:</b> {plan_name} ({amount})\n"
        f"🕒 <b>Vaqt:</b> {formatted_time}"
    )
    
    for admin_id in config.ADMINS:
        try:
            if message.photo:
                await message.bot.send_photo(admin_id, message.photo[-1].file_id, caption=admin_txt, parse_mode="HTML", reply_markup=kb)
            elif message.document:
                await message.bot.send_document(admin_id, message.document.file_id, caption=admin_txt, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass


# ─── TANLANGANLAR ──────────────────────────────────────────────────────────────
@router.message(F.text == "Tanlanganlar ⭐️")
async def show_favorites(message: Message, state: FSMContext):
    await state.clear()
    favorites = await db_req.get_favorites(message.from_user.id)
    
    if not favorites:
        await message.answer("❌ Siz hali hech qanday kino tanlanganlarga qo'shmadingiz.")
        return
    
    text = "⭐ <b>Sizning tanlangan kinolaringiz:</b>\n\n"
    for movie_id, caption in favorites:
        name = caption[:40] if caption else "(nomsiz)"
        text += f"🎬 /{movie_id} — {name}\n"
    
    text += "\nKinoni olish uchun uning kodini ustiga bosing."
    await message.answer(text)

# ─── TASODIFIY KINO ─────────────────────────────────────────────────────────
@router.message(Command("random"))
@router.message(F.text.regexp(r"(?i).*(tasodifiy kino).*"))
async def random_movie(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    # Kunlik limit tekshirish (premium bo'lmaganlar uchun)
    is_premium = await db_req.is_premium_user(user_id)
    if not is_premium:
        daily_count = await db_req.get_daily_movie_count(user_id)
        bonus_limit = await db_req.get_daily_bonus_limit(user_id)
        max_allowed = 3 + bonus_limit
        if daily_count >= max_allowed:
            await message.answer(
                f"⚠️ <b>Kunlik limit tugadi!</b>\n\n"
                f"Siz bugun {max_allowed} ta kino ko'rishingiz mumkin edi.\n"
                f"Premium obuna olish uchun /premium buyrug'ini yozing.",
                parse_mode="HTML"
            )
            return

    from database.connection import get_db
    async with get_db() as db:
        async with db.execute("SELECT id FROM movies") as cursor:
            all_ids = await cursor.fetchall()

    if not all_ids:
        await message.answer("🎬 Botda hali kinolar qo'shilmagan.")
        return

    random_id = random.choice(all_ids)[0]
    movie = await db_req.get_movie(random_id)

    if movie:
        if not is_premium:
            await db_req.increment_daily_movie_count(user_id)

        await db_req.add_to_watch_history(user_id, random_id)

        file_id, caption = movie
        avg_rating, votes = await db_req.get_movie_rating(random_id)
        is_fav = await db_req.is_favorite(user_id, random_id)

        cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{random_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿"
        if avg_rating > 0:
            cap += f"\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz)"
        cap += f"\n\n🤖 {config.BOT_USERNAME}"

        await message.answer_video(
            video=file_id,
            caption=cap,
            parse_mode="HTML",
            protect_content=True,
            reply_markup=get_movie_action_keyboard(random_id, is_fav, avg_rating)
        )
    else:
        await message.answer(f"❌ Kino topilmadi (ID: {random_id})")


# ─── REYTINGLAR (LEADERBOARD) ─────────────────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(reytinglar).*"))
async def show_user_leaderboard(message: Message, state: FSMContext):
    """Foydalanuvchilar uchun leaderboard"""
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 TOP 10 (Ballar)", callback_data="user_top_points"),
            InlineKeyboardButton(text="👥 TOP 10 (Referallar)", callback_data="user_top_referrals")
        ],
        [
            InlineKeyboardButton(text="🔥 TOP 10 (Faollik)", callback_data="user_top_activity")
        ]
    ])

    await message.answer(
        "🏆 <b>Reytinglar - Leaderboard</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "user_top_points")
async def user_top_points(callback: CallbackQuery):
    """Ballar bo'yicha TOP 10"""
    top_users = await db_req.get_top_users_by_points(10)

    text = "🏆 <b>TOP 10 Foydalanuvchilar (Ballar bo'yicha)</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, username, full_name, points, referrals_count) in enumerate(top_users, 1):
        medal = medals[i-1] if i <= 3 else f"#{i}"
        username_display = username or full_name or f"User {user_id}"
        text += f"{medal} <b>{username_display}</b>\n"
        text += f"   💰 Ball: {points:,} | 👥 Referallar: {referrals_count}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="user_top_points")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="user_leaderboard")]
    ])

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "user_top_referrals")
async def user_top_referrals(callback: CallbackQuery):
    """Referallar bo'yicha TOP 10"""
    top_users = await db_req.get_top_users_by_referrals(10)

    text = "👥 <b>TOP 10 Foydalanuvchilar (Referallar bo'yicha)</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, username, full_name, referrals_count, points) in enumerate(top_users, 1):
        medal = medals[i-1] if i <= 3 else f"#{i}"
        username_display = username or full_name or f"User {user_id}"
        text += f"{medal} <b>{username_display}</b>\n"
        text += f"   👥 Referallar: {referrals_count} | 💰 Ball: {points:,}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="user_top_referrals")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="user_leaderboard")]
    ])

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "user_top_activity")
async def user_top_activity(callback: CallbackQuery):
    """Faollik bo'yicha TOP 10"""
    top_users = await db_req.get_top_users_by_activity(10)

    text = "🔥 <b>TOP 10 Foydalanuvchilar (Faollik bo'yicha)</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, username, full_name, last_active_at, points) in enumerate(top_users, 1):
        medal = medals[i-1] if i <= 3 else f"#{i}"
        username_display = username or full_name or f"User {user_id}"
        text += f"{medal} <b>{username_display}</b>\n"
        text += f"   ⏰ Oxirgi faollik: {last_active_at}\n"
        text += f"   💰 Ball: {points:,}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="user_top_activity")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="user_leaderboard")]
    ])

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "user_leaderboard")
async def back_user_leaderboard(callback: CallbackQuery):
    """User leaderboard menyusiga qaytish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 TOP 10 (Ballar)", callback_data="user_top_points"),
            InlineKeyboardButton(text="👥 TOP 10 (Referallar)", callback_data="user_top_referrals")
        ],
        [
            InlineKeyboardButton(text="🔥 TOP 10 (Faollik)", callback_data="user_top_activity")
        ]
    ])

    try:
        await callback.message.edit_text(
            "🏆 <b>Reytinglar - Leaderboard</b>\n\n"
            "Quyidagi bo'limlardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        await callback.message.answer(
            "🏆 <b>Reytinglar - Leaderboard</b>\n\n"
            "Quyidagi bo'limlardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback.answer()


# ─── KINO SO'RASH ────────────────────────────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(kino so'rash).*"))
async def request_movie(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_for_movie_request)
    await message.answer(
        "🎬 <b>Kino so'rash:</b>\n\n"
        "Qidirayotgan kinoning nomini yuboring:",
        parse_mode="HTML"
    )


@router.message(UserStates.waiting_for_movie_request, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def process_movie_request(message: Message, state: FSMContext):
    """Foydalanuvchining kino so'rovini qayta ishlash"""
    user_id = message.from_user.id
    movie_name = message.text

    # So'rovni bazaga qo'shish
    await db_req.add_movie_request(user_id, movie_name)

    await state.clear()
    await message.answer(
        f"✅ <b>So'rov qabul qilindi!</b>\n\n"
        f"🎬 Kino: {movie_name}\n"
        f"📊 Adminlar tez orada ko'rib chiqishadi.\n\n"
        f"⏰ Kino qo'shilganda sizga xabar beramiz.",
        parse_mode="HTML"
    )


# ─── REFERAL TIZIMI ──────────────────────────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(referal).*"))
async def show_referral_stats(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    # Referal havolasini tayyorlash
    bot_clean = config.BOT_USERNAME.lstrip('@')
    ref_link = f"https://t.me/{bot_clean}?start={user_id}"
    
    # User ma'lumotlarini olish (referal sonini ko'rish uchun)
    user_db = await db_req.get_user(user_id)
    referrals_count = user_db[5] if user_db and len(user_db) > 5 else 0
    
    # Top 10 taklif qilganlarni olish
    top_referrers = await db_req.get_top_referrers()
    top_text = ""
    if top_referrers:
        top_text = "\n🏆 <b>Eng ko'p taklif qilgan TOP 10 a'zo:</b>\n"
        for idx, (uid, username, full_name, count) in enumerate(top_referrers, 1):
            name = f"@{username}" if username else full_name or str(uid)
            top_text += f"{idx}. 👤 {name} — <code>{count}</code> ta do'st\n"
            
    stats_text = (
        f"📊 <b>Sizning referal statistikangiz:</b>\n\n"
        f"👥 <b>Taklif qilingan a'zolar:</b> <code>{referrals_count}</code> ta\n"
        f"🔗 <b>Sizning taklif havolangiz:</b>\n<code>{ref_link}</code>\n"
        f"{top_text}\n"
        f"👇 <b>Do'stlaringizga ulashish uchun:</b>\n\n"
        f"🚀 Quyidagi tugmani bosing va do'stingizga yuboring!"
    )

    import urllib.parse
    share_text = "🚀 Kino bot - ko'p kino, bepul, qulay!\n\nQuyidagi havola orqali kiring:"
    share_url = f"https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Botni boshlash", url=ref_link),
            InlineKeyboardButton(text="📤 Ulashish", url=share_url)
        ]
    ])

    await message.answer(stats_text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data == "ref_my_stats")
async def show_ref_stats_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_db = await db_req.get_user(user_id)
    referrals_count = user_db[5] if user_db and len(user_db) > 5 else 0
    
    top_referrers = await db_req.get_top_referrers()
    top_text = ""
    if top_referrers:
        top_text = "\n\n🏆 TOP 10 taklif qilganlar:\n"
        for idx, (uid, username, full_name, count) in enumerate(top_referrers[:5], 1):
            name = f"@{username}" if username else full_name or str(uid)
            top_text += f"{idx}. {name} — {count} ta\n"
            
    alert_text = (
        f"📊 Sizning referal statistikangiz:\n\n"
        f"👥 Taklif qilingan a'zolar: {referrals_count} ta"
        f"{top_text}"
    )
    await callback.answer(alert_text, show_alert=True)



# Foydalanuvchi menyu tugmalari ro'yxati (state filtrlash uchun)
USER_MENU_BUTTONS = [
    " Kino qidirish", "Tanlanganlar ⭐️",
    "Tasodifiy Kino 🎲", "Kino so'rash 🎬", "💎 Mening Ballarim",
    "🏆 Reytinglar", "👥 Referal", "🗳️ Kino so'rovlari",
    "⚙️ Sozlamalar"
]

# ─── 💎 MENING BALLARIM ──────────────────────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(mening ballarim|ballarim).*"))
async def my_points(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    points = await db_req.get_points(user_id)
    leaderboard = await db_req.get_points_leaderboard(10)
    
    top_text = ""
    user_rank = None
    for idx, (uid, username, full_name, pts) in enumerate(leaderboard, 1):
        name = f"@{username}" if username else full_name or str(uid)
        top_text += f"{idx}. 👤 {name} — <code>{pts}</code> 💎\n"
        if uid == user_id:
            user_rank = idx
    
    rank_text = f"\n🏅 <b>Sizning o'rningiz:</b> {user_rank}-o'rin" if user_rank else ""
    
    text = (
        f"💎 <b>Sizning ballaringiz: <code>{points}</code> 💎</b>\n\n"
        f"📌 <b>Ball qanday yig'iladi?</b>\n"
        f"⭐ Kino baholash → +2 💎\n"
        f"💬 Izoh yozish → +3 💎\n"
        f"👥 Do'st taklif qilish → +10 💎\n"
        f"{rank_text}\n"
    )
    
    kb = None
    if points >= 150:
        text += (
            f"\n🎁 <b>MAXSUS TAKLIF (PROFFESIONAL REJIM):</b>\n"
            f"Sizda <b>{points} ball</b> bor! <b>150 ball</b> evaziga <b>👑 2 OYLIK PREMIUM VIP</b> maqomini ishga tushirishingiz mumkin!\n"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="🎁 2 Oylik Premiumni Ishlatish (150 ball)", callback_data="redeem_150pts_premium")
        kb = builder.as_markup()
        
    if top_text:
        text += f"\n🏆 <b>TOP 10 ball yig'uvchilar:</b>\n{top_text}"
    
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "redeem_150pts_premium")
async def redeem_150pts_premium_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    success, msg = await db_req.redeem_150pts_for_2m_premium(user_id)
    if success:
        await callback.message.edit_text(msg, parse_mode="HTML")
        await callback.answer("👑 2 Oylik Premium faollashtirildi! 🎉", show_alert=True)
    else:
        await callback.answer(msg, show_alert=True)

# ─── 🗳️ KINO SO'ROVLARI (CROWDSOURCED VOTES) ──────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(kino so'rovlari).*"))
async def show_movie_requests(message: Message, state: FSMContext):
    await state.clear()
    requests = await db_req.get_top_movie_requests(limit=10)
    
    if not requests:
        await message.answer(
            "🗳️ <b>Hozircha hech qanday kino so'rovi yo'q.</b>\n\n"
            "Birinchi bo'lib <b>Kino so'rash 📥</b> orqali so'rov qoldiring!",
            parse_mode="HTML"
        )
        return
    
    text = "🗳️ <b>Eng ko'p so'ralgan kinolar:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    for idx, (req_id, movie_name, votes, user_id, created_at) in enumerate(requests, 1):
        text += f"{idx}. 🎬 <b>{movie_name}</b> — <code>{votes}</code> ovoz\n"
        builder.button(
            text=f"👍 {movie_name[:20]} ({votes})",
            callback_data=f"vote_req_{req_id}"
        )
    
    builder.adjust(1)
    text += "\n<i>Kino nomiga bosing va ovoz bering! Ko'proq ovoz = tezroq qo'shiladi.</i>"
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.startswith("vote_req_"))
async def vote_movie_request_cb(callback: CallbackQuery):
    request_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    is_new_vote = await db_req.vote_movie_request(user_id, request_id)
    
    if is_new_vote:
        await callback.answer("✅ Ovozingiz qabul qilindi! +1 ovoz.", show_alert=True)
        # Tugma matnini yangilash
        try:
            requests = await db_req.get_top_movie_requests(limit=10)
            target = next((r for r in requests if r[0] == request_id), None)
            if target and callback.message.reply_markup:
                builder = InlineKeyboardBuilder()
                for req_id, movie_name, votes, uid, created_at in requests:
                    builder.button(
                        text=f"👍 {movie_name[:20]} ({votes})",
                        callback_data=f"vote_req_{req_id}"
                    )
                builder.adjust(1)
                await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
        except Exception:
            pass
    else:
        await callback.answer("❌ Siz bu kinoga allaqachon ovoz bergansiz!", show_alert=True)


# ─── ⚙️ SOZLAMALAR (PERSONAL SETTINGS) ───────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(sozlamalar).*"))
async def show_settings(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    notify_pts = await db_req.get_user_notify_points(user_id)
    
    status_icon = "✅ Yoqilgan" if notify_pts else "❌ O'chirilgan"
    toggle_text = "🔕 O'chirish" if notify_pts else "🔔 Yoqish"
    
    text = (
        "⚙️ <b>Shaxsiy Sozlamalar</b>\n\n"
        f"🔔 <b>Ball bildirishnomalari:</b> {status_icon}\n"
        "<i>(Kino baholash, izoh yozish va referal uchun olgan ballaringiz haqida xabar)</i>\n\n"
        "Sozlamani o'zgartirish uchun quyidagi tugmani bosing:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{toggle_text} — Ball bildirishnomalari", callback_data="toggle_notify_points")
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@router.callback_query(F.data == "toggle_notify_points")
async def toggle_notify_points_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    new_state = await db_req.toggle_user_notify_points(user_id)
    
    status_icon = "✅ Yoqilgan" if new_state else "❌ O'chirilgan"
    toggle_text = "🔕 O'chirish" if new_state else "🔔 Yoqish"
    
    text = (
        "⚙️ <b>Shaxsiy Sozlamalar</b>\n\n"
        f"🔔 <b>Ball bildirishnomalari:</b> {status_icon}\n"
        "<i>(Kino baholash, izoh yozish va referal uchun olgan ballaringiz haqida xabar)</i>\n\n"
        "Sozlamani o'zgartirish uchun quyidagi tugmani bosing:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{toggle_text} — Ball bildirishnomalari", callback_data="toggle_notify_points")
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    state_msg = "yoqildi ✅" if new_state else "o'chirildi ❌"
    await callback.answer(f"Ball bildirishnomalari {state_msg}", show_alert=False)

# ─── KINO TUGMALARI CALLBACKLARI ─────────────────────────────────────────────
@router.callback_query(F.data.startswith("fav_toggle_"))
async def toggle_favorite(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    is_fav = await db_req.is_favorite(user_id, movie_id)
    
    if is_fav:
        await db_req.remove_favorite(user_id, movie_id)
        await callback.answer("Tanlanganlardan olib tashlandi ❌", show_alert=False)
    else:
        await db_req.add_favorite(user_id, movie_id)
        await callback.answer("Tanlanganlarga qo'shildi ⭐", show_alert=False)
    
    # Tugmani yangilash
    avg_rating, _ = await db_req.get_movie_rating(movie_id)
    new_is_fav = not is_fav
    await callback.message.edit_reply_markup(
        reply_markup=get_movie_action_keyboard(movie_id, new_is_fav, avg_rating)
    )

@router.callback_query(F.data.startswith("rate_menu_"))
async def show_rating_menu(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    await callback.message.edit_reply_markup(
        reply_markup=get_rating_keyboard(movie_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("movie_menu_"))
async def back_to_movie_menu(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    movie = await db_req.get_movie(movie_id)
    if not movie:
        await callback.answer("Kino topilmadi ❌", show_alert=True)
        return
        
    file_id, caption = movie
    avg_rating, votes = await db_req.get_movie_rating(movie_id)
    is_fav = await db_req.is_favorite(callback.from_user.id, movie_id)
    
    rating_stars = "⭐" * round(avg_rating) if avg_rating else ""
    cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> <code>{movie_id}</code>"
    if avg_rating > 0:
        cap += f"\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}"
    cap += f"\n\n🤖 {config.BOT_USERNAME}"
    
    try:
        if callback.message.text is not None:
            await callback.message.edit_text(
                cap,
                reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_caption(
                caption=cap,
                reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating),
                parse_mode="HTML"
            )
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("rate_") & ~F.data.startswith("rate_menu_"))
async def submit_rating(callback: CallbackQuery):
    parts = callback.data.split("_")
    movie_id = int(parts[1])
    rating = int(parts[2])
    
    # Kunlik baholash limiti tekshirish (max 10 ta)
    daily_count = await db_req.get_daily_ratings_count(callback.from_user.id)
    if daily_count >= 10:
        await callback.answer("❌ Kuniga maksimal 10 ta kino baholash mumkin! Ertaga qaytib baholashingiz mumkin.", show_alert=True)
        return
    
    await db_req.add_rating(callback.from_user.id, movie_id, rating)
    # +2 ball beriladi
    await db_req.add_points(callback.from_user.id, 2)
    
    avg_rating, votes = await db_req.get_movie_rating(movie_id)
    is_fav = await db_req.is_favorite(callback.from_user.id, movie_id)
    
    stars = "⭐" * rating
    # Foydalanuvchi sozlamasiga ko'ra ball bildirishnomasi
    notify_pts = await db_req.get_user_notify_points(callback.from_user.id)
    remaining = 10 - (daily_count + 1)
    answer_text = f"Bahoyingiz qabul qilindi: {stars} (+2 💎 ball). Bugun yana {remaining} ta baholash qolgan!" if notify_pts else f"Bahoyingiz qabul qilindi: {stars}"
    await callback.answer(answer_text, show_alert=False)
    await callback.message.edit_reply_markup(
        reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating)
    )

# ─── KINO IZOHLARI (COMMENTS) ─────────────────────────────────────────────────
@router.callback_query(F.data.startswith("comments_list_"))
async def show_movie_comments(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    comments = await db_req.get_comments(movie_id)
    
    movie = await db_req.get_movie(movie_id)
    movie_name = movie[1][:40] if movie and movie[1] else f"Kino {movie_id}"
    
    text = f"💬 <b>«{movie_name}» filmi uchun izohlar:</b>\n\n"
    
    if not comments:
        text += "<i>Hozircha hech qanday izoh yo'q. Birinchi bo'lib o'z fikringizni yozib qoldiring!</i>"
    else:
        for idx, (comment_text, username, full_name, created_at) in enumerate(comments[:15], 1):
            name = f"@{username}" if username else full_name or "Foydalanuvchi"
            text += f"{idx}. <b>{name}</b>:\n└ <i>{comment_text}</i>\n\n"
            
    try:
        if callback.message.text is not None:
            await callback.message.edit_text(
                text,
                reply_markup=get_comments_keyboard(movie_id),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=get_comments_keyboard(movie_id),
                parse_mode="HTML"
            )
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("add_comment_start_"))
async def add_comment_start(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split("_")[3])
    await state.set_state(UserStates.waiting_for_comment)
    await state.update_data(comment_movie_id=movie_id)
    
    await callback.message.answer(
        "📝 <b>Ushbu kino uchun o'z fikringizni (izoh) yozib yuboring:</b>\n\n"
        "<i>Eslatma: Izoh uzunligi 3 dan 300 belgigacha bo'lishi kerak.</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(UserStates.waiting_for_comment, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def add_comment_exec(message: Message, state: FSMContext):
    comment_text = message.text.strip()
    
    if len(comment_text) < 3:
        await message.answer("⚠️ Izoh juda qisqa! Kamida 3 ta belgi bo'lishi lozim. Qayta yozing:")
        return
    if len(comment_text) > 300:
        await message.answer("⚠️ Izoh juda uzun! Maksimal 300 ta belgi bo'lishi lozim. Qayta yozing:")
        return
    
    # Nojo'ya so'zlar filtri
    if db_req.contains_profanity(comment_text):
        await message.answer("🚫 <b>Izohingizda nojo'ya so'zlar borligi aniqlandi!</b>\nIltimos, hurmatli so'zlar yozing.", parse_mode="HTML")
        # Shubhali harakatni jurnalga yozish
        await db_req.add_abuse_log(message.from_user.id, "profanity", f"Comment: {comment_text[:50]}")
        return
    
    # Reklama havolalari filtri
    import re
    url_pattern = r'https?://[^\s]+|www\.[^\s]+|t\.me/[^\s]+|@[\w_]+'
    if re.search(url_pattern, comment_text):
        await message.answer("🚫 <b>Izohlarda reklama havolalari taqiqlanadi!</b>\nIltimos, havolalarsiz izoh yozing.", parse_mode="HTML")
        # Shubhali harakatni jurnalga yozish
        await db_req.add_abuse_log(message.from_user.id, "spam_link", f"Comment: {comment_text[:50]}")
        return
    
    # Cooldown tekshirish (30 soniya)
    can_post, cooldown_msg = await db_req.can_post_comment(message.from_user.id)
    if not can_post:
        await message.answer(cooldown_msg)
        return
        
    data = await state.get_data()
    movie_id = data["comment_movie_id"]
    user = message.from_user
    
    # Birinchi izoh ekanligini tekshirish
    is_first_comment = not await db_req.has_commented_on_movie(user.id, movie_id)
    
    await db_req.add_comment(user.id, movie_id, comment_text)
    
    # Ball berish: faqat birinchi izoh uchun +3 ball
    points_added = 0
    if is_first_comment:
        added, limit_reached = await db_req.add_points(user.id, 3)
        points_added = added
        
    await state.clear()
    
    # Foydalanuvchi sozlamasiga ko'ra xabar
    mod_setting = await db_req.get_config_int("comment_moderation", 0)
    notify_pts = await db_req.get_user_notify_points(user.id)
    
    if mod_setting == 1:
        confirm_text = "🛡 <b>Rahmat! Izohingiz saqlandi va moderatorlar tasdig'idan so'ng ko'rinadi.</b>"
    elif is_first_comment and points_added > 0:
        confirm_text = f"✅ <b>Rahmat! Izohingiz saqlandi. (+{points_added} 💎 ball)</b>" if notify_pts else "✅ <b>Rahmat! Izohingiz saqlandi.</b>"
    elif is_first_comment and points_added == 0:
        confirm_text = "✅ <b>Rahmat! Izohingiz saqlandi. (Kunlik ball limit to'lgan)</b>" if notify_pts else "✅ <b>Rahmat! Izohingiz saqlandi.</b>"
    else:
        confirm_text = "✅ <b>Rahmat! Izohingiz saqlandi.</b>"
    
    await message.answer(confirm_text, parse_mode="HTML")
    
    # Bosh adminlarga yuborish
    movie = await db_req.get_movie(movie_id)
    movie_name = movie[1][:40] if movie and movie[1] else f"Kino {movie_id}"
    username_display = f"@{user.username}" if user.username else user.full_name
    
    admin_text = (
        f"💬 <b>Kino uchun yangi izoh keldi!</b>\n\n"
        f"🎬 <b>Kino:</b> {movie_name} (Kodi: <code>{movie_id}</code>)\n"
        f"👤 <b>Foydalanuvchi:</b> {username_display} (ID: <code>{user.id}</code>)\n"
        f"📝 <b>Izoh:</b>\n<i>{comment_text}</i>"
    )
    
    for admin_id in config.ADMINS:
        try:
            await message.bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except Exception:
            pass


# ─── INLINE MODE QIDIRUV ──────────────────────────────────────────────────────
@router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip()
    
    # ── Referal Promo Xabarni Ulashish ──
    if query.isdigit():
        # 12345678 shaklida kelgan querydan user_id ni ajratib olamiz
        ref_user_id = int(query)
    else:
        ref_user_id = inline_query.from_user.id
    
    bot_clean = config.BOT_USERNAME.lstrip('@')
    ref_link = f"https://t.me/{bot_clean}?start={ref_user_id}"
    
    # Promo ma'lumotlarini bazadan olish
    file_id = await db_req.get_setting("ref_promo_file_id")
    media_type = await db_req.get_setting("ref_promo_media_type")
    promo_caption = await db_req.get_setting("ref_promo_caption")
    
    # Default promo matni
    if not promo_caption:
        promo_caption = (
            "🚀 <b>Bizning bot orqali eng sara kinolarni tomosha qiling!</b>\n\n"
            "🍿 Har kuni yangi va qiziqarli filmlar!\n"
            "⚡ Botdan bepul foydalanish va qulay izlash."
        )
        
    caption = f"{promo_caption}\n\n🚀 {ref_link}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Boshlash:", url=f"https://t.me/{bot_clean}")]
    ])
    
    inline_results = []
    if file_id and media_type:
        if media_type == "video":
            inline_results.append(
                InlineQueryResultCachedVideo(
                    id="promo",
                    video_file_id=file_id,
                    title="Taklif xabarini yuborish 🚀",
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            )
        elif media_type == "photo":
            from aiogram.types import InlineQueryResultCachedPhoto
            inline_results.append(
                InlineQueryResultCachedPhoto(
                    id="promo",
                    photo_file_id=file_id,
                    title="Taklif xabarini yuborish 🚀",
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            )
        else:
            from aiogram.types import InlineQueryResultCachedDocument
            inline_results.append(
                InlineQueryResultCachedDocument(
                    id="promo",
                    document_file_id=file_id,
                    title="Taklif xabarini yuborish 🚀",
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            )
    else:
        from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
        inline_results.append(
            InlineQueryResultArticle(
                id="promo",
                title="Taklif xabarini yuborish 🚀",
                input_message_content=InputTextMessageContent(
                    message_text=caption,
                    parse_mode="HTML"
                ),
                reply_markup=keyboard,
                description="Taklif havolasini do'stlaringizga yuboring"
            )
        )
        
    await inline_query.answer(inline_results, cache_time=5, is_personal=True)
    return

    # ── Oddiy Kino Qidiruv ──
    if not query:
        # Agar so'rov bo'sh bo'lsa, eng trenddagi 10 ta kinoni ko'rsatamiz
        results = await db_req.get_trending_movies()
    else:
        results = await db_req.search_movies_by_name(query)
        
    inline_results = []
    for idx, item in enumerate(results):
        movie_id = item[0]
        caption = item[1]
        
        movie = await db_req.get_movie(movie_id)
        if not movie:
            continue
        file_id, movie_caption = movie
        
        # O'rtacha reytingni olish
        avg_rating, votes = await db_req.get_movie_rating(movie_id)
        rating_text = f" | ⭐ {avg_rating:.1f} ({votes} ta ovoz)" if avg_rating > 0 else ""
        
        # Ulashish caption matni: Kino tavsifi + Kino kodi + Bot username
        shared_caption = (
            f"{movie_caption or ''}"
            f"\n\n🎬 <b>Kino kodi:</b> <code>{movie_id}</code>\n"
            f"🤖 {config.BOT_USERNAME}"
        )
        
        inline_results.append(
            InlineQueryResultCachedVideo(
                id=str(movie_id),
                video_file_id=file_id,
                title=f"Kino kodi: {movie_id}",
                description=f"{caption[:100] if caption else 'Tavsifsiz'}{rating_text}",
                caption=shared_caption,
                parse_mode="HTML"
            )
        )
        
    await inline_query.answer(inline_results, cache_time=10, is_personal=True)


# ─── KUNLIK BONUS (+3 BALL) ───────────────────────────────────────────────────
@router.message(F.text == "🎁 Kunlik Bonus")
async def user_daily_bonus(message: Message, state: FSMContext):
    await state.clear()
    success, msg, pts = await db_req.claim_daily_bonus(message.from_user.id)
    await message.answer(msg, parse_mode="HTML")


# ─── SAQLANGAN KINOLAR (FAVORITES) ───────────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(saqlanganlar|tanlanganlar).*"))
async def user_favorites_list(message: Message, state: FSMContext):
    await state.clear()
    favs = await db_req.get_user_favorites(message.from_user.id)
    if not favs:
        await message.answer(
            "⭐️ <b>Sizda hali saqlangan kinolar yo'q.</b>\n\n"
            "Kinolar ostidagi <b>«Tanlanganlarga qo'shish ⭐»</b> tugmasini bosib o'zingizga ma'qul kinolarni saqlab qo'yishingiz mumkin.",
            parse_mode="HTML"
        )
        return
        
    text = f"⭐️ <b>Sizning saqlangan kinolaringiz ({len(favs)} ta):</b>\n\n"
    builder = InlineKeyboardBuilder()
    for movie_id, caption, _ in favs[:15]:
        title = caption[:30] if caption else f"Kino {movie_id}"
        text += f"🎬 <b>{movie_id}</b> — {title}\n"
        builder.button(text=f"🎬 {movie_id}", callback_data=f"show_movie_{movie_id}")
        
    builder.adjust(3)
    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("fav_toggle_"))
async def toggle_favorite_callback(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    is_fav = await db_req.is_favorite(user_id, movie_id)
    if is_fav:
        await db_req.remove_favorite(user_id, movie_id)
        answer_msg = "Kino saqlanganlardan o'chirildi ❌"
        new_fav = False
    else:
        await db_req.add_favorite(user_id, movie_id)
        answer_msg = "Kino saqlanganlarga qo'shildi ⭐"
        new_fav = True
        
    avg_rating = await db_req.get_movie_average_rating(movie_id)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_movie_action_keyboard(movie_id, new_fav, avg_rating)
        )
    except Exception:
        pass
    await callback.answer(answer_msg, show_alert=True)


# ─── IZOHLAR LIKELARI ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("like_comm_"))
async def toggle_comment_like_callback(callback: CallbackQuery):
    comm_id = int(callback.data.split("_")[2])
    liked, count = await db_req.toggle_comment_like(comm_id, callback.from_user.id)
    status_txt = "Like bosildi! ❤️" if liked else "Like olib tashlandi 💔"
    await callback.answer(f"{status_txt} (Jami: {count})")


# ─── SAQLANGAN KINOLAR (FAVORITES) ───────────────────────────────────────────
@router.message(F.text.regexp(r"(?i).*(saqlanganlar|tanlanganlar).*"))
async def user_favorites_list(message: Message, state: FSMContext):
    await state.clear()
    favs = await db_req.get_user_favorites(message.from_user.id)
    if not favs:
        await message.answer(
            "⭐️ <b>Sizda hali saqlangan kinolar yo'q.</b>\n\n"
            "Kinolar ostidagi <b>«Tanlanganlarga qo'shish ⭐»</b> tugmasini bosib o'zingizga ma'qul kinolarni saqlab qo'yishingiz mumkin.",
            parse_mode="HTML"
        )
        return
        
    text = f"⭐️ <b>Sizning saqlangan kinolaringiz ({len(favs)} ta):</b>\n\n"
    builder = InlineKeyboardBuilder()
    for movie_id, caption, _ in favs[:15]:
        title = caption[:30] if caption else f"Kino {movie_id}"
        text += f"🎬 <b>/{movie_id}</b> — {title}\n"
        builder.button(text=f"🎬 {movie_id}", callback_data=f"show_movie_{movie_id}")
        
    builder.adjust(3)
    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

@router.callback_query(F.data == "show_favorites_profile")
async def show_favorites_profile_cb(callback: CallbackQuery):
    favs = await db_req.get_user_favorites(callback.from_user.id)
    if not favs:
        await callback.answer("Sizda hali saqlangan kinolar yo'q.", show_alert=True)
        return
    text = f"⭐️ <b>Sizning saqlangan kinolaringiz ({len(favs)} ta):</b>\n\n"
    builder = InlineKeyboardBuilder()
    for movie_id, caption, _ in favs[:15]:
        title = caption[:30] if caption else f"Kino {movie_id}"
        text += f"🎬 <b>/{movie_id}</b> — {title}\n"
        builder.button(text=f"🎬 {movie_id}", callback_data=f"show_movie_{movie_id}")
    builder.adjust(3)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()


# ─── QO'LLAB-QUVVATLASH / ADMINGA MUROJAAT (SUPPORT TICKETS) ───────────────────
@router.message(Command("help"))
@router.message(F.text.regexp(r"(?i).*(yordam|murojaat).*"))
async def user_support_ticket_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_for_support_ticket)
    await message.answer(
        "🆘 <b>Adminlarimiz bilan bog'lanish (Qo'llab-quvvatlash):</b>\n\n"
        "Savolingiz, murojaatingiz yoki taklifingiz bo'lsa, uni quyida yozib yuboring.\n"
        "Adminlarimiz xabaringizni ko'rib chiqib, sizga tez arada javob yuborishadi.",
        parse_mode="HTML"
    )

@router.message(UserStates.waiting_for_support_ticket, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def user_support_ticket_save(message: Message, state: FSMContext):
    ticket_text = message.text.strip()
    user_id = message.from_user.id
    user_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name or str(user_id)
    
    ticket_id = await db_req.create_ticket(user_id, ticket_text)
    await state.clear()
    
    from keyboards.inline import get_ticket_reply_keyboard
    admin_alert = (
        f"🆘 <b>YANGI MUROJAAT / TICKET (#{ticket_id})</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {user_name} (ID: <code>{user_id}</code>)\n"
        f"📝 <b>Matn:</b> <i>{ticket_text}</i>\n\n"
        "Javob berish uchun quyidagi tugmani bosing:"
    )
    
    for admin_id in config.ADMINS:
        try:
            await message.bot.send_message(
                admin_id,
                admin_alert,
                parse_mode="HTML",
                reply_markup=get_ticket_reply_keyboard(ticket_id)
            )
        except Exception:
            pass
            
    await message.answer(
        f"✅ <b>Murojaatingiz adminlarga yetkazildi! (Ticket #{ticket_id})</b>\n\n"
        "Adminlarimiz ko'rib chiqqach, javob ushbu bot orqali sizga yuboriladi.",
        parse_mode="HTML"
    )


# ─── USER 4: 👑 MENING PROFILIM (PROFILE CARD & LEVELS) ───────────────────────
@router.message(Command("profile"))
@router.message(F.text.in_(["👑 Profilim", "Profilim 👑", "Profilim", "Mening Profilim 👑", "Mening Profilim"]))
async def user_profile_card(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user = await db_req.get_user(user_id)
    
    if not user:
        await message.answer("Foydalanuvchi topilmadi.")
        return
        
    pts = user[6] if len(user) > 6 and user[6] is not None else 0
    ref_count = user[5] if len(user) > 5 and user[5] is not None else 0
    
    level_name, level_emoji, next_limit = db_req.get_user_level(pts)
    is_premium = await db_req.is_user_premium(user_id)
    status_str = "👑 VIP / Premium" if is_premium else "Standard Foydalanuvchi"
    
    favs = await db_req.get_user_favorites(user_id)
    fav_count = len(favs) if favs else 0
    
    birthday = await db_req.get_user_birthday(user_id)
    bday_str = birthday if birthday else "Kiritilmagan ❌"
    
    next_info = f"\n🎯 Keyingi daraja (VIP) uchun: <code>{next_limit - pts}</code> ball qoldi." if next_limit is not None else ""
    
    txt = (
        f"👑 <b>SHAXSIY PROFILINGIZ:</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {message.from_user.full_name}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"🌟 <b>Darajangiz:</b> {level_emoji} <b>{level_name}</b>\n"
        f"💎 <b>To'plangan Ballar:</b> <code>{pts}</code> 💎{next_info}\n"
        f"👥 <b>Chaqirgan Referallaringiz:</b> <code>{ref_count}</code> ta\n"
        f"⭐️ <b>Saqlangan Kinolaringiz:</b> <code>{fav_count}</code> ta\n"
        f"🎂 <b>Tug'ilgan Kuningiz:</b> <code>{bday_str}</code>\n"
        f"🛡 <b>Maqomingiz:</b> {status_str}"
    )
    
    from keyboards.inline import get_profile_keyboard
    await message.answer(txt, parse_mode="HTML", reply_markup=get_profile_keyboard())

@router.callback_query(F.data == "show_watch_history")
async def show_watch_history_callback(callback: CallbackQuery):
    history = await db_req.get_watch_history(callback.from_user.id, limit=10)
    if not history:
        await callback.answer("Sizda hali ko'rilgan kinolar tarixi yo'q.", show_alert=True)
        return
        
    txt = "🕒 <b>Oxirgi ko'rilgan kinolaringiz:</b>\n\n"
    builder = InlineKeyboardBuilder()
    for m_id, cap, w_at in history:
        title = cap[:25] if cap else f"Kino {m_id}"
        txt += f"🎬 <b>{m_id}</b> — {title} (<i>{w_at}</i>)\n"
        builder.button(text=f"🎬 {m_id}", callback_data=f"show_movie_{m_id}")
    builder.adjust(3)
    await callback.message.answer(txt, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()


# ─── USER 6: 🔝 TOP 100 ENG YUQORI BAHOLANGAN KINOLAR ────────────────────────
@router.message(Command("top"))
@router.message(F.text.in_(["🔝 TOP Kinolar", "TOP Kinolar 🔝", "TOP Kinolar"]))
async def user_top_movies_list(message: Message, state: FSMContext):
    await state.clear()
    await render_top_movies(message, page=1)

@router.callback_query(F.data.startswith("top_movies_page_"))
async def top_movies_page_callback(callback: CallbackQuery):
    page = int(callback.data.split("_")[3])
    await render_top_movies(callback.message, page=page, is_callback=True)
    await callback.answer()

@router.callback_query(F.data == "show_top_movies_1")
async def show_top_movies_profile_callback(callback: CallbackQuery):
    await render_top_movies(callback.message, page=1, is_callback=True)
    await callback.answer()

async def render_top_movies(event: Message, page: int = 1, is_callback: bool = False):
    top_movies = await db_req.get_top_rated_movies(limit=100)
    if not top_movies:
        txt = "🔝 <b>Hali baholangan kinolar mavjud emas.</b>"
        if is_callback:
            await event.edit_text(txt, parse_mode="HTML")
        else:
            await event.answer(txt, parse_mode="HTML")
        return
        
    per_page = 10
    total_pages = (len(top_movies) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = top_movies[start_idx:end_idx]
    
    txt = f"🔝 <b>ENG YUQORI BAHOLANGAN KINOLAR (TOP 100)</b>\n<i>Sahifa {page}/{total_pages}</i>\n\n"
    
    builder = InlineKeyboardBuilder()
    for rank, (m_id, cap, avg_r, votes, views) in enumerate(page_items, start_idx + 1):
        title = cap[:25] if cap else f"Kino {m_id}"
        stars = "⭐" * round(avg_r) if avg_r else ""
        txt += f"<b>#{rank}</b> 🎬 <b>/{m_id}</b> — {title}\n└ Reyting: <b>{avg_r:.1f}</b>/5 ({votes} ovoz) {stars}\n\n"
        builder.button(text=f"🎬 {m_id}", callback_data=f"show_movie_{m_id}")
        
    builder.adjust(3)
    
    from keyboards.inline import get_top_movies_keyboard
    nav_kb = get_top_movies_keyboard(page, total_pages)
    
    # Tugmalarni birlashtirish
    combined_builder = InlineKeyboardBuilder()
    for btn_row in builder.export():
        combined_builder.row(*btn_row)
    for btn_row in nav_kb.inline_keyboard:
        combined_builder.row(*btn_row)
        
    if is_callback:
        await event.edit_text(txt, parse_mode="HTML", reply_markup=combined_builder.as_markup())
    else:
        await event.answer(txt, parse_mode="HTML", reply_markup=combined_builder.as_markup())


# ─── USER 8: 🎂 TUG'ILGAN KUN BONUSI (KK.OO.YYYY) ────────────────────────────
@router.message(F.text.regexp(r"(?i).*(tug'ilgan kun).*"))
async def user_birthday_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    existing_bday = await db_req.get_user_birthday(user_id)
    
    if existing_bday:
        await message.answer(
            f"🎂 <b>Sizning saqlangan tug'ilgan kuningiz:</b> <code>{existing_bday}</code>\n\n"
            f"⚠️ <i>Eslatma: Tug'ilgan kun ma'lumotlari 1 marta saqlanadi va o'zgartirib bo'lmaydi.\n"
            f"Har yili ushbu kunda sizga <b>+50 💎 ball</b> va <b>👑 1 kunlik VIP</b> taqdim etiladi!</i>",
            parse_mode="HTML"
        )
        return
        
    await state.set_state(UserStates.waiting_for_birthday)
    await message.answer(
        "🎂 <b>Tug'ilgan kuningizni kiriting!</b>\n\n"
        "Agar botimizdan tug'ilgan kuningizda:\n"
        "  🎁 <b>+50 💎 ball</b>\n"
        "  👑 <b>1 kunlik VIP maqomi</b>\n"
        "  🎉 <b>Shaxsiy tabrik xabari</b> olmoqchi bo'lsangiz, quyidagi formatda yuboring:\n\n"
        "📅 <b>Format:</b> <code>KK.OO.YYYY</code>\n"
        "  <i>Masalan: 10.10.2013 (10-oktyabr 2013-yil)</i>\n\n"
        "⚠️ <b>Eslatma:</b>\n"
        "  • Yosh 12 yosh va undan yuqori bo'lishi kerak\n"
        "  • Tug'ilgan kun 1 marta saqlanadi va qayta kiritib bo'lmaydi\n"
        "  • Noto'g'ri ma'lumot kiritilsa bonus berilmaydi va imkoniyat yo'qoladi!",
        parse_mode="HTML"
    )

@router.message(UserStates.waiting_for_birthday, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def user_birthday_save(message: Message, state: FSMContext):
    import re
    from datetime import datetime
    
    text = message.text.strip()
    user_id = message.from_user.id
    
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", text):
        await message.answer(
            "⚠️ <b>Noto'g'ri format!</b>\n\n"
            "Iltimos, <code>KK.OO.YYYY</code> formatida kiriting.\n"
            "<i>Masalan: 10.10.2013</i>",
            parse_mode="HTML"
        )
        return
        
    try:
        b_day, b_month, b_year = map(int, text.split("."))
        birth_dt = datetime(year=b_year, month=b_month, day=b_day)
    except ValueError:
        await message.answer("⚠️ <b>Mavjud bo'lmagan sana kiritildi!</b> Iltimos to'g'ri sana kiriting (Masalan: 10.10.2013):", parse_mode="HTML")
        return
        
    now = datetime.now()
    if birth_dt > now:
        await message.answer("⚠️ Tug'ilgan kun kelajakdagi sana bo'la olmaydi! Qayta kiriting:")
        return
        
    # Yosh hisoblash
    age = now.year - birth_dt.year - ((now.month, now.day) < (birth_dt.month, birth_dt.day))
    
    if age < 12:
        # Qoida: 12 yoshdan kichik bo'lsa qayta imkoniyat berilmasin!
        await db_req.set_user_birthday(user_id, "BLOCKED_UNDERAGE")
        await state.clear()
        await message.answer(
            f"❌ <b>Uzr!</b> Botimizdan foydalanish va tug'ilgan kun bonusini olish uchun yoshingiz kamida <b>12 da</b> bo'lishi kerak.\n\n"
            f"Siz kiritgan sana bo'yicha yoshingiz <b>{age} da</b> bo'lgani sababli tug'ilgan kuningiz saqlanmadi va qayta kiritish imkoniyati berilmaydi.",
            parse_mode="HTML"
        )
        return
        
    success = await db_req.set_user_birthday(user_id, text)
    await state.clear()
    
    if success:
        await message.answer(
            f"🎉 <b>Tabriklaymiz! Tug'ilgan kuningiz ({text}) muvaffaqiyatli saqlandi!</b>\n\n"
            f"Har yili ushbu kunda botimiz sizga <b>+50 💎 ball</b> va <b>👑 1 kunlik VIP maqomi</b> taqdim etadi!",
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Siz allaqachon tug'ilgan kuningizni saqlagansiz!")


# ─── SHOW MOVIE CALLBACK HANDLER WITH DAILY LIMIT ─────────────────────────────
@router.callback_query(F.data.startswith("show_movie_"))
async def show_movie_callback(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    is_premium = await db_req.is_premium_user(user_id)
    if not is_premium:
        daily_count = await db_req.get_daily_movie_count(user_id)
        bonus_limit = await db_req.get_daily_bonus_limit(user_id)
        max_allowed = 3 + bonus_limit
        if daily_count >= max_allowed:
            await callback.answer(
                f"⚠️ Kunlik limit tugadi! Bugun {max_allowed} ta kino ko'rishingiz mumkin edi.",
                show_alert=True
            )
            return

    movie = await db_req.get_movie(movie_id)
    if movie:
        if not is_premium:
            await db_req.increment_daily_movie_count(user_id)

        await db_req.add_to_watch_history(user_id, movie_id)

        file_id, caption = movie
        avg_rating, votes = await db_req.get_movie_rating(movie_id)
        is_fav = await db_req.is_favorite(user_id, movie_id)

        cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿"
        if avg_rating > 0:
            cap += f"\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz)"
        cap += f"\n\n🤖 {config.BOT_USERNAME}"

        await callback.message.answer_video(
            video=file_id,
            caption=cap,
            parse_mode="HTML",
            reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating)
        )
        await callback.answer()
    else:
        await callback.answer("❌ Kino topilmadi", show_alert=True)


# ─── KUNLIK BONUS (+3 BALL) ───────────────────────────────────────────────────
@router.message(Command("bonus"))
@router.message(F.text.regexp(r"(?i).*(kunlik bonus).*"))
async def user_daily_bonus(message: Message, state: FSMContext):
    await state.clear()
    success, msg, pts = await db_req.claim_daily_bonus(message.from_user.id)
    await message.answer(msg, parse_mode="HTML")


# ─── MATNLI QIDIRUV (FALLBACK AT THE VERY END OF FILE) ───────────────────────
@router.message(F.text, ~F.text.startswith("/"))
async def search_movie_by_text(message: Message, state: FSMContext = None):
    query = message.text.strip()
    # Raqamlar va URL havolalar kino nomi emas
    if query.isdigit() or query.lstrip('/').isdigit() or query.startswith(("http://", "https://", "t.me/")) or "://" in query:
        return
    if not query or len(query) < 2:
        await message.answer("🔍 Kamida 2 ta belgi kiriting.")
        return

    # Agar yuborilgan matn menyu tugmasi bo'lsa, kino izlamaymiz
    text_clean = query.lower().replace("\ufe0f", "").strip()
    menu_keywords = [
        "qidirish", "saqlanganlar", "tanlanganlar", "tasodifiy", "so'rash",
        "ballarim", "bonus", "reytinglar", "referal", "so'rovlari",
        "sozlamalar", "profilim", "top kinolar", "tug'ilgan kun", "yordam", "murojaat",
        "kino qo'shish", "kino o'chirish", "kino tahrirlash", "statistika", "reklama",
        "kassa", "audit", "tahlili", "bot rejimi", "nofaollarga", "promo", "zaxira",
        "moderatorlar", "trendlari", "kun kinosi", "shubhali", "keshni", "ommaviy"
    ]
    if any(kw in text_clean for kw in menu_keywords):
        return

    # @username NUMBER shaklida kelgan xabarni aniqlash
    import re, urllib.parse as _up
    ref_match = re.match(r"^@\w+\s+\d+$", query.lower())
    ref_link_match = re.search(r"t\.me/\w+\?start=(\d+)", query)
    if ref_match or ref_link_match:
        sender_id = message.from_user.id
        if ref_link_match:
            ref_owner_id = int(ref_link_match.group(1))
        else:
            ref_owner_id = sender_id

        _bot_clean = config.BOT_USERNAME.lstrip('@')
        _ref_link = f"https://t.me/{_bot_clean}?start={sender_id}"
        _share_text = "🚀 Kino bot - ko'p kino, bepul, qulay!\n\nQuyidagi havola orqali kiring:"
        _share_url = f"https://t.me/share/url?url={_up.quote(_ref_link)}&text={_up.quote(_share_text)}"

        _file_id = await db_req.get_setting("ref_promo_file_id")
        _mtype = await db_req.get_setting("ref_promo_media_type")
        _caption_txt = await db_req.get_setting("ref_promo_caption")
        if not _caption_txt:
            _caption_txt = (
                "🚀 <b>Bizning bot orqali eng sara kinolarni tomosha qiling!</b>\n\n"
                "🍿 Har kuni yangi va qiziqarli filmlar!\n"
                "⚡ Botdan bepul foydalanish va qulay izlash."
            )
        _cap = f"{_caption_txt}\n\n🚀 {_ref_link}"
        _kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📍 Boshlash:", url=f"https://t.me/{_bot_clean}")],
            [InlineKeyboardButton(text="Do'stlarga ulashish 🚀", url=_share_url)],
        ])
        try:
            if _file_id and _mtype == "video":
                await message.answer_video(video=_file_id, caption=_cap, reply_markup=_kb, parse_mode="HTML")
            elif _file_id and _mtype == "photo":
                await message.answer_photo(photo=_file_id, caption=_cap, reply_markup=_kb, parse_mode="HTML")
            else:
                await message.answer(_cap, reply_markup=_kb, parse_mode="HTML")
        except Exception:
            pass
        return

    inline_match = re.match(r"^@\w+\s+(\d+)$", query)
    if inline_match:
        movie_id = int(inline_match.group(1))
        movie = await db_req.get_movie(movie_id)
        if movie:
            file_id, caption = movie
            avg_rating, votes = await db_req.get_movie_rating(movie_id)
            is_fav = await db_req.is_favorite(message.from_user.id, movie_id)
            rating_stars = "⭐" * round(avg_rating) if avg_rating else ""
            cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿"
            if avg_rating > 0:
                cap += f"\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}"
            cap += f"\n\n🤖 {config.BOT_USERNAME}"
            await message.answer_video(
                video=file_id,
                caption=cap,
                parse_mode="HTML",
                reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating)
            )
        else:
            await message.answer(f"❌ <b>{movie_id}</b> kodli kino topilmadi.")
        return

    results = await db_req.search_movies_by_name(query)
    
    if results:
        text = f"🔍 <b>'{query}' bo'yicha topilganlar:</b>\n\n"
        for movie_id, caption in results:
            name = caption[:40] if caption else "(nomsiz)"
            text += f"🎬 /{movie_id} — {name}\n"
        text += "\nKinoni olish uchun uning kodini ustiga bosing."
        await message.answer(text)
    else:
        try:
            all_movies = await db_req.get_all_movie_titles()
            suggestions = []
            
            def get_levenshtein_distance(s1, s2):
                if len(s1) < len(s2):
                    return get_levenshtein_distance(s2, s1)
                if len(s2) == 0:
                    return len(s1)
                previous_row = range(len(s2) + 1)
                for i, c1 in enumerate(s1):
                    current_row = [i + 1]
                    for j, c2 in enumerate(s2):
                        insertions = previous_row[j + 1] + 1
                        deletions = current_row[j] + 1
                        substitutions = previous_row[j] + (c1 != c2)
                        current_row.append(min(insertions, deletions, substitutions))
                    previous_row = current_row
                return previous_row[-1]

            q_low = query.lower()
            for movie_id, caption in all_movies:
                if not caption:
                    continue
                cap_low = caption.lower()
                
                if q_low in cap_low:
                    score = 0.9 - (len(cap_low) - len(q_low)) * 0.005
                else:
                    dist = get_levenshtein_distance(q_low, cap_low)
                    max_len = max(len(q_low), len(cap_low))
                    score = 1.0 - (dist / max_len) if max_len > 0 else 0.0
                
                if score > 0.3:
                    suggestions.append((score, movie_id, caption))
            
            suggestions.sort(key=lambda x: x[0], reverse=True)
            
            if suggestions:
                suggestion_text = f"❌ <b>'{query}'</b> nomli kino topilmadi.\n\n🤔 <b>Balki quyidagi kinolardan birini qidirgandirsiz?</b>\n\n"
                for score, movie_id, caption in suggestions[:3]:
                    name = caption[:45] if caption else "(nomsiz)"
                    suggestion_text += f"🎬 /{movie_id} — {name}\n"
                suggestion_text += "\nKo'rish uchun kino kodi ustiga bosing."
                await message.answer(suggestion_text, parse_mode="HTML")
                return
        except Exception:
            pass

        await message.answer(
            f"❌ <b>'{query}'</b> nomli kino topilmadi.\n\n"
            "Iltimos, kino nomini to'g'ri yozing yoki <b>Kino so'rash 📥</b> tugmasidan foydalaning."
        )




