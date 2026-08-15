import random
from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultCachedVideo, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config
from database import requests as db_req
from keyboards.reply import get_admin_menu, get_user_menu, get_moderator_menu
from keyboards.inline import get_subscription_keyboard, get_movie_action_keyboard, get_rating_keyboard, get_comments_keyboard
router = Router()

PREMIUM_PLANS = {
    'premium_1w': {
        'name': '1 haftalik Premium',
        'label': '1 haftalik',
        'days': 7,
        'stars': 25,
        'card_base': 7000
    },
    'premium_monthly': {
        'name': '1 oylik Premium',
        'label': '1 oylik',
        'days': 30,
        'stars': 80,
        'card_base': 20000
    },
    'premium_quarterly': {
        'name': '3 oylik Premium',
        'label': '3 oylik',
        'days': 90,
        'stars': 200,
        'card_base': 50000
    },
    'premium_6m': {
        'name': '6 oylik Premium',
        'label': '6 oylik',
        'days': 180,
        'stars': 430,
        'card_base': 100000
    },
    'premium_1y': {
        'name': '1 yillik Premium',
        'label': '1 yillik',
        'days': 365,
        'stars': 800,
        'card_base': 180000
    },
    'premium_yearly': {
        'name': '1 yillik Premium',
        'label': '1 yillik',
        'days': 365,
        'stars': 800,
        'card_base': 180000
    }
}

CONTACT_FOOTER = '\n\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'

def with_footer(text):
    if text is None:
        return text
    if not isinstance(text, str):
        return text
    if "8245305906" in text or "Abdulaziz7o1" in text or "Murojaat uchun" in text:
        return text
    return f"{text}{CONTACT_FOOTER}"


def fmt_price(n: int) -> str:
    """Narxni 'X ming so'm' yoki 'X ming Y so'm' formatda qaytarish"""
    m = n // 1000
    r = n % 1000
    return f"{m} ming {r} so'm" if r else f"{m} ming so'm"
USER_MENU_BUTTONS = ['🔍 Kino qidirish', 'Kino qidirish 🔍', 'Kino qidirish', 'Tanlanganlar ⭐️', 'Saqlanganlar ⭐️', '⭐️ Saqlanganlar', 'Tanlanganlar', 'Saqlanganlar', 'Tasodifiy Kino 🎲', 'Tasodifiy Kino', "Kino so'rash 🎬", "Kino so'rash 📥", "Kino so'rash", '💎 Mening Ballarim', 'Mening Ballarim 💎', 'Mening Ballarim', 'Ballar 💎', '🏆 Reytinglar', 'Reytinglar 🏆', 'Reytinglar', '👥 Referal', 'Referal 👥', 'Takliflar (Referal) 👥', 'Referal', "🗳️ Kino so'rovlari", "Kino so'rovlari 📥", "Kino so'rovlari 🗳️", "Kino so'rovlari", '⚙️ Sozlamalar', 'Sozlamalar ⚙️', 'Sozlamalar', '🎁 Kunlik Bonus', 'Kunlik Bonus 🎁', 'Kunlik Bonus', '👑 Profilim', 'Profilim 👑', 'Profilim', '🔝 TOP Kinolar', 'TOP Kinolar 🔝', 'TOP Kinolar', "🎂 Tug'ilgan Kun", "Tug'ilgan Kun 🎂", "Tug'ilgan Kun", '🆘 Yordam / Murojaat', 'Yordam / Murojaat 🆘', 'Yordam / Murojaat', 'Yordam']

class UserStates(StatesGroup):
    waiting_for_request_name = State()
    waiting_for_comment = State()
    waiting_for_movie_search = State()
    waiting_for_movie_request = State()
    waiting_for_support_ticket = State()
    waiting_for_birthday = State()
    waiting_for_payment_receipt = State()
    waiting_for_promo_code_input = State()

async def execute_start_logic(message: Message, state: FSMContext):
    """Start logikasini bajarish (umumiy funksiya)"""
    await state.clear()
    user_id = message.from_user.id
    user = message.from_user
    name_to_show = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1:
        start_arg = args[1]
        if start_arg.isdigit():
            referred_id = int(start_arg)
            if referred_id != user_id:
                existing_user = await db_req.get_user(user_id)
                if not existing_user:
                    referred_by = referred_id
    await db_req.add_user(user_id, user.username or '', user.full_name, referred_by)
    db_admins = await db_req.get_all_admins()
    if user_id in config.ADMINS:
        await message.answer(with_footer(f'👋 <b>Assalomu alaykum, Bosh Admin {name_to_show}!</b>\n\n🛠 <b>Bot boshqaruv paneliga xush kelibsiz.</b>\nQuyidagi menyudan foydalanib botni boshqarishingiz mumkin:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_admin_menu())
    elif user_id in db_admins:
        await message.answer(with_footer(f'👋 <b>Assalomu alaykum, Moderator {name_to_show}!</b>\n\n🛠 <b>Moderator paneliga xush kelibsiz.</b>\nQuyidagi menyudan foydalanib botni boshqarishingiz mumkin:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_moderator_menu())
    else:
        # Texnik ishlar rejimi tekshiruvi (Admin 4)
        if await db_req.is_maintenance_mode():
            m_txt = (
                "🛠 <b>BOTDA TEXNIK YANGILANISH KETMOQDA!</b>\n\n"
                "Hurmatli foydalanuvchi, ayni daqiqalarda botimiz serverida rejali profilaktika va optimallashtirish ishlari olib borilmoqda. ⚡\n\n"
                "⏳ <i>Iltimos, 15-20 daqiqadan so'ng qayta urinib ko'ring. Noqulaylik uchun uzr so'raymiz!</i>"
            )
            await message.answer(with_footer(m_txt), parse_mode='HTML')
            return

        # Premium foydalanuvchi - kanal tekshiruvini o'tkazib yuborish
        is_prem = await db_req.is_premium_user(user_id)
        if is_prem:
            await message.answer(with_footer(f'👑 <b>Assalomu alaykum, {name_to_show}!</b>\n\n🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n⚡ Quyidagi menyudan foydalaning:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_user_menu())
        else:
            await message.answer(with_footer(f'👋 <b>Assalomu alaykum, {name_to_show}!</b>\n\n🍿 <b>Kino botiga xush kelibsiz!</b>\n\n🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n⚡ Quyidagi menyudan foydalaning:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_user_menu())

@router.message(CommandStart(), StateFilter('*'))
@router.message(Command('start'), StateFilter('*'))
async def cmd_start(message: Message, state: FSMContext):
    """Start komandasi - umumiy start logikasini chaqirish"""
    await execute_start_logic(message, state)
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith('movie_'):
        raw_id = args[1][len('movie_'):]
        if raw_id.isdigit():
            movie_id = int(raw_id)
            user_id = message.from_user.id
            movie = await db_req.get_movie(movie_id, user_id=user_id)
            if movie:
                file_id, caption, views_count, is_prem_only = (movie[0], movie[1], movie[2] if len(movie) > 2 else 0, movie[3] if len(movie) > 3 else 0)
                if is_prem_only and not (await db_req.is_premium_user(user_id)):
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💎 Premium Obuna Sotib Olish", callback_data="sub_buy_premium")],
                        [InlineKeyboardButton(text="⏳ 1 Soatlik Bepul VIP Sinov", callback_data="claim_vip_trial_cb")]
                    ])
                    txt = (
                        f"🔒 <b>BU KINO FAQAT PREMIUM OBUNACHILAR UCHUN!</b> 👑\n\n"
                        f"🎬 <b>Kino kodi:</b> /{movie_id}\n\n"
                        f"Ushbu kinoni tomosha qilish uchun <b>VIP Premium</b> obunaga ega bo'lishingiz yoki <b>1 soatlik bepul VIP sinov</b>dan foydalanishingiz kerak! 🍿"
                    )
                    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)
                    return
                await db_req.add_to_watch_history(user_id, movie_id)
                avg_rating, votes = await db_req.get_movie_rating(movie_id)
                is_fav = await db_req.is_favorite(user_id, movie_id)
                rating_stars = '⭐' * round(avg_rating) if avg_rating else ''
                cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿"
                if views_count:
                    cap += f'\n📥 <b>Yuklashlar:</b> {views_count:,} marta'
                if avg_rating > 0:
                    cap += f'\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}'
                cap += f'\n\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
                await message.answer_video(video=file_id, caption=with_footer(cap), parse_mode='HTML', protect_content=True, reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating))
            else:
                await message.answer(with_footer(f'❌ <b>{movie_id}</b> kodli kino topilmadi.'), parse_mode='HTML')

@router.message(F.text == '🚀 Boshlash')
async def btn_start(message: Message, state: FSMContext):
    """Boshlash tugmasi - start logikasini chaqirish"""
    await state.clear()
    user_id = message.from_user.id
    user = message.from_user
    name_to_show = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    await db_req.add_user(user_id, user.username, user.first_name)
    db_admins = await db_req.get_all_admins()
    if user_id in config.ADMINS or user_id in db_admins:
        await message.answer(with_footer(f'👋 Assalomu alaykum, {name_to_show}!\n\n🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n⚡ Quyidagi menyudan foydalaning:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_user_menu())
        return
    # Premium foydalanuvchi sponsor kanal tekshiruvidan o'tkazilmaydi
    is_prem = await db_req.is_premium_user(user_id)
    if is_prem:
        await message.answer(with_footer(f'👑 Assalomu alaykum, {name_to_show}!\n\n🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n⚡ Quyidagi menyudan foydalaning:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_user_menu())
        return
    db_channels = await db_req.get_sponsor_channels()
    all_channels = list(config.CHANNELS) + [c[1] for c in db_channels]
    if all_channels:
        channel_buttons = []
        for channel in all_channels:
            try:
                chat = await message.bot.get_chat(channel)
                channel_buttons.append([InlineKeyboardButton(text=chat.title, url=f'https://t.me/{channel}')])
            except Exception:
                channel_buttons.append([InlineKeyboardButton(text=channel, url=f'https://t.me/{channel}')])
        channel_buttons.append([InlineKeyboardButton(text='✅ Obunani tekshirish', callback_data='check_sub')])
        await message.answer(with_footer(f"👋 Assalomu alaykum, {name_to_show}!\n\n🎬 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:{CONTACT_FOOTER}"), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(inline_keyboard=channel_buttons))
    else:
        await message.answer(with_footer(f'👋 Assalomu alaykum, {name_to_show}!\n\n🎬 Bot orqali eng sara kinolarni tomosha qilishingiz mumkin.\n⚡ Quyidagi menyudan foydalaning:{CONTACT_FOOTER}'), parse_mode='HTML', reply_markup=get_user_menu())

@router.callback_query(F.data == 'check_sub')
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot = callback.bot
    db_channels = await db_req.get_sponsor_channels()
    formatted_channels = []
    for ch in config.CHANNELS:
        formatted_channels.append((ch, ch))
    for db_ch in db_channels:
        formatted_channels.append((db_ch[1], db_ch[2] or db_ch[1]))
    not_subscribed = []
    for ch_tuple in formatted_channels:
        ch_id = ch_tuple[0]
        ch_target = str(ch_id).strip()
        if 't.me/' in ch_target:
            parts = ch_target.split('t.me/')[1].strip('/')
            if not parts.startswith('+') and (not parts.startswith('joinchat/')) and (not parts.startswith('c/')):
                ch_target = '@' + parts.split('/')[0]
        try:
            member = await bot.get_chat_member(chat_id=ch_target, user_id=user_id)
            if member.status not in ['creator', 'administrator', 'member']:
                not_subscribed.append(ch_tuple)
        except Exception as e:
            print(f'Kanal tekshirishda xato ({ch_target}): {e}')
            not_subscribed.append(ch_tuple)
    if not_subscribed:
        await callback.answer("❌ Hali barcha homiy kanallarga a'zo bo'lmadingiz! Iltimos, a'zo bo'lib qayta bosing.", show_alert=True)
        return
    await db_req.check_and_reward_referral(callback.bot, user_id)
    await callback.message.edit_text(with_footer("✅ <b>Rahmat! Barcha homiy kanallarga muvaffaqiyatli a'zo bo'ldingiz.</b>\n\nEndi kino nomini yoki kodini yuborishingiz mumkin! 🍿"), parse_mode='HTML')
    await callback.answer("A'zolik tasdiqlandi! ✅", show_alert=True)

@router.message(StateFilter(None), F.text.regexp('^/?\\d+$'))
async def search_movie_by_code(message: Message):
    user_id = message.from_user.id
    
    # Texnik ishlar rejimi
    if user_id not in config.ADMINS and (await db_req.is_maintenance_mode()):
        await message.answer(with_footer("🛠 <b>Botda texnik ishlar olib borilmoqda. Qisqa vaqtdan so'ng qayta urinib ko'ring!</b>"), parse_mode='HTML')
        return

    # Anti-Scraping / Ketma-ket soxta bot so'rovlarini to'xtatish (Admin 15)
    if not db_req.check_anti_scraping_guard(user_id):
        await message.answer(with_footer("⚠️ <b>Iltimos, biroz sekinroq so'rov yuboring! (Anti-Spam himoyasi)</b>"), parse_mode='HTML')
        return

    movie_id = int(message.text.lstrip('/'))
    movie = await db_req.get_movie(movie_id, user_id=user_id)
    if movie:
        file_id, caption, views_count, is_prem_only = (movie[0], movie[1], movie[2] if len(movie) > 2 else 0, movie[3] if len(movie) > 3 else 0)
        if is_prem_only and not (await db_req.is_premium_user(user_id)):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Premium Obuna Sotib Olish", callback_data="sub_buy_premium")],
                [InlineKeyboardButton(text="⏳ 1 Soatlik Bepul VIP Sinov", callback_data="claim_vip_trial_cb")]
            ])
            txt = (
                f"🔒 <b>BU KINO FAQAT PREMIUM OBUNACHILAR UCHUN!</b> 👑\n\n"
                f"🎬 <b>Kino kodi:</b> /{movie_id}\n\n"
                f"Ushbu kinoni tomosha qilish uchun <b>VIP Premium</b> obunaga ega bo'lishingiz yoki <b>1 soatlik bepul VIP sinov</b>dan foydalanishingiz kerak! 🍿"
            )
            await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)
            return

        await db_req.add_to_watch_history(user_id, movie_id)
        avg_rating, votes = await db_req.get_movie_rating(movie_id)
        is_fav = await db_req.is_favorite(message.from_user.id, movie_id)
        likes, dislikes, fires = await db_req.get_movie_reactions(movie_id)
        rating_stars = '⭐' * round(avg_rating) if avg_rating else ''
        prem_badge = " [👑 VIP]" if is_prem_only else ""
        cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}{prem_badge}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿\n📥 <b>Yuklashlar:</b> {views_count:,} marta"
        if avg_rating > 0:
            cap += f'\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}'
        cap += f'\n\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
        await message.answer_video(video=file_id, caption=with_footer(cap), parse_mode='HTML', protect_content=True, reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating, likes, dislikes, fires))
        await _movie_watched_extra(user_id, caption)
    else:
        await message.answer(with_footer(f"❌ <b>Kino topilmadi!</b>\n\nKino kodi <code>{movie_id}</code> bo'yicha kino mavjud emas.\nIltimos, to'g'ri kino kodini kiriting yoki kino qidirishdan foydalaning.{CONTACT_FOOTER}"), parse_mode='HTML')
        return

@router.callback_query(F.data.startswith('react_'))
async def movie_reaction_cb(callback: CallbackQuery):
    parts = callback.data.split('_')
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
    await callback.answer(f'Reaksiyangiz saqlandi! {react_type.upper()} 👍', show_alert=False)

@router.callback_query(F.data.startswith('report_movie_'))
async def report_movie_cb(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    user = callback.from_user
    await db_req.add_movie_report(movie_id, user_id)
    uname = f'@{user.username}' if user.username else user.full_name or str(user_id)
    alert_admin_msg = f'⚠️ <b>KINO FAYLIDA NUQSON BOR SHIKOYATI!</b>\n\n🎬 <b>Kino ID:</b> <code>{movie_id}</code>\n👤 <b>Shikoyat qilgan:</b> {uname} (ID: <code>{user_id}</code>)\n📌 <i>Ushbu kinoda ovoz yoki rasm nuqsoni borligi haqida xabar berildi.</i>'
    for admin_id in config.ADMINS:
        try:
            await callback.bot.send_message(with_footer(admin_id), alert_admin_msg, parse_mode='HTML')
        except Exception:
            pass
    await callback.answer('Shikoyatingiz adminga yetkazildi! Rahmat! 🙏', show_alert=True)

@router.message(Command('search'))
@router.message(F.text.in_(['🔍 Kino qidirish', 'Kino qidirish 🔍', 'Kino qidirish']))
async def start_movie_search(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_for_movie_search)
    await message.answer(with_footer('🔍 <b>Kino qidirish:</b>\n\nQidirish uchun kino nomini yuboring:'), parse_mode='HTML')

@router.message(UserStates.waiting_for_movie_search, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def search_movie_by_name(message: Message, state: FSMContext):
    query = message.text.strip()
    await state.clear()
    if len(query) < 2:
        await message.answer(with_footer('❌ Iltimos, kamida 2 ta harf kiriting!'))
        return
    movies = await db_req.search_movies_by_name(query, limit=10)
    if movies:
        response = f'🔍 <b>Qidirish natijalari: "{query}"</b>\n\n'
        for movie_id, caption in movies:
            movie_name = caption.split('\n')[0] if caption else 'Nomsiz'
            response += f'🎬 /{movie_id} — {movie_name}\n'
        await message.answer(with_footer(response), parse_mode='HTML')
    else:
        await message.answer(with_footer(f'''❌ "{query}" bo'yicha kino topilmadi.'''), parse_mode='HTML')

@router.callback_query(F.data == 'sub_buy_premium')
async def sub_buy_premium_cb(callback: CallbackQuery):
    await callback.answer()
    await premium_info(callback.message)

@router.message(Command('premium'))
@router.message(F.text == '/premium')
@router.message(F.text.in_(['💎 Premium', '💎 VIP Premium', 'VIP Premium 💎', 'VIP Premium']))
async def premium_info(message: Message):
    user_id = message.from_user.id
    is_premium = await db_req.is_premium_user(user_id)
    if is_premium:
        import math
        from datetime import datetime
        subscription = await db_req.get_premium_subscription(user_id)
        if subscription:
            start_raw = subscription[1]
            end_raw = subscription[2]
            plan = subscription[3] or 'Premium'
            try:
                start_dt = datetime.fromisoformat(start_raw.replace(' ', 'T'))
                end_dt = datetime.fromisoformat(end_raw.replace(' ', 'T'))
                start_str = start_dt.strftime('%d.%m.%Y')
                end_str = end_dt.strftime('%d.%m.%Y')
                diff_sec = (end_dt - datetime.now()).total_seconds()
                if diff_sec <= 0:
                    days_left_str = '0 kun'
                elif diff_sec < 86400:
                    hours_left = max(1, int(diff_sec // 3600))
                    days_left_str = f'{hours_left} soat'
                else:
                    days_cnt = math.ceil(diff_sec / 86400)
                    days_left_str = f'{days_cnt} kun'
            except Exception:
                start_str = start_raw[:10] if start_raw else '—'
                end_str = end_raw[:10] if end_raw else '—'
                days_left_str = '?'
        else:
            end_raw = await db_req.get_user_premium_until(user_id)
            plan = 'Premium'
            start_str = '—'
            if end_raw:
                try:
                    end_dt = datetime.fromisoformat(end_raw.replace(' ', 'T'))
                    end_str = end_dt.strftime('%d.%m.%Y')
                    diff_sec = (end_dt - datetime.now()).total_seconds()
                    if diff_sec <= 0:
                        days_left_str = '0 kun'
                    elif diff_sec < 86400:
                        hours_left = max(1, int(diff_sec // 3600))
                        days_left_str = f'{hours_left} soat'
                    else:
                        days_cnt = math.ceil(diff_sec / 86400)
                        days_left_str = f'{days_cnt} kun'
                except Exception:
                    end_str = end_raw[:10]
                    days_left_str = '?'
            else:
                end_str = "Noma'lum"
                days_left_str = '?'
        await message.answer(with_footer(f"👑 <b>Premium Obuna — Faol</b> ✅\n\n📋 <b>Plan:</b> {plan}\n📅 <b>Boshlangan:</b> {start_str}\n⏳ <b>Tugaydi:</b> {end_str}\n🕐 <b>Qolgan muddat:</b> {days_left_str}\n\n🎁 <b>Premium imtiyozlari:</b>\n• Kunlik limit yo'q\n• Cheklovsiz kino ko'rish\n• Prioritet qo'llab-quvvatlash\n\n<i>Rahmat! Siz bizning Premium a'zomiz! 🙏</i>{CONTACT_FOOTER}"), parse_mode='HTML')
        return
    await send_or_edit_premium_plans_menu(message, user_id, is_edit=False)

async def send_or_edit_premium_plans_menu(event, user_id: int, is_edit: bool=False):
    discount_pct = await db_req.get_user_active_discount(user_id)
    is_repeat = await db_req.has_user_bought_premium_before(user_id)
    p_1w_b = await db_req.get_premium_price_1w()
    p_1m_b = await db_req.get_premium_price_1m()
    p_3m_b = await db_req.get_premium_price_3m()
    p_6m_b = await db_req.get_premium_price_6m()
    p_1y_b = await db_req.get_premium_price_1y()
    
    flash_active, flash_disc, flash_until = await db_req.get_flash_sale_status()
    
    if flash_active:
        calc = lambda p: max(1000, int(p * (100 - flash_disc) / 100) // 1000 * 1000)
        discount_hdr = f"\n\n⚡ <b>1 SOATLIK FLASH SALE — {flash_disc}% CHEGIRMA!</b> <i>({flash_until[:16]} gacha)</i>"
    elif discount_pct > 0:
        calc = lambda p: max(1000, int(p * (100 - discount_pct) / 100) // 1000 * 1000)
        discount_hdr = f"\n\n🔥 (<b>{discount_pct}% PROMO SKIDKA QO'LLANILDI!</b>)"
    elif is_repeat:
        calc = lambda p: max(1000, int(p * 0.85) // 1000 * 1000)
        discount_hdr = "\n\n🎉 (<b>15% TAKRORIY CHEGIRMA QO'LLANILDI!</b>)"
    else:
        calc = lambda p: p
        discount_hdr = ''
        
    p_1w, p_1m, p_3m, p_6m, p_1y = (calc(p_1w_b), calc(p_1m_b), calc(p_3m_b), calc(p_6m_b), calc(p_1y_b))

    def fmt(n):
        ming = n // 1000
        qoldi = n % 1000
        if qoldi:
            return f"{ming} ming {qoldi} so'm"
        return f"{ming} ming so'm"

    txt_plans = (
        f"1️⃣ <b>1 haftalik (7 kun):</b> {fmt(p_1w)} (⭐️ 25 Stars)\n"
        f"2️⃣ <b>1 oylik (30 kun):</b> {fmt(p_1m)} (⭐️ 80 Stars)\n"
        f"3️⃣ <b>3 oylik (90 kun):</b> {fmt(p_3m)} (⭐️ 200 Stars)\n"
        f"4️⃣ <b>6 oylik (180 kun):</b> {fmt(p_6m)} (⭐️ 430 Stars)\n"
        f"5️⃣ <b>1 yillik (365 kun):</b> {fmt(p_1y)} (⭐️ 800 Stars)"
    )
    
    trial_claimed = await db_req.has_claimed_vip_trial(user_id)
    
    kb_rows = [
        [
            InlineKeyboardButton(text=f'1️⃣ 1 haftalik - {fmt(p_1w)}', callback_data='premium_1w'),
            InlineKeyboardButton(text=f'2️⃣ 1 oylik - {fmt(p_1m)}', callback_data='premium_monthly')
        ],
        [
            InlineKeyboardButton(text=f'3️⃣ 3 oylik - {fmt(p_3m)}', callback_data='premium_quarterly'),
            InlineKeyboardButton(text=f'4️⃣ 6 oylik - {fmt(p_6m)}', callback_data='premium_6m')
        ],
        [
            InlineKeyboardButton(text=f'5️⃣ 1 yillik - {fmt(p_1y)}', callback_data='premium_1y')
        ]
    ]
    
    if not trial_claimed:
        kb_rows.append([
            InlineKeyboardButton(text="⏳ 1 Soatlik Bepul VIP Sinov", callback_data="claim_vip_trial_cb")
        ])
        
    kb_rows.append([
        InlineKeyboardButton(text='🏷️ Promo kod kiritish', callback_data='user_enter_promo'),
        InlineKeyboardButton(text="📞 Manual to'lov", callback_data='premium_manual')
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    text = (
        f"💎 <b>Premium obuna:</b>{discount_hdr}\n\n"
        f"📋 <b>Obuna rejalari:</b>\n\n"
        f"{txt_plans}\n\n"
        f"🎁 <b>Premium imtiyozlari:</b>\n"
        f"• Kunlik limit yo'q\n"
        f"• Cheklovsiz kino ko'rish\n"
        f"• Prioritet qo'llab-quvvatlash\n\n"
        f"👇 <b>Plan tanlang yoki Promo kod kiriting:</b>"
    )
    if is_edit and isinstance(event, CallbackQuery):
        await event.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    elif isinstance(event, Message):
        await event.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    elif isinstance(event, CallbackQuery):
        await event.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)

@router.callback_query(F.data == 'user_enter_promo')
async def user_enter_promo_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_promo_code_input)
    await callback.message.answer(with_footer("🏷️ <b>Promo kodingizni kiriting:</b>\n\n<i>Promo kod orqali bepul Premium, ballar yoki to'lov uchun skidka olishingiz mumkin!</i>"), parse_mode='HTML')
    await callback.answer()

async def _notify_admin_promo_auto_deleted(bot, code_name: str, used_c: int, max_u: int):
    """Admin(lar)ga promo kod limiti to'lib avtomatik o'chirilgani haqida rasmiy xabarnoma yuborish"""
    import config
    txt = f"🏛️ <b>RASMIY BILDIRISHNOMA: PROMO KOD LIMITI TUGADI</b>\n\n📋 <b>Tafsilotlar:</b>\n🔹 <b>Promo kod:</b> <code>{code_name}</code>\n📊 <b>Ishlatilganlik holati:</b> {used_c}/{max_u} marta (100% to'ldi)\n⚙️ <b>Bajarilgan chora:</b> Tizim tomonidan bazadan avtomatik va to'liq o'chirildi 🗑️\n\nℹ️ <i>Bot tizimi hamda xavfsizlik qoidalariga muvofiq, limiti to'liq bajarilgan promo kodlar qayta ishlatilmasligi uchun darhol tozalanadi.</i>"
    for admin_id in config.ADMINS:
        try:
            await bot.send_message(with_footer(admin_id), txt, parse_mode='HTML')
        except Exception:
            pass

@router.message(Command('promo'))
async def user_promo_cmd(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        code = args[1].strip()
        user_id = message.from_user.id
        success, msg, auto_del, disc_pct = await db_req.use_promo_code(user_id, code)
        if success:
            if auto_del:
                await _notify_admin_promo_auto_deleted(message.bot, auto_del['code'], auto_del['used'], auto_del['max'])
            if disc_pct == 100:
                await db_req.set_user_premium(user_id, days=30)
                await db_req.consume_user_discount(user_id)
                user_info = message.from_user
                uname = f'@{user_info.username}' if user_info.username else user_info.full_name
                p_1m_base = await db_req.get_premium_price_1m()
                await message.answer(with_footer(f"🎉 <b>TABRIKLAYMIZ!</b>\n\n🏷️ Siz kiritgan promo kod orqali sizga\n<b>1 oylik 👑 Premium obuna — 0 UZS</b> ga\nmuvaffaqiyatli taqdim etildi!\n\n✅ <b>Obuna holati:</b> Faol (30 kun)\n💳 <b>To'lov summasi:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>0 UZS</b>\n\n📌 <i>Premium obunangiz tafsilotlarini ko'rish uchun /premium buyrug'ini yuboring.</i>\n🙏 <i>Botimizdan foydalanganingiz uchun rahmat!</i>{CONTACT_FOOTER}"), parse_mode='HTML')
                await _notify_admin_promo_100(message.bot, user_id, uname, code)
                return
            elif disc_pct > 0:
                p_1w_base = await db_req.get_premium_price_1w()
                p_1m_base = await db_req.get_premium_price_1m()
                p_3m_base = await db_req.get_premium_price_3m()
                p_6m_base = await db_req.get_premium_price_6m()
                p_1y_base = await db_req.get_premium_price_1y()
                p_1w = int(p_1w_base * (100 - disc_pct) / 100)
                p_1m = int(p_1m_base * (100 - disc_pct) / 100)
                p_3m = int(p_3m_base * (100 - disc_pct) / 100)
                p_6m = int(p_6m_base * (100 - disc_pct) / 100)
                p_1y = int(p_1y_base * (100 - disc_pct) / 100)
                msg = f"✅ <b>PROMO KOD MUVAFFAQIYATLI ISHLATILDI!</b> 🎉\n\n🏷️ <b>Sizga {disc_pct}% SKIDKA taqdim etildi!</b>\n\n💰 <b>SKIDKADAGI YANGI NARXLARINGIZ:</b>\n1️⃣ <b>1 haftalik:</b> <s>{fmt_price(p_1w_base)}</s> ➔ <b>{fmt_price(p_1w)}</b>\n2️⃣ <b>1 oylik:</b> <s>{fmt_price(p_1m_base)}</s> ➔ <b>{fmt_price(p_1m)}</b>\n3️⃣ <b>3 oylik:</b> <s>{fmt_price(p_3m_base)}</s> ➔ <b>{fmt_price(p_3m)}</b>\n4️⃣ <b>6 oylik:</b> <s>{fmt_price(p_6m_base)}</s> ➔ <b>{fmt_price(p_6m)}</b>\n5️⃣ <b>1 yillik:</b> <s>{fmt_price(p_1y_base)}</s> ➔ <b>{fmt_price(p_1y)}</b>\n\n👉 To'lovni amalga oshirish va obunani faollashtirish uchun /premium buyrug'ini yuboring!"
            else:
                msg = f"✅ <b>PROMO KOD MUVAFFAQIYATLI ISHLATILDI!</b> 🎉\n\n{msg}\n\n👉 Obuna va ballaringizni tekshirish uchun /premium buyrug'ini yuboring!"
        await message.answer(with_footer(msg), parse_mode='HTML')
    else:
        await state.set_state(UserStates.waiting_for_promo_code_input)
        await message.answer(with_footer('🏷️ <b>Promo kodingizni kiriting:</b>'), parse_mode='HTML')

async def _notify_admin_promo_100(bot, user_id: int, uname: str, code: str):
    """Admin(lar)ga 100% promo kod ishlatilgani haqida xabarnoma yuborish"""
    import config
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⚠️ Ogohlantirish', callback_data=f'prem_warn_{user_id}'), InlineKeyboardButton(text='🚫 Bloklash', callback_data=f'prem_ban_{user_id}')], [InlineKeyboardButton(text='❌ Premiumni bekor qilish', callback_data=f'prem_remove_{user_id}')]])
    text = f"🔔 <b>100% PROMO KOD ISHLATILDI!</b>\n\n👤 <b>Foydalanuvchi:</b> {uname} (<code>{user_id}</code>)\n🏷️ <b>Promo kod:</b> <code>{code}</code>\n🎁 <b>Berilgan imtiyoz:</b> 1 oylik Premium — 0 UZS\n\n⚙️ Agar bu shubhali faoliyat bo'lsa, quyidagi tugmalar orqali chora ko'ring:"
    for admin_id in config.ADMINS:
        try:
            await bot.send_message(with_footer(admin_id), text, parse_mode='HTML', reply_markup=kb)
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
            await _notify_admin_promo_auto_deleted(message.bot, auto_del['code'], auto_del['used'], auto_del['max'])
        if disc_pct == 100:
            await db_req.set_user_premium(user_id, days=30)
            await db_req.consume_user_discount(user_id)
            user_info = message.from_user
            uname = f'@{user_info.username}' if user_info.username else user_info.full_name
            p_1m_base = await db_req.get_premium_price_1m()
            await message.answer(with_footer(f"🎉 <b>TABRIKLAYMIZ!</b>\n\n🏷️ Siz kiritgan promo kod orqali sizga\n<b>1 oylik 👑 Premium obuna — 0 UZS</b> ga\nmuvaffaqiyatli taqdim etildi!\n\n✅ <b>Obuna holati:</b> Faol (30 kun)\n💳 <b>To'lov summasi:</b> <s>{p_1m_base:,} UZS</s> ➔ <b>0 UZS</b>\n\n📌 <i>Premium obunangiz tafsilotlarini ko'rish uchun /premium buyrug'ini yuboring.</i>\n🙏 <i>Botimizdan foydalanganingiz uchun rahmat!</i>{CONTACT_FOOTER}"), parse_mode='HTML')
            await _notify_admin_promo_100(message.bot, user_id, uname, code)
            return
        if disc_pct > 0:
            p_1w_base = await db_req.get_premium_price_1w()
            p_1m_base = await db_req.get_premium_price_1m()
            p_3m_base = await db_req.get_premium_price_3m()
            p_6m_base = await db_req.get_premium_price_6m()
            p_1y_base = await db_req.get_premium_price_1y()
            p_1w = int(p_1w_base * (100 - disc_pct) / 100)
            p_1m = int(p_1m_base * (100 - disc_pct) / 100)
            p_3m = int(p_3m_base * (100 - disc_pct) / 100)
            p_6m = int(p_6m_base * (100 - disc_pct) / 100)
            p_1y = int(p_1y_base * (100 - disc_pct) / 100)

            def _fmt(n):
                return fmt_price(n)
            detail_msg = f"✅ <b>PROMO KOD QABUL QILINDI!</b> 🎉\n\n🏷️ <b>Sizga to'lov uchun {disc_pct}% SKIDKA taqdim etildi!</b>\n\n💰 <b>SKIDKADAGI YANGI NARXLARINGIZ:</b>\n1️⃣ <b>1 haftalik:</b> <s>{_fmt(p_1w_base)}</s> ➔ <b>{_fmt(p_1w)}</b>\n2️⃣ <b>1 oylik:</b> <s>{_fmt(p_1m_base)}</s> ➔ <b>{_fmt(p_1m)}</b>\n3️⃣ <b>3 oylik:</b> <s>{_fmt(p_3m_base)}</s> ➔ <b>{_fmt(p_3m)}</b>\n4️⃣ <b>6 oylik:</b> <s>{_fmt(p_6m_base)}</s> ➔ <b>{_fmt(p_6m)}</b>\n5️⃣ <b>1 yillik:</b> <s>{_fmt(p_1y_base)}</s> ➔ <b>{_fmt(p_1y)}</b>\n\n📌 <i>Istalgan vaqtda qayta ko'rish uchun /premium buyrug'idan foydalanishingiz mumkin!</i>\n\n👇 To'lov qilish uchun quyidagi obuna planlaridan birini tanlang:"
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'1️⃣ 1 haftalik - {_fmt(p_1w)}', callback_data='premium_1w'), InlineKeyboardButton(text=f'2️⃣ 1 oylik - {_fmt(p_1m)}', callback_data='premium_monthly')], [InlineKeyboardButton(text=f'3️⃣ 3 oylik - {_fmt(p_3m)}', callback_data='premium_quarterly'), InlineKeyboardButton(text=f'4️⃣ 6 oylik - {_fmt(p_6m)}', callback_data='premium_6m')], [InlineKeyboardButton(text=f'5️⃣ 1 yillik - {_fmt(p_1y)}', callback_data='premium_yearly')], [InlineKeyboardButton(text="📞 Manual to'lov", callback_data='premium_manual')]])
            await message.answer(with_footer(detail_msg), parse_mode='HTML', reply_markup=kb)
            return
        conf_msg = f"✅ <b>PROMO KOD MUVAFFAQIYATLI ISHLATILDI!</b> 🎉\n\n{msg}\n\n📌 <i>Imtiyoz va obuna ma'lumotlarini ko'rish uchun /premium buyrug'ini yuboring.</i>"
        await message.answer(with_footer(conf_msg), parse_mode='HTML')
    else:
        await message.answer(with_footer(f"{msg}\n\n<i>Qayta urinib ko'rish uchun /premium yoki promo kodni qayta kiriting.</i>"), parse_mode='HTML')

@router.callback_query(F.data.in_(['premium_1w', 'premium_monthly', 'premium_quarterly', 'premium_6m', 'premium_1y', 'premium_yearly']))
async def select_plan_payment_method(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data
    user_id = callback.from_user.id
    plan_info = PREMIUM_PLANS.get(plan_key)
    if not plan_info:
        return

    discount_pct = await db_req.get_user_active_discount(user_id)
    is_repeat = await db_req.has_user_bought_premium_before(user_id)
    
    if plan_key == 'premium_1w':
        base_price = await db_req.get_premium_price_1w()
    elif plan_key == 'premium_monthly':
        base_price = await db_req.get_premium_price_1m()
    elif plan_key == 'premium_quarterly':
        base_price = await db_req.get_premium_price_3m()
    elif plan_key == 'premium_6m':
        base_price = await db_req.get_premium_price_6m()
    else:
        base_price = await db_req.get_premium_price_1y()

    if discount_pct > 0:
        card_price = max(1000, int(base_price * (100 - discount_pct) / 100) // 1000 * 1000)
        card_label = f"{card_price:,} UZS ({discount_pct}% skidka)"
    elif is_repeat:
        card_price = max(1000, int(base_price * 0.85) // 1000 * 1000)
        card_label = f"{card_price:,} UZS (15% chegirma)"
    else:
        card_price = base_price
        card_label = f"{card_price:,} UZS"

    stars_price = plan_info['stars']

    bonus_badge = ""
    if plan_info['days'] >= 365:
        bonus_badge = "\n🎁 <b>SUPER BONUS:</b> 1 Yillik VIP xaridi uchun do'stingizga sovg'a qilish uchun <b>1 oylik (30 kunlik) bepul VIP promo kodi</b> sovg'a qilinadi! 🎉\n"

    txt = (
        f"👑 <b>{plan_info['name'].upper()} ({plan_info['days']} KUN)</b>\n\n"
        f"Iltimos, qulay to'lov usulini tanlang:\n\n"
        f"💳 <b>Karta (Click / Payme / Uzum):</b> <code>{card_label}</code>\n"
        f"⭐️ <b>Telegram Stars:</b> <code>{stars_price} Stars</code>\n"
        f"{bonus_badge}\n"
        f"<i>Eslatma: Telegram Stars orqali to'lov amalga oshirilganda VIP obuna 1 soniyada avtomatik faollashadi! ⚡</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Karta orqali to'lash ({card_label})", callback_data=f"pay_card_{plan_key}")],
        [InlineKeyboardButton(text=f"⭐️ Telegram Stars ({stars_price} ⭐️)", callback_data=f"pay_stars_{plan_key}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_premium")]
    ])

    await callback.message.edit_text(with_footer(txt), parse_mode='HTML', reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith('pay_card_'))
async def process_card_payment_cb(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data.replace('pay_card_', '')
    plan_info = PREMIUM_PLANS.get(plan_key, PREMIUM_PLANS['premium_monthly'])
    user_id = callback.from_user.id

    discount_pct = await db_req.get_user_active_discount(user_id)
    is_repeat = await db_req.has_user_bought_premium_before(user_id)
    card_text = await db_req.get_admin_card_number()
    card_display = db_req.format_user_card_display(card_text)

    if plan_key == 'premium_1w':
        base_price = await db_req.get_premium_price_1w()
    elif plan_key == 'premium_monthly':
        base_price = await db_req.get_premium_price_1m()
    elif plan_key == 'premium_quarterly':
        base_price = await db_req.get_premium_price_3m()
    elif plan_key == 'premium_6m':
        base_price = await db_req.get_premium_price_6m()
    else:
        base_price = await db_req.get_premium_price_1y()

    days = plan_info['days']
    plan_name = plan_info['name']
    plan_label = plan_info['label']

    if discount_pct > 0:
        final_price = max(1000, int(base_price * (100 - discount_pct) / 100) // 1000 * 1000)
        amount = f"{final_price:,} UZS ({discount_pct}% PROMO SKIDKA QO'LLANDI!)"
    elif is_repeat:
        final_price = max(1000, int(base_price * 0.85) // 1000 * 1000)
        amount = f"{final_price:,} UZS (🎉 15% TAKRORIY CHEGIRMA QO'LLANDI!)"
    else:
        final_price = base_price
        amount = f"{final_price:,} UZS"

    await state.set_state(UserStates.waiting_for_payment_receipt)
    await state.update_data(payment_plan=plan_name, payment_amount=amount, payment_raw_amount=final_price, payment_days=days, payment_label=plan_label)

    msg = (
        f"💳 <b>TO'LOV MA'LUMOTLARI ({plan_name}):</b>\n\n"
        f"To'lovni amalga oshirish uchun quyidagi kartaga to'lov qiling:\n\n"
        f"{card_display}\n\n"
        f"💵 <b>To'lov summasi:</b> <code>{amount}</code>\n\n"
        f"📌 <b>To'lov qilgach:</b> To'lov chekini (skrinshotini) shu yerning o'zida yuboring! To'lov tasdiqlangach Premium faollashtiriladi!"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔙 Orqaga', callback_data='back_to_premium')]])
    await callback.message.edit_text(with_footer(msg), parse_mode='HTML', reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith('pay_stars_'))
async def process_stars_payment_cb(callback: CallbackQuery):
    plan_key = callback.data.replace('pay_stars_', '')
    plan_info = PREMIUM_PLANS.get(plan_key, PREMIUM_PLANS['premium_monthly'])
    user_id = callback.from_user.id

    stars_amount = plan_info['stars']
    days = plan_info['days']
    plan_name = plan_info['name']

    prices = [LabeledPrice(label=f"👑 VIP ({days} kun)", amount=stars_amount)]

    try:
        await callback.message.answer_invoice(
            title=f"👑 VIP Premium — {plan_name}",
            description=f"Botdan barcha kinolarni cheklovlarsiz tomosha qilish uchun {days} kunlik VIP Premium obuna",
            payload=f"stars_vip_{days}_{stars_amount}_{user_id}",
            currency="XTR",
            prices=prices
        )
    except Exception as e:
        await callback.message.answer(with_footer(f"❌ Xatolik yuz berdi: {e}"), parse_mode='HTML')
    await callback.answer()


@router.pre_checkout_query()
async def stars_pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def stars_successful_payment_handler(message: Message):
    sp = message.successful_payment
    payload = sp.invoice_payload or ""
    parts = payload.split('_')
    if len(parts) >= 4 and parts[0] == 'stars' and parts[1] == 'vip':
        days = int(parts[2])
        stars_amount = int(parts[3])
    else:
        days = 30
        stars_amount = sp.total_amount

    user_id = message.from_user.id
    uname = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    await db_req.set_user_premium(user_id, days=days, plan=f"{days} kunlik VIP (Stars ⭐️)")

    await db_req.add_payment_record(
        user_id=user_id,
        amount=stars_amount,
        plan=f"⭐️ {stars_amount} Stars ({days} kun)",
        confirmed_by=0
    )

    # VIP Keshbek hisoblash va berish (Admin 14)
    cb_pct = await db_req.get_vip_cashback_percent()
    cashback_pts = max(1, int(days * cb_pct / 10))
    await db_req.add_points(user_id, cashback_pts)

    # 1 Yillik VIP olganga do'sti uchun 1 oylik bepul VIP promo kod sovg'asi (User 15)
    yearly_gift_extra = ""
    if days >= 365:
        gift_promo = await db_req.generate_yearly_vip_gift_promocode(user_id)
        yearly_gift_extra = (
            f"\n\n🎁 <b>MAXSUS YILLIK VIP SOVG'ASI!</b> 🎉\n"
            f"Siz 1 yillik VIP xarid qilganingiz uchun sizga do'stingizga sovg'a qilish uchun <b>1 oylik (30 kunlik) bepul VIP promo kodi</b> taqdim etiladi:\n\n"
            f"🎟 <b>Sizning promo kodingiz:</b> <code>{gift_promo}</code>\n"
            f"<i>(Ushbu kodni do'stingizga yuboring, u botga kirib promo kodni terishi bilan 1 oy VIP ga ega bo'ladi!)</i> 🍿"
        )

    await message.answer(
        with_footer(
            f"🎉 <b>TO'LOV QABUL QILINDI!</b> ⭐️\n\n"
            f"👑 <b>Sizga {days} kunlik VIP Premium obuna muvaffaqiyatli yoqildi!</b>\n\n"
            f"⭐️ <b>To'langan:</b> <code>{stars_amount} Stars</code>\n"
            f"🎁 <b>VIP Keshbek:</b> +{cashback_pts} 💎 ball hisobingizga qo'shildi!{yearly_gift_extra}\n\n"
            f"🍿 <i>Endi botdan barcha filmlarni hech qanday cheklovlarsiz tomosha qilishingiz mumkin!</i>"
        ),
        parse_mode='HTML'
    )

    admin_alert = (
        f"⭐️ <b>YANGI TELEGRAM STARS TO'LOVI!</b>\n\n"
        f"👤 <b>Foydalanuvchi:</b> {uname} (ID: <code>{user_id}</code>)\n"
        f"⭐️ <b>To'lov:</b> {stars_amount} Stars\n"
        f"👑 <b>Berilgan muddat:</b> {days} kun VIP\n"
        f"⚡ <i>Avtomatik faollashtirildi!</i>"
    )
    for admin_id in config.ADMINS:
        try:
            await message.bot.send_message(admin_id, with_footer(admin_alert), parse_mode='HTML')
        except Exception:
            pass


@router.callback_query(F.data == 'claim_vip_trial_cb')
async def claim_vip_trial_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    success, msg = await db_req.claim_vip_trial(user_id)
    if success:
        await callback.message.edit_text(with_footer(msg), parse_mode='HTML')
        uname = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        for admin_id in config.ADMINS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    with_footer(f"⏳ <b>1 SOATLIK BEPUL VIP SINOV OLINDI!</b>\n\n👤 {uname} (ID: <code>{user_id}</code>)"),
                    parse_mode='HTML'
                )
            except Exception:
                pass
    else:
        await callback.answer(msg, show_alert=True)
    await callback.answer()


@router.callback_query(F.data == 'back_to_premium')
async def back_to_premium_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_or_edit_premium_plans_menu(callback, callback.from_user.id, is_edit=True)
    await callback.answer()

@router.message(UserStates.waiting_for_payment_receipt, F.photo | F.document)
async def user_payment_receipt_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data.get('payment_plan', 'Premium')
    amount = data.get('payment_amount', '')
    days = data.get('payment_days', 30)
    plan_label = data.get('payment_label', '1 oylik')
    user = message.from_user
    username_disp = f'@{user.username}' if user.username else user.full_name or str(user.id)
    await state.clear()
    await message.answer(with_footer("✅ <b>To'lov chekingiz muvaffaqiyatli qabul qilindi!</b>\n\nAdminlarimiz chekni tekshirib chiqib, tez orada Premium obunangizni tasdiqlashadi. Rahmat! 🍿"), parse_mode='HTML')
    raw_amount = data.get('payment_raw_amount', 55000 if days == 90 else 20000)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'✅ {plan_label} Premium tasdiqlash', callback_data=f'admin_approve_prem_{user.id}_{days}_{raw_amount}')], [InlineKeyboardButton(text='❌ Xato chek', callback_data=f'admin_reject_receipt_{user.id}'), InlineKeyboardButton(text='⚠️ Ogohlantirish', callback_data=f'admin_warn_receipt_{user.id}')], [InlineKeyboardButton(text='🚫 Bloklash', callback_data=f'admin_ban_receipt_{user.id}')]])
    from datetime import datetime, timedelta
    uzb_now = datetime.utcnow() + timedelta(hours=5)
    formatted_time = uzb_now.strftime('%Y-%m-%d %H:%M')
    admin_txt = f"💳 <b>YANGI TO'LOV CHEKI KELDI!</b>\n\n👤 <b>Foydalanuvchi:</b> {username_disp} (ID: <code>{user.id}</code>)\n📋 <b>Plan:</b> {plan_name} ({amount})\n🕒 <b>Vaqt:</b> {formatted_time}"
    for admin_id in config.ADMINS:
        try:
            if message.photo:
                await message.bot.send_photo(admin_id, message.photo[-1].file_id, caption=with_footer(admin_txt), parse_mode='HTML', reply_markup=kb)
            elif message.document:
                await message.bot.send_document(admin_id, message.document.file_id, caption=admin_txt, parse_mode='HTML', reply_markup=kb)
        except Exception:
            pass

@router.message(F.text == 'Tanlanganlar ⭐️')
async def show_favorites(message: Message, state: FSMContext):
    await state.clear()
    favorites = await db_req.get_favorites(message.from_user.id)
    if not favorites:
        await message.answer(with_footer("❌ Siz hali hech qanday kino tanlanganlarga qo'shmadingiz."))
        return
    text = '⭐ <b>Sizning tanlangan kinolaringiz:</b>\n\n'
    for movie_id, caption in favorites:
        name = caption[:40] if caption else '(nomsiz)'
        text += f'🎬 /{movie_id} — {name}\n'
    text += '\nKinoni olish uchun uning kodini ustiga bosing.'
    await message.answer(with_footer(text))

@router.message(Command('random'))
@router.message(F.text.regexp('(?i).*(tasodifiy kino).*'))
async def random_movie(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    from database.connection import get_db
    async with get_db() as db:
        async with db.execute('SELECT id FROM movies') as cursor:
            all_ids = await cursor.fetchall()
    if not all_ids:
        await message.answer(with_footer("🎬 Botda hali kinolar qo'shilmagan."))
        return
    random_id = random.choice(all_ids)[0]
    movie = await db_req.get_movie(random_id, user_id=user_id)
    if movie:
        await db_req.add_to_watch_history(user_id, random_id)
        file_id, caption, *rest = movie
        views_count = rest[0] if rest else 1
        avg_rating, votes = await db_req.get_movie_rating(random_id)
        is_fav = await db_req.is_favorite(user_id, random_id)
        cap = f'{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{random_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿\n📥 <b>Yuklashlar:</b> {views_count:,} marta'
        if avg_rating > 0:
            cap += f'\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz)'
        cap += f'\n\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
        await message.answer_video(video=file_id, caption=with_footer(cap), parse_mode='HTML', protect_content=True, reply_markup=get_movie_action_keyboard(random_id, is_fav, avg_rating))
    else:
        await message.answer(with_footer(f'❌ Kino topilmadi (ID: {random_id}){CONTACT_FOOTER}'))

@router.message(F.text.regexp('(?i).*(reytinglar).*'))
async def show_user_leaderboard(message: Message, state: FSMContext):
    """Foydalanuvchilar uchun leaderboard"""
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏆 TOP 10 (Ballar)', callback_data='user_top_points'), InlineKeyboardButton(text='👥 TOP 10 (Referallar)', callback_data='user_top_referrals')], [InlineKeyboardButton(text='🔥 TOP 10 (Faollik)', callback_data='user_top_activity')]])
    await message.answer(with_footer("🏆 <b>Reytinglar - Leaderboard</b>\n\nQuyidagi bo'limlardan birini tanlang:"), parse_mode='HTML', reply_markup=keyboard)

@router.callback_query(F.data == 'user_top_points')
async def user_top_points(callback: CallbackQuery):
    """Ballar bo'yicha TOP 10"""
    top_users = await db_req.get_top_users_by_points(10)
    text = "🏆 <b>TOP 10 Foydalanuvchilar (Ballar bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, (user_id, username, full_name, points, referrals_count) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = username or full_name or f'User {user_id}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f'   💰 Ball: {points:,} | 👥 Referallar: {referrals_count}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='user_top_points')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='user_leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'user_top_referrals')
async def user_top_referrals(callback: CallbackQuery):
    """Referallar bo'yicha TOP 10"""
    top_users = await db_req.get_top_users_by_referrals(10)
    text = "👥 <b>TOP 10 Foydalanuvchilar (Referallar bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, (user_id, username, full_name, referrals_count, points) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = username or full_name or f'User {user_id}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f'   👥 Referallar: {referrals_count} | 💰 Ball: {points:,}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='user_top_referrals')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='user_leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'user_top_activity')
async def user_top_activity(callback: CallbackQuery):
    """Faollik bo'yicha TOP 10"""
    top_users = await db_req.get_top_users_by_activity(10)
    text = "🔥 <b>TOP 10 Foydalanuvchilar (Faollik bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, (user_id, username, full_name, last_active_at, points) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = username or full_name or f'User {user_id}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f'   ⏰ Oxirgi faollik: {last_active_at}\n'
        text += f'   💰 Ball: {points:,}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='user_top_activity')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='user_leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'user_leaderboard')
async def back_user_leaderboard(callback: CallbackQuery):
    """User leaderboard menyusiga qaytish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏆 TOP 10 (Ballar)', callback_data='user_top_points'), InlineKeyboardButton(text='👥 TOP 10 (Referallar)', callback_data='user_top_referrals')], [InlineKeyboardButton(text='🔥 TOP 10 (Faollik)', callback_data='user_top_activity')]])
    try:
        await callback.message.edit_text(with_footer("🏆 <b>Reytinglar - Leaderboard</b>\n\nQuyidagi bo'limlardan birini tanlang:"), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer("🏆 <b>Reytinglar - Leaderboard</b>\n\nQuyidagi bo'limlardan birini tanlang:"), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.message(F.text.regexp("(?i).*(kino so'rash).*"))
async def request_movie(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_for_movie_request)
    await message.answer(with_footer("🎬 <b>Kino so'rash:</b>\n\nQidirayotgan kinoning nomini yuboring:"), parse_mode='HTML')

@router.message(UserStates.waiting_for_movie_request, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def process_movie_request(message: Message, state: FSMContext):
    """Foydalanuvchining kino so'rovini qayta ishlash"""
    user_id = message.from_user.id
    movie_name = message.text
    await db_req.add_movie_request(user_id, movie_name)
    await state.clear()
    await message.answer(with_footer(f"✅ <b>So'rov qabul qilindi!</b>\n\n🎬 Kino: {movie_name}\n📊 Adminlar tez orada ko'rib chiqishadi.\n\n⏰ Kino qo'shilganda sizga xabar beramiz.{CONTACT_FOOTER}"), parse_mode='HTML')

@router.message(F.text.regexp('(?i).*(referal).*'))
async def show_referral_stats(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    bot_clean = config.BOT_USERNAME.lstrip('@')
    ref_link = f'https://t.me/{bot_clean}?start={user_id}'
    user_db = await db_req.get_user(user_id)
    referrals_count = user_db[5] if user_db and len(user_db) > 5 else 0
    top_referrers = await db_req.get_top_referrers()
    top_text = ''
    if top_referrers:
        top_text = "\n🏆 <b>Eng ko'p taklif qilgan TOP 10 a'zo:</b>\n"
        for idx, (uid, username, full_name, count) in enumerate(top_referrers, 1):
            name = f'@{username}' if username else full_name or str(uid)
            top_text += f"{idx}. 👤 {name} — <code>{count}</code> ta do'st\n"
    stats_text = f"📊 <b>Sizning referal statistikangiz:</b>\n\n👥 <b>Taklif qilingan a'zolar:</b> <code>{referrals_count}</code> ta\n🔗 <b>Sizning taklif havolangiz:</b>\n<code>{ref_link}</code>\n{top_text}\n👇 <b>Do'stlaringizga ulashish uchun:</b>\n\n🚀 Quyidagi tugmani bosing va do'stingizga yuboring!"
    import urllib.parse
    share_text = "🚀 Kino bot - ko'p kino, bepul, qulay!\n\nQuyidagi havola orqali kiring:"
    share_url = f'https://t.me/share/url?url={urllib.parse.quote(ref_link)}&text={urllib.parse.quote(share_text)}'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🚀 Botni boshlash', url=ref_link), InlineKeyboardButton(text='📤 Ulashish', url=share_url)]])
    await message.answer(with_footer(stats_text), parse_mode='HTML', reply_markup=keyboard)

@router.callback_query(F.data == 'ref_my_stats')
async def show_ref_stats_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_db = await db_req.get_user(user_id)
    referrals_count = user_db[5] if user_db and len(user_db) > 5 else 0
    top_referrers = await db_req.get_top_referrers()
    top_text = ''
    if top_referrers:
        top_text = '\n\n🏆 TOP 10 taklif qilganlar:\n'
        for idx, (uid, username, full_name, count) in enumerate(top_referrers[:5], 1):
            name = f'@{username}' if username else full_name or str(uid)
            top_text += f'{idx}. {name} — {count} ta\n'
    alert_text = f"📊 Sizning referal statistikangiz:\n\n👥 Taklif qilingan a'zolar: {referrals_count} ta{top_text}"
    await callback.answer(alert_text, show_alert=True)
USER_MENU_BUTTONS = [' Kino qidirish', 'Tanlanganlar ⭐️', 'Tasodifiy Kino 🎲', "Kino so'rash 🎬", '💎 Mening Ballarim', '🏆 Reytinglar', '👥 Referal', "🗳️ Kino so'rovlari", '⚙️ Sozlamalar']

@router.message(F.text.regexp('(?i).*(mening ballarim|ballarim).*'))
async def my_points(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    points = await db_req.get_points(user_id)
    leaderboard = await db_req.get_points_leaderboard(10)
    top_text = ''
    user_rank = None
    for idx, (uid, username, full_name, pts) in enumerate(leaderboard, 1):
        name = f'@{username}' if username else full_name or str(uid)
        top_text += f'{idx}. 👤 {name} — <code>{pts}</code> 💎\n'
        if uid == user_id:
            user_rank = idx
    rank_text = f"\n🏅 <b>Sizning o'rningiz:</b> {user_rank}-o'rin" if user_rank else ''
    text = f"💎 <b>Sizning ballaringiz: <code>{points}</code> 💎</b>\n\n📌 <b>Ball qanday yig'iladi?</b>\n⭐ Kino baholash → +2 💎\n💬 Izoh yozish → +3 💎\n👥 Do'st taklif qilish → +10 💎\n{rank_text}\n"
    kb = None
    if points >= 150:
        text += f'\n🎁 <b>MAXSUS TAKLIF (PROFFESIONAL REJIM):</b>\nSizda <b>{points} ball</b> bor! <b>150 ball</b> evaziga <b>👑 2 OYLIK PREMIUM VIP</b> maqomini ishga tushirishingiz mumkin!\n'
        builder = InlineKeyboardBuilder()
        builder.button(text='🎁 2 Oylik Premiumni Ishlatish (150 ball)', callback_data='redeem_150pts_premium')
        kb = builder.as_markup()
    if top_text:
        text += f"\n🏆 <b>TOP 10 ball yig'uvchilar:</b>\n{top_text}"
    await message.answer(with_footer(text), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'redeem_150pts_premium')
async def redeem_150pts_premium_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    success, msg = await db_req.redeem_150pts_for_2m_premium(user_id)
    if success:
        await callback.message.edit_text(with_footer(msg), parse_mode='HTML')
        await callback.answer('👑 2 Oylik Premium faollashtirildi! 🎉', show_alert=True)
    else:
        await callback.answer(msg, show_alert=True)

@router.message(F.text.regexp("(?i).*(kino so'rovlari).*"))
async def show_movie_requests(message: Message, state: FSMContext):
    await state.clear()
    requests = await db_req.get_top_movie_requests(limit=10)
    if not requests:
        await message.answer(with_footer("🗳️ <b>Hozircha hech qanday kino so'rovi yo'q.</b>\n\nBirinchi bo'lib <b>Kino so'rash 📥</b> orqali so'rov qoldiring!"), parse_mode='HTML')
        return
    text = "🗳️ <b>Eng ko'p so'ralgan kinolar:</b>\n\n"
    builder = InlineKeyboardBuilder()
    for idx, (req_id, movie_name, votes, user_id, created_at) in enumerate(requests, 1):
        text += f'{idx}. 🎬 <b>{movie_name}</b> — <code>{votes}</code> ovoz\n'
        builder.button(text=f'👍 {movie_name[:20]} ({votes})', callback_data=f'vote_req_{req_id}')
    builder.adjust(1)
    text += "\n<i>Kino nomiga bosing va ovoz bering! Ko'proq ovoz = tezroq qo'shiladi.</i>"
    await message.answer(with_footer(text), reply_markup=builder.as_markup(), parse_mode='HTML')

@router.callback_query(F.data.startswith('vote_req_'))
async def vote_movie_request_cb(callback: CallbackQuery):
    request_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    is_new_vote = await db_req.vote_movie_request(user_id, request_id)
    if is_new_vote:
        await callback.answer('✅ Ovozingiz qabul qilindi! +1 ovoz.', show_alert=True)
        try:
            requests = await db_req.get_top_movie_requests(limit=10)
            target = next((r for r in requests if r[0] == request_id), None)
            if target and callback.message.reply_markup:
                builder = InlineKeyboardBuilder()
                for req_id, movie_name, votes, uid, created_at in requests:
                    builder.button(text=f'👍 {movie_name[:20]} ({votes})', callback_data=f'vote_req_{req_id}')
                builder.adjust(1)
                await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
        except Exception:
            pass
    else:
        await callback.answer('❌ Siz bu kinoga allaqachon ovoz bergansiz!', show_alert=True)

@router.message(F.text.regexp('(?i).*(sozlamalar).*'))
async def show_settings(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    notify_pts = await db_req.get_user_notify_points(user_id)
    status_icon = '✅ Yoqilgan' if notify_pts else "❌ O'chirilgan"
    toggle_text = "🔕 O'chirish" if notify_pts else '🔔 Yoqish'
    text = f"⚙️ <b>Shaxsiy Sozlamalar</b>\n\n🔔 <b>Ball bildirishnomalari:</b> {status_icon}\n<i>(Kino baholash, izoh yozish va referal uchun olgan ballaringiz haqida xabar)</i>\n\nSozlamani o'zgartirish uchun quyidagi tugmani bosing:"
    builder = InlineKeyboardBuilder()
    builder.button(text=f'{toggle_text} — Ball bildirishnomalari', callback_data='toggle_notify_points')
    await message.answer(with_footer(text), reply_markup=builder.as_markup(), parse_mode='HTML')

@router.callback_query(F.data == 'toggle_notify_points')
async def toggle_notify_points_cb(callback: CallbackQuery):
    user_id = callback.from_user.id
    new_state = await db_req.toggle_user_notify_points(user_id)
    status_icon = '✅ Yoqilgan' if new_state else "❌ O'chirilgan"
    toggle_text = "🔕 O'chirish" if new_state else '🔔 Yoqish'
    text = f"⚙️ <b>Shaxsiy Sozlamalar</b>\n\n🔔 <b>Ball bildirishnomalari:</b> {status_icon}\n<i>(Kino baholash, izoh yozish va referal uchun olgan ballaringiz haqida xabar)</i>\n\nSozlamani o'zgartirish uchun quyidagi tugmani bosing:"
    builder = InlineKeyboardBuilder()
    builder.button(text=f'{toggle_text} — Ball bildirishnomalari', callback_data='toggle_notify_points')
    await callback.message.edit_text(with_footer(text), reply_markup=builder.as_markup(), parse_mode='HTML')
    state_msg = 'yoqildi ✅' if new_state else "o'chirildi ❌"
    await callback.answer(f'Ball bildirishnomalari {state_msg}', show_alert=False)

@router.callback_query(F.data.startswith('fav_toggle_'))
async def toggle_favorite(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    is_fav = await db_req.is_favorite(user_id, movie_id)
    if is_fav:
        await db_req.remove_favorite(user_id, movie_id)
        await callback.answer('Tanlanganlardan olib tashlandi ❌', show_alert=False)
    else:
        await db_req.add_favorite(user_id, movie_id)
        await callback.answer("Tanlanganlarga qo'shildi ⭐", show_alert=False)
    avg_rating, _ = await db_req.get_movie_rating(movie_id)
    new_is_fav = not is_fav
    await callback.message.edit_reply_markup(reply_markup=get_movie_action_keyboard(movie_id, new_is_fav, avg_rating))

@router.callback_query(F.data.startswith('rate_menu_'))
async def show_rating_menu(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
    await callback.message.edit_reply_markup(reply_markup=get_rating_keyboard(movie_id))
    await callback.answer()

@router.callback_query(F.data.startswith('movie_menu_'))
async def back_to_movie_menu(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
    movie = await db_req.get_movie(movie_id)
    if not movie:
        await callback.answer('Kino topilmadi ❌', show_alert=True)
        return
    file_id, caption = movie
    avg_rating, votes = await db_req.get_movie_rating(movie_id)
    is_fav = await db_req.is_favorite(callback.from_user.id, movie_id)
    rating_stars = '⭐' * round(avg_rating) if avg_rating else ''
    cap = f'{caption or ''}\n\n🎬 <b>Kino kodi:</b> <code>{movie_id}</code>'
    if avg_rating > 0:
        cap += f'\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}'
    cap += f'\n\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
    try:
        if callback.message.text is not None:
            await callback.message.edit_text(with_footer(cap), reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating), parse_mode='HTML')
        else:
            await callback.message.edit_caption(caption=cap, reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating), parse_mode='HTML')
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith('rate_') & ~F.data.startswith('rate_menu_'))
async def submit_rating(callback: CallbackQuery):
    parts = callback.data.split('_')
    movie_id = int(parts[1])
    rating = int(parts[2])
    daily_count = await db_req.get_daily_ratings_count(callback.from_user.id)
    if daily_count >= 10:
        await callback.answer('❌ Kuniga maksimal 10 ta kino baholash mumkin! Ertaga qaytib baholashingiz mumkin.', show_alert=True)
        return
    await db_req.add_rating(callback.from_user.id, movie_id, rating)
    await db_req.add_points(callback.from_user.id, 2)
    avg_rating, votes = await db_req.get_movie_rating(movie_id)
    is_fav = await db_req.is_favorite(callback.from_user.id, movie_id)
    stars = '⭐' * rating
    notify_pts = await db_req.get_user_notify_points(callback.from_user.id)
    remaining = 10 - (daily_count + 1)
    answer_text = f'Bahoyingiz qabul qilindi: {stars} (+2 💎 ball). Bugun yana {remaining} ta baholash qolgan!' if notify_pts else f'Bahoyingiz qabul qilindi: {stars}'
    await callback.answer(answer_text, show_alert=False)
    await callback.message.edit_reply_markup(reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating))

@router.callback_query(F.data.startswith('comments_list_'))
async def show_movie_comments(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
    comments = await db_req.get_comments(movie_id)
    movie = await db_req.get_movie(movie_id)
    movie_name = movie[1][:40] if movie and movie[1] else f'Kino {movie_id}'
    text = f'💬 <b>«{movie_name}» filmi uchun izohlar:</b>\n\n'
    if not comments:
        text += "<i>Hozircha hech qanday izoh yo'q. Birinchi bo'lib o'z fikringizni yozib qoldiring!</i>"
    else:
        from datetime import datetime, timezone, timedelta
        uzb_tz = timezone(timedelta(hours=5))
        now_dt = datetime.now(uzb_tz).replace(tzinfo=None)
        
        for idx, row in enumerate(comments[:15], 1):
            comment_text = row[0]
            username = row[1]
            full_name = row[2]
            created_at = row[3]
            prem_until = row[4] if len(row) > 4 else None
            
            is_vip = False
            if prem_until:
                try:
                    p_dt = datetime.fromisoformat(prem_until.replace(' ', 'T'))
                    if p_dt > now_dt:
                        is_vip = True
                except Exception:
                    pass
            
            badge = " 👑 <b>[VIP]</b>" if is_vip else ""
            name = f'@{username}' if username else (full_name or 'Foydalanuvchi')
            text += f'{idx}. <b>{name}</b>{badge}:\n└ <i>{comment_text}</i>\n\n'
    try:
        if callback.message.text is not None:
            await callback.message.edit_text(with_footer(text), reply_markup=get_comments_keyboard(movie_id), parse_mode='HTML')
        else:
            await callback.message.edit_caption(caption=text, reply_markup=get_comments_keyboard(movie_id), parse_mode='HTML')
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith('add_comment_start_'))
async def add_comment_start(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split('_')[3])
    await state.set_state(UserStates.waiting_for_comment)
    await state.update_data(comment_movie_id=movie_id)
    await callback.message.answer(with_footer("📝 <b>Ushbu kino uchun o'z fikringizni (izoh) yozib yuboring:</b>\n\n<i>Eslatma: Izoh uzunligi 3 dan 300 belgigacha bo'lishi kerak.</i>"), parse_mode='HTML')
    await callback.answer()

@router.message(UserStates.waiting_for_comment, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def add_comment_exec(message: Message, state: FSMContext):
    comment_text = message.text.strip()
    if len(comment_text) < 3:
        await message.answer(with_footer("⚠️ Izoh juda qisqa! Kamida 3 ta belgi bo'lishi lozim. Qayta yozing:"))
        return
    if len(comment_text) > 300:
        await message.answer(with_footer("⚠️ Izoh juda uzun! Maksimal 300 ta belgi bo'lishi lozim. Qayta yozing:"))
        return
    if db_req.contains_profanity(comment_text):
        await message.answer(with_footer("🚫 <b>Izohingizda nojo'ya so'zlar borligi aniqlandi!</b>\nIltimos, hurmatli so'zlar yozing."), parse_mode='HTML')
        await db_req.add_abuse_log(message.from_user.id, 'profanity', f'Comment: {comment_text[:50]}')
        return
    import re
    url_pattern = 'https?://[^\\s]+|www\\.[^\\s]+|t\\.me/[^\\s]+|@[\\w_]+'
    if re.search(url_pattern, comment_text):
        await message.answer(with_footer('🚫 <b>Izohlarda reklama havolalari taqiqlanadi!</b>\nIltimos, havolalarsiz izoh yozing.'), parse_mode='HTML')
        await db_req.add_abuse_log(message.from_user.id, 'spam_link', f'Comment: {comment_text[:50]}')
        return
    can_post, cooldown_msg = await db_req.can_post_comment(message.from_user.id)
    if not can_post:
        await message.answer(with_footer(cooldown_msg))
        return
    data = await state.get_data()
    movie_id = data['comment_movie_id']
    user = message.from_user
    is_first_comment = not await db_req.has_commented_on_movie(user.id, movie_id)
    await db_req.add_comment(user.id, movie_id, comment_text)
    points_added = 0
    if is_first_comment:
        added, limit_reached = await db_req.add_points(user.id, 3)
        points_added = added
    await state.clear()
    mod_setting = await db_req.get_config_int('comment_moderation', 0)
    notify_pts = await db_req.get_user_notify_points(user.id)
    if mod_setting == 1:
        confirm_text = "🛡 <b>Rahmat! Izohingiz saqlandi va moderatorlar tasdig'idan so'ng ko'rinadi.</b>"
    elif is_first_comment and points_added > 0:
        confirm_text = f'✅ <b>Rahmat! Izohingiz saqlandi. (+{points_added} 💎 ball)</b>' if notify_pts else '✅ <b>Rahmat! Izohingiz saqlandi.</b>'
    elif is_first_comment and points_added == 0:
        confirm_text = "✅ <b>Rahmat! Izohingiz saqlandi. (Kunlik ball limit to'lgan)</b>" if notify_pts else '✅ <b>Rahmat! Izohingiz saqlandi.</b>'
    else:
        confirm_text = '✅ <b>Rahmat! Izohingiz saqlandi.</b>'
    await message.answer(with_footer(confirm_text), parse_mode='HTML')
    movie = await db_req.get_movie(movie_id)
    movie_name = movie[1][:40] if movie and movie[1] else f'Kino {movie_id}'
    username_display = f'@{user.username}' if user.username else user.full_name
    admin_text = f'💬 <b>Kino uchun yangi izoh keldi!</b>\n\n🎬 <b>Kino:</b> {movie_name} (Kodi: <code>{movie_id}</code>)\n👤 <b>Foydalanuvchi:</b> {username_display} (ID: <code>{user.id}</code>)\n📝 <b>Izoh:</b>\n<i>{comment_text}</i>'
    for admin_id in config.ADMINS:
        try:
            await message.bot.send_message(with_footer(admin_id), admin_text, parse_mode='HTML')
        except Exception:
            pass

@router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    query = inline_query.query.strip()
    if query.isdigit():
        ref_user_id = int(query)
    else:
        ref_user_id = inline_query.from_user.id
    bot_clean = config.BOT_USERNAME.lstrip('@')
    ref_link = f'https://t.me/{bot_clean}?start={ref_user_id}'
    file_id = await db_req.get_setting('ref_promo_file_id')
    media_type = await db_req.get_setting('ref_promo_media_type')
    promo_caption = await db_req.get_setting('ref_promo_caption')
    if not promo_caption:
        promo_caption = '🚀 <b>Bizning bot orqali eng sara kinolarni tomosha qiling!</b>\n\n🍿 Har kuni yangi va qiziqarli filmlar!\n⚡ Botdan bepul foydalanish va qulay izlash.'
    caption = f'{promo_caption}\n\n🚀 {ref_link}'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📍 Boshlash:', url=f'https://t.me/{bot_clean}')]])
    inline_results = []
    if file_id and media_type:
        if media_type == 'video':
            inline_results.append(InlineQueryResultCachedVideo(id='promo', video_file_id=file_id, title='Taklif xabarini yuborish 🚀', caption=caption, reply_markup=keyboard, parse_mode='HTML'))
        elif media_type == 'photo':
            from aiogram.types import InlineQueryResultCachedPhoto
            inline_results.append(InlineQueryResultCachedPhoto(id='promo', photo_file_id=file_id, title='Taklif xabarini yuborish 🚀', caption=caption, reply_markup=keyboard, parse_mode='HTML'))
        else:
            from aiogram.types import InlineQueryResultCachedDocument
            inline_results.append(InlineQueryResultCachedDocument(id='promo', document_file_id=file_id, title='Taklif xabarini yuborish 🚀', caption=caption, reply_markup=keyboard, parse_mode='HTML'))
    else:
        from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
        inline_results.append(InlineQueryResultArticle(id='promo', title='Taklif xabarini yuborish 🚀', input_message_content=InputTextMessageContent(message_text=caption, parse_mode='HTML'), reply_markup=keyboard, description="Taklif havolasini do'stlaringizga yuboring"))
    await inline_query.answer(with_footer(inline_results), cache_time=5, is_personal=True)
    return
    if not query:
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
        avg_rating, votes = await db_req.get_movie_rating(movie_id)
        rating_text = f' | ⭐ {avg_rating:.1f} ({votes} ta ovoz)' if avg_rating > 0 else ''
        shared_caption = f'{movie_caption or ''}\n\n🎬 <b>Kino kodi:</b> <code>{movie_id}</code>\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
        inline_results.append(InlineQueryResultCachedVideo(id=str(movie_id), video_file_id=file_id, title=f'Kino kodi: {movie_id}', description=f'{(caption[:100] if caption else 'Tavsifsiz')}{rating_text}', caption=shared_caption, parse_mode='HTML'))
    await inline_query.answer(with_footer(inline_results), cache_time=10, is_personal=True)

@router.message(F.text == '🎁 Kunlik Bonus')
async def user_daily_bonus(message: Message, state: FSMContext):
    await state.clear()
    success, msg, pts = await db_req.claim_daily_bonus(message.from_user.id)
    await message.answer(with_footer(msg), parse_mode='HTML')

@router.message(F.text.regexp('(?i).*(saqlanganlar|tanlanganlar).*'))
async def user_favorites_list(message: Message, state: FSMContext):
    await state.clear()
    favs = await db_req.get_user_favorites(message.from_user.id)
    if not favs:
        await message.answer(with_footer("⭐️ <b>Sizda hali saqlangan kinolar yo'q.</b>\n\nKinolar ostidagi <b>«Tanlanganlarga qo'shish ⭐»</b> tugmasini bosib o'zingizga ma'qul kinolarni saqlab qo'yishingiz mumkin."), parse_mode='HTML')
        return
    text = f'⭐️ <b>Sizning saqlangan kinolaringiz ({len(favs)} ta):</b>\n\n'
    builder = InlineKeyboardBuilder()
    for movie_id, caption, _ in favs[:15]:
        title = caption[:30] if caption else f'Kino {movie_id}'
        text += f'🎬 <b>{movie_id}</b> — {title}\n'
        builder.button(text=f'🎬 {movie_id}', callback_data=f'show_movie_{movie_id}')
    builder.adjust(3)
    await message.answer(with_footer(text), parse_mode='HTML', reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith('fav_toggle_'))
async def toggle_favorite_callback(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
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
        await callback.message.edit_reply_markup(reply_markup=get_movie_action_keyboard(movie_id, new_fav, avg_rating))
    except Exception:
        pass
    await callback.answer(answer_msg, show_alert=True)

@router.callback_query(F.data.startswith('like_comm_'))
async def toggle_comment_like_callback(callback: CallbackQuery):
    comm_id = int(callback.data.split('_')[2])
    liked, count = await db_req.toggle_comment_like(comm_id, callback.from_user.id)
    status_txt = 'Like bosildi! ❤️' if liked else 'Like olib tashlandi 💔'
    await callback.answer(f'{status_txt} (Jami: {count})')

@router.callback_query(F.data == 'show_favorites_profile')
async def show_favorites_profile_cb(callback: CallbackQuery):
    favs = await db_req.get_user_favorites(callback.from_user.id)
    if not favs:
        await callback.answer("Sizda hali saqlangan kinolar yo'q.", show_alert=True)
        return
    text = f'⭐️ <b>Sizning saqlangan kinolaringiz ({len(favs)} ta):</b>\n\n'
    builder = InlineKeyboardBuilder()
    for movie_id, caption, _ in favs[:15]:
        title = caption[:30] if caption else f'Kino {movie_id}'
        text += f'🎬 <b>/{movie_id}</b> — {title}\n'
        builder.button(text=f'🎬 {movie_id}', callback_data=f'show_movie_{movie_id}')
    builder.adjust(3)
    await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=builder.as_markup())
    await callback.answer()

@router.message(Command('help'))
@router.message(F.text.regexp('(?i).*(yordam|murojaat).*'))
async def user_support_ticket_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserStates.waiting_for_support_ticket)
    await message.answer(with_footer("🆘 <b>Adminlarimiz bilan bog'lanish (Qo'llab-quvvatlash):</b>\n\nSavolingiz, murojaatingiz yoki taklifingiz bo'lsa, uni quyida yozib yuboring.\nAdminlarimiz xabaringizni ko'rib chiqib, sizga tez arada javob yuborishadi."), parse_mode='HTML')

@router.message(UserStates.waiting_for_support_ticket, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def user_support_ticket_save(message: Message, state: FSMContext):
    ticket_text = message.text.strip()
    user_id = message.from_user.id
    user_name = f'@{message.from_user.username}' if message.from_user.username else message.from_user.full_name or str(user_id)
    ticket_id = await db_req.create_ticket(user_id, ticket_text)
    await state.clear()
    from keyboards.inline import get_ticket_reply_keyboard
    admin_alert = f'🆘 <b>YANGI MUROJAAT / TICKET (#{ticket_id})</b>\n\n👤 <b>Foydalanuvchi:</b> {user_name} (ID: <code>{user_id}</code>)\n📝 <b>Matn:</b> <i>{ticket_text}</i>\n\nJavob berish uchun quyidagi tugmani bosing:'
    for admin_id in config.ADMINS:
        try:
            await message.bot.send_message(with_footer(admin_id), admin_alert, parse_mode='HTML', reply_markup=get_ticket_reply_keyboard(ticket_id))
        except Exception:
            pass
    await message.answer(with_footer(f"✅ <b>Murojaatingiz adminlarga yetkazildi! (Ticket #{ticket_id})</b>\n\nAdminlarimiz ko'rib chiqqach, javob ushbu bot orqali sizga yuboriladi."), parse_mode='HTML')

@router.message(Command('profile'))
@router.message(F.text.in_(['👑 Profilim', 'Profilim 👑', 'Profilim', 'Mening Profilim 👑', 'Mening Profilim']))
async def user_profile_card(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user = await db_req.get_user(user_id)
    if not user:
        await message.answer(with_footer('Foydalanuvchi topilmadi.'))
        return
    pts = user[6] if len(user) > 6 and user[6] is not None else 0
    ref_count = user[5] if len(user) > 5 and user[5] is not None else 0
    level_name, level_emoji, next_limit = db_req.get_user_level(pts)
    is_premium = await db_req.is_user_premium(user_id)
    status_str = '👑 VIP / Premium' if is_premium else 'Standard Foydalanuvchi'
    favs = await db_req.get_user_favorites(user_id)
    fav_count = len(favs) if favs else 0
    birthday = await db_req.get_user_birthday(user_id)
    bday_str = birthday if birthday else 'Kiritilmagan ❌'
    next_info = f'\n🎯 Keyingi daraja (VIP) uchun: <code>{next_limit - pts}</code> ball qoldi.' if next_limit is not None else ''
    txt = f"👑 <b>SHAXSIY PROFILINGIZ:</b>\n\n👤 <b>Foydalanuvchi:</b> {message.from_user.full_name}\n🆔 <b>ID:</b> <code>{user_id}</code>\n🌟 <b>Darajangiz:</b> {level_emoji} <b>{level_name}</b>\n💎 <b>To'plangan Ballar:</b> <code>{pts}</code> 💎{next_info}\n👥 <b>Chaqirgan Referallaringiz:</b> <code>{ref_count}</code> ta\n⭐️ <b>Saqlangan Kinolaringiz:</b> <code>{fav_count}</code> ta\n🎂 <b>Tug'ilgan Kuningiz:</b> <code>{bday_str}</code>\n🛡 <b>Maqomingiz:</b> {status_str}"
    from keyboards.inline import get_profile_extended_keyboard
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=get_profile_extended_keyboard())

@router.callback_query(F.data == 'show_watch_history')
async def show_watch_history_callback(callback: CallbackQuery):
    history = await db_req.get_watch_history(callback.from_user.id, limit=100)
    if not history:
        await callback.answer("Sizda hali ko'rilgan kinolar tarixi yo'q.", show_alert=True)
        return
    txt = f"🕒 <b>Ko'rilgan kinolarim tarixi (oxirgi {min(len(history), 100)} ta):</b>\n\n"
    builder = InlineKeyboardBuilder()
    for idx, (m_id, cap, w_at) in enumerate(history, 1):
        title = cap[:25] if cap else f'Kino {m_id}'
        txt += f'{idx}. 🎬 <b>/{m_id}</b> — {title} (<i>{w_at}</i>)\n'
        if idx <= 30:
            builder.button(text=f'🎬 {m_id}', callback_data=f'show_movie_{m_id}')
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(text='🧹 Tarixni tozalash', callback_data='clear_watch_history'),
        InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='home_menu')
    )
    await callback.message.answer(with_footer(txt), parse_mode='HTML', reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == 'clear_watch_history')
async def clear_watch_history_callback(callback: CallbackQuery):
    await db_req.clear_watch_history(callback.from_user.id)
    await callback.answer("✅ Ko'rilgan kinolar tarixi tozalandi!", show_alert=True)
    try:
        await callback.message.delete()
    except Exception:
        pass

@router.message(Command('top'))
@router.message(F.text.in_(['🔝 TOP Kinolar', 'TOP Kinolar 🔝', 'TOP Kinolar']))
async def user_top_movies_list(message: Message, state: FSMContext):
    await state.clear()
    await render_top_movies(message, page=1)

@router.callback_query(F.data.startswith('top_movies_page_'))
async def top_movies_page_callback(callback: CallbackQuery):
    page = int(callback.data.split('_')[3])
    await render_top_movies(callback.message, page=page, is_callback=True)
    await callback.answer()

@router.callback_query(F.data == 'show_top_movies_1')
async def show_top_movies_profile_callback(callback: CallbackQuery):
    await render_top_movies(callback.message, page=1, is_callback=True)
    await callback.answer()

async def render_top_movies(event: Message, page: int=1, is_callback: bool=False):
    top_movies = await db_req.get_top_rated_movies(limit=100)
    if not top_movies:
        txt = '🔝 <b>Hali baholangan kinolar mavjud emas.</b>'
        if is_callback:
            await event.edit_text(with_footer(txt), parse_mode='HTML')
        else:
            await event.answer(with_footer(txt), parse_mode='HTML')
        return
    per_page = 10
    total_pages = (len(top_movies) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = top_movies[start_idx:end_idx]
    txt = f'🔝 <b>ENG YUQORI BAHOLANGAN KINOLAR (TOP 100)</b>\n<i>Sahifa {page}/{total_pages}</i>\n\n'
    builder = InlineKeyboardBuilder()
    for rank, (m_id, cap, avg_r, votes, views) in enumerate(page_items, start_idx + 1):
        title = cap[:25] if cap else f'Kino {m_id}'
        stars = '⭐' * round(avg_r) if avg_r else ''
        txt += f'<b>#{rank}</b> 🎬 <b>/{m_id}</b> — {title}\n└ Reyting: <b>{avg_r:.1f}</b>/5 ({votes} ovoz) {stars}\n\n'
        builder.button(text=f'🎬 {m_id}', callback_data=f'show_movie_{m_id}')
    builder.adjust(3)
    from keyboards.inline import get_top_movies_keyboard
    nav_kb = get_top_movies_keyboard(page, total_pages)
    combined_builder = InlineKeyboardBuilder()
    for btn_row in builder.export():
        combined_builder.row(*btn_row)
    for btn_row in nav_kb.inline_keyboard:
        combined_builder.row(*btn_row)
    if is_callback:
        await event.edit_text(with_footer(txt), parse_mode='HTML', reply_markup=combined_builder.as_markup())
    else:
        await event.answer(with_footer(txt), parse_mode='HTML', reply_markup=combined_builder.as_markup())

@router.message(F.text.regexp("(?i).*(tug'ilgan kun).*"))
async def user_birthday_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    locked = await db_req.is_birthday_locked(user_id)
    existing_bday = await db_req.get_user_birthday(user_id)
    if locked or existing_bday:
        display = existing_bday if existing_bday and existing_bday != 'BLOCKED_UNDERAGE' else "❌ Belgilanmagan"
        await message.answer(with_footer(f"🎂 <b>Sizning saqlangan tug'ilgan kuningiz:</b> <code>{display}</code>\n\n🔒 <b>Diqqat:</b> Tug'ilgan kun ma'lumotlari <b>1 MARTAGINA</b> saqlanadi va keyinchalik o'zgartirib BO'LMAYDI!\n\n🎁 <b>Sovg'a (har yili shu kunda):</b>\n  • � 1 KUNLIK Premium\n  • � 100 ball\n  • 🎂 Maxsus stickerlar xabari\n\n<i>Biz bilan qoling! 🌟</i>{CONTACT_FOOTER}"), parse_mode='HTML')
        return
    await state.set_state(UserStates.waiting_for_birthday)
    await message.answer(with_footer("🎂 <b>Tug'ilgan kuningizni kiriting!</b>\n\nAgar botimizdan tug'ilgan kuningizda <b>MAXSUS SOVG'A</b> olmoqchi bo'lsangiz:\n\n🎁 <b>Sovg'a (har yili):</b>\n  • 👑 1 KUNLIK VIP Premium\n  • 💎 100 ball\n  • � Shaxsiy tabrik + stickerlar\n\n📅 <b>Format:</b> <code>KK.OO.YYYY</code>\n  <i>Masalan: 10.10.2013 (10-oktyabr 2013-yil)</i>\n\n⚠️ <b>JUDDAM AHMIYATLI:</b>\n  • Yosh kamida <b>12 da</b> bo'lishi kerak\n  • <b>1 MARTA</b> saqlanadi — keyin o'zgartirib BO'LMAYDI!\n  • Noto'g'ri ma'lumot → imkoniyat BUTUNLAY yo'qoladi!"), parse_mode='HTML')

@router.message(UserStates.waiting_for_birthday, F.text, ~F.text.in_(USER_MENU_BUTTONS))
async def user_birthday_save(message: Message, state: FSMContext):
    import re
    from datetime import datetime
    text = message.text.strip()
    user_id = message.from_user.id
    if await db_req.is_birthday_locked(user_id):
        await state.clear()
        await message.answer(with_footer("🔒 <b>Kechirasiz, tug'ilgan kun allaqachon 1 marta kiritilgan. O'zgartirib bo'lmaydi.</b>"))
        return
    if not re.match('^\\d{2}\\.\\d{2}\\.\\d{4}$', text):
        await message.answer(with_footer("⚠️ <b>Noto'g'ri format!</b>\n\nIltimos, <code>KK.OO.YYYY</code> formatida kiriting.\n<i>Masalan: 10.10.2013</i>"), parse_mode='HTML')
        return
    try:
        b_day, b_month, b_year = map(int, text.split('.'))
        birth_dt = datetime(year=b_year, month=b_month, day=b_day)
    except ValueError:
        await message.answer(with_footer("⚠️ <b>Mavjud bo'lmagan sana kiritildi!</b> Iltimos to'g'ri sana kiriting (Masalan: 10.10.2013):"), parse_mode='HTML')
        return
    now = datetime.now()
    if birth_dt > now:
        await message.answer(with_footer("⚠️ Tug'ilgan kun kelajakdagi sana bo'la olmaydi! Qayta kiriting:"))
        return
    age = now.year - birth_dt.year - ((now.month, now.day) < (birth_dt.month, birth_dt.day))
    if age < 12:
        await db_req.set_user_birthday(user_id, 'BLOCKED_UNDERAGE')
        await db_req.lock_user_birthday(user_id)
        await state.clear()
        await message.answer(with_footer(f"❌ <b>Uzr!</b> Botimizdan foydalanish va sovg'alar olish uchun yoshingiz kamida <b>12 da</b> bo'lishi kerak.\n\nSiz kiritgan sana bo'yicha yoshingiz <b>{age} da</b> bo'lgani sababli:\n  • Tug'ilgan kun saqlanmadi\n  • Qayta kiritish IMKONIYATI BERILMAYDI\n\nBu amal <b>1 MARTA</b> bajarildi va o'zgartirib bo'lmaydi.{CONTACT_FOOTER}"), parse_mode='HTML')
        return
    success = await db_req.set_user_birthday(user_id, text)
    await db_req.lock_user_birthday(user_id)
    await state.clear()
    if success:
        today_is_birthday = (now.month == b_month and now.day == b_day)
        extra = ""
        if today_is_birthday:
            from database.requests import add_premium_days, add_points_to_user
            try:
                await add_premium_days(user_id, "Tug'ilgan kun sovg'asi", 1)
            except Exception:
                pass
            try:
                await add_points_to_user(user_id, 100)
            except Exception:
                pass
            extra = f"\n\n🎉 <b>Aynan bugun sizning kuningiz!</b>\n  • 👑 1 kunlik Premium: <b>BERILDI ✅</b>\n  • 💎 100 ball: <b>BERILDI ✅</b>\n  • 🎂 Maxsus tabrik: <b>Tayyor! ✅</b>"
            try:
                sticker_caps = [
                    "🎂🎉🎈 HAPPY BIRTHDAY! 🎈🎉🎂",
                    "🎁✨ Siz uchun maxsus sovg'alar! ✨🎁",
                    "🎊💝 Bu kunningiz baxtli o'tsin! 💝🎊"
                ]
                for sc in sticker_caps:
                    try:
                        await message.bot.send_message(
                            chat_id=user_id,
                            text=f"<b>{sc}</b>\n\n🎂 <i>Sizni tug'ilgan kuningiz bilan chin dildan tabriklaymiz!\nSiz uchun maxsus sovg'alar tayyorlandi!</i>",
                            parse_mode='HTML'
                        )
                    except Exception:
                        pass
            except Exception:
                pass
        await message.answer(with_footer(f"🎉 <b>Tabriklaymiz! Tug'ilgan kuningiz ({text}) saqlandi!</b>\n\n🔒 <b>1 MARTAGINA qulflandi</b> — endi o'zgartirib bo'lmaydi.\n\n🎁 <b>Har yili ushbu kunda sizga:</b>\n  • 👑 1 KUNLIK Premium\n  • 💎 100 ball\n  • 🎂 Shaxsiy tabrik xabari{extra}"), parse_mode='HTML')
    else:
        await message.answer(with_footer("⚠️ Xatolik yuz berdi."))

@router.callback_query(F.data.startswith('show_movie_'))
async def show_movie_callback(callback: CallbackQuery):
    movie_id = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    movie = await db_req.get_movie(movie_id, user_id=user_id)
    if movie:
        file_id, caption, views_count, is_prem_only = (movie[0], movie[1], movie[2] if len(movie) > 2 else 0, movie[3] if len(movie) > 3 else 0)
        if is_prem_only and not (await db_req.is_premium_user(user_id)):
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Premium Obuna Sotib Olish", callback_data="sub_buy_premium")],
                [InlineKeyboardButton(text="⏳ 1 Soatlik Bepul VIP Sinov", callback_data="claim_vip_trial_cb")]
            ])
            txt = (
                f"🔒 <b>BU KINO FAQAT PREMIUM OBUNACHILAR UCHUN!</b> 👑\n\n"
                f"🎬 <b>Kino kodi:</b> /{movie_id}\n\n"
                f"Ushbu kinoni tomosha qilish uchun <b>VIP Premium</b> obunaga ega bo'lishingiz yoki <b>1 soatlik bepul VIP sinov</b>dan foydalanishingiz kerak! 🍿"
            )
            await callback.message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)
            await callback.answer("🔒 Faqat Premium obunachilar uchun!", show_alert=True)
            return

        await db_req.add_to_watch_history(user_id, movie_id)
        avg_rating, votes = await db_req.get_movie_rating(movie_id)
        is_fav = await db_req.is_favorite(user_id, movie_id)
        likes, dislikes, fires = await db_req.get_movie_reactions(movie_id)
        prem_badge = " [👑 VIP]" if is_prem_only else ""
        cap = f"{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}{prem_badge}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿\n📥 <b>Yuklashlar:</b> {views_count:,} marta"
        if avg_rating > 0:
            rating_stars = '⭐' * round(avg_rating) if avg_rating else ''
            cap += f'\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}'
        cap += f'\n\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
        await callback.message.answer_video(video=file_id, caption=with_footer(cap), parse_mode='HTML', reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating, likes, dislikes, fires))
        await _movie_watched_extra(user_id, caption)
        await callback.answer()
    else:
        await callback.answer('❌ Kino topilmadi', show_alert=True)

@router.message(Command('bonus'))
@router.message(F.text.regexp('(?i).*(kunlik bonus).*'))
async def user_daily_bonus(message: Message, state: FSMContext):
    await state.clear()
    success, msg, pts = await db_req.claim_daily_bonus(message.from_user.id)
    await message.answer(with_footer(msg), parse_mode='HTML')

@router.message(F.text, ~F.text.startswith('/'))
async def search_movie_by_text(message: Message, state: FSMContext=None):
    if state:
        current_state = await state.get_state()
        if current_state is not None:
            return
    query = message.text.strip()
    if query.isdigit() or query.lstrip('/').isdigit() or query.startswith(('http://', 'https://', 't.me/')) or ('://' in query):
        return
    if not query or len(query) < 2:
        await message.answer(with_footer('🔍 Kamida 2 ta belgi kiriting.'))
        return
    text_clean = query.lower().replace('️', '').strip()
    menu_keywords = ['qidirish', 'saqlanganlar', 'tanlanganlar', 'tasodifiy', "so'rash", 'ballarim', 'bonus', 'reytinglar', 'referal', "so'rovlari", 'sozlamalar', 'profilim', 'top kinolar', "tug'ilgan kun", 'yordam', 'murojaat', "kino qo'shish", "kino o'chirish", 'kino tahrirlash', 'statistika', 'reklama', 'kassa', 'audit', 'tahlili', 'bot rejimi', 'nofaollarga', 'promo', 'zaxira', 'moderatorlar', 'trendlari', 'shubhali', 'keshni', 'ommaviy']
    if any((kw in text_clean for kw in menu_keywords)):
        return
    import re, urllib.parse as _up
    ref_match = re.match('^@\\w+\\s+\\d+$', query.lower())
    ref_link_match = re.search('t\\.me/\\w+\\?start=(\\d+)', query)
    if ref_match or ref_link_match:
        sender_id = message.from_user.id
        if ref_link_match:
            ref_owner_id = int(ref_link_match.group(1))
        else:
            ref_owner_id = sender_id
        _bot_clean = config.BOT_USERNAME.lstrip('@')
        _ref_link = f'https://t.me/{_bot_clean}?start={sender_id}'
        _share_text = "🚀 Kino bot - ko'p kino, bepul, qulay!\n\nQuyidagi havola orqali kiring:"
        _share_url = f'https://t.me/share/url?url={_up.quote(_ref_link)}&text={_up.quote(_share_text)}'
        _file_id = await db_req.get_setting('ref_promo_file_id')
        _mtype = await db_req.get_setting('ref_promo_media_type')
        _caption_txt = await db_req.get_setting('ref_promo_caption')
        if not _caption_txt:
            _caption_txt = '🚀 <b>Bizning bot orqali eng sara kinolarni tomosha qiling!</b>\n\n🍿 Har kuni yangi va qiziqarli filmlar!\n⚡ Botdan bepul foydalanish va qulay izlash.'
        _cap = f'{_caption_txt}\n\n🚀 {_ref_link}'
        _kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📍 Boshlash:', url=f'https://t.me/{_bot_clean}')], [InlineKeyboardButton(text="Do'stlarga ulashish 🚀", url=_share_url)]])
        try:
            if _file_id and _mtype == 'video':
                await message.answer_video(video=_file_id, caption=with_footer(_cap), reply_markup=_kb, parse_mode='HTML')
            elif _file_id and _mtype == 'photo':
                await message.answer_photo(photo=_file_id, caption=with_footer(_cap), reply_markup=_kb, parse_mode='HTML')
            else:
                await message.answer(with_footer(_cap), reply_markup=_kb, parse_mode='HTML')
        except Exception:
            pass
        return
    inline_match = re.match('^@\\w+\\s+(\\d+)$', query)
    if inline_match:
        movie_id = int(inline_match.group(1))
        movie = await db_req.get_movie(movie_id)
        if movie:
            file_id, caption = movie
            avg_rating, votes = await db_req.get_movie_rating(movie_id)
            is_fav = await db_req.is_favorite(message.from_user.id, movie_id)
            rating_stars = '⭐' * round(avg_rating) if avg_rating else ''
            cap = f'{caption or ''}\n\n🎬 <b>Kino kodi:</b> /{movie_id}\n🖥 <b>Sifati:</b> 1080p Full HD 🍿'
            if avg_rating > 0:
                cap += f'\n⭐ <b>Reyting:</b> {avg_rating:.1f}/5 ({votes} ta ovoz) {rating_stars}'
            cap += f'\n\n🤖 {config.BOT_USERNAME}\n📩 <b>Murojaat uchun:</b> <a href="tg://user?id=8245305906">@Abdulaziz7o1</a>'
            await message.answer_video(video=file_id, caption=with_footer(cap), parse_mode='HTML', reply_markup=get_movie_action_keyboard(movie_id, is_fav, avg_rating))
        else:
            await message.answer(with_footer(f'❌ <b>{movie_id}</b> kodli kino topilmadi.{CONTACT_FOOTER}'))
        return
    results = await db_req.search_movies_by_name(query)
    if results:
        text = f"🔍 <b>'{query}' bo'yicha topilganlar:</b>\n\n"
        for movie_id, caption in results:
            name = caption[:40] if caption else '(nomsiz)'
            text += f'🎬 /{movie_id} — {name}\n'
        text += '\nKinoni olish uchun uning kodini ustiga bosing.'
        await message.answer(with_footer(text))
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
                    score = 1.0 - dist / max_len if max_len > 0 else 0.0
                if score > 0.3:
                    suggestions.append((score, movie_id, caption))
            suggestions.sort(key=lambda x: x[0], reverse=True)
            if suggestions:
                suggestion_text = f"❌ <b>'{query}'</b> nomli kino topilmadi.\n\n🤔 <b>Balki quyidagi kinolardan birini qidirgandirsiz?</b>\n\n"
                for score, movie_id, caption in suggestions[:3]:
                    name = caption[:45] if caption else '(nomsiz)'
                    suggestion_text += f'🎬 /{movie_id} — {name}\n'
                suggestion_text += "\nKo'rish uchun kino kodi ustiga bosing."
                await message.answer(with_footer(suggestion_text), parse_mode='HTML')
                return
        except Exception:
            pass
        from keyboards.inline import get_notify_request_keyboard
        await message.answer(with_footer(f"❌ <b>'{query}'</b> nomli kino topilmadi.\n\nIltimos, kino nomini to'g'ri yozing yoki quyidagi tugmalardan foydalaning:"),
                             parse_mode='HTML',
                             reply_markup=get_notify_request_keyboard(query))


# ─── 🔔 U10: KINO TOPILMAGANDA ESATMA SO'RASH ──────────────────────────────
@router.callback_query(F.data.startswith('notify_me_'))
async def cb_notify_me(callback: CallbackQuery):
    q = callback.data[len('notify_me_'):]
    ok = await db_req.add_movie_notify_request(callback.from_user.id, q)
    if ok:
        await callback.answer("✅ Saqlandi! Kino qo'shilganda sizga xabar beraman!", show_alert=True)
    else:
        await callback.answer("⚠️ Xatolik yuz berdi", show_alert=True)
    try:
        await callback.message.delete()
    except Exception:
        pass


# ─── 🏠 BOSH MENYU ───────────────────────────────────────────────────────────
@router.callback_query(F.data == 'home_menu')
async def cb_home_menu(callback: CallbackQuery):
    from keyboards.reply import get_user_menu, get_admin_menu, get_moderator_menu
    uid = callback.from_user.id
    user = callback.from_user
    name = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    db_admins = await db_req.get_all_admins()
    if uid in config.ADMINS:
        txt = f'👋 <b>Assalomu alaykum, Bosh Admin {name}!</b>\n\n🛠 Boshqaruv paneli'
        kb = get_admin_menu()
    elif uid in db_admins:
        txt = f'👋 <b>Assalomu alaykum, Moderator {name}!</b>\n\n🛠 Moderator paneli'
        kb = get_moderator_menu()
    else:
        txt = f'👋 <b>Assalomu alaykum, {name}!</b>\n\n🍿 Kino botiga xush kelibsiz!'
        kb = get_user_menu()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)
    await callback.answer()


# ─── 🎯 U1: JANR TAVSIYASI ───────────────────────────────────────────────────
@router.callback_query(F.data == 'show_recommendation')
async def cb_show_recommendation(callback: CallbackQuery):
    uid = callback.from_user.id
    movies = await db_req.recommend_movies_by_genre(uid, limit=10)
    if not movies:
        await callback.answer("❌ Hozircha siz uchun tavsiya yo'q. Ko'proq kino ko'ring! 🍿", show_alert=True)
        return
    txt = "🎯 <b>Sizga tavsiya etilgan kinolar:</b>\n\n"
    for idx, mv in enumerate(movies, 1):
        m_id, caption, views = mv
        name = (caption or 'Nomsiz').split('\n')[0][:50]
        txt += f"{idx}. 🎬 /{m_id} — {name} (👁 {views or 0})\n"
    txt += "\nKinoni ko'rish uchun kodi ustiga bosing."
    await callback.message.answer(with_footer(txt), parse_mode='HTML')
    await callback.answer()


# ─── 🔥 U9: HAFTALIK TOP 10 ───────────────────────────────────────────────────
@router.callback_query(F.data == 'show_weekly_top')
async def cb_show_weekly_top(callback: CallbackQuery):
    rows = await db_req.get_weekly_top_movies(limit=10)
    if not rows:
        await callback.answer("❌ Bu hafta hali reyting shakllanmagan.", show_alert=True)
        return
    txt = "🔥 <b>Bu hafta TOP 10 kinolar:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"] + [f"#{i}" for i in range(4, 11)]
    for idx, mv in enumerate(rows):
        m_id, caption, avg_r, cnt = mv
        medal = medals[idx] if idx < len(medals) else f"#{idx+1}"
        name = (caption or 'Nomsiz').split('\n')[0][:45]
        avg_str = f"{avg_r:.1f}" if avg_r else "0.0"
        txt += f"{medal} 🎬 /{m_id} — {name} ({avg_str}⭐, {cnt or 0} ovoz)\n"
    await callback.message.answer(with_footer(txt), parse_mode='HTML')
    await callback.answer()


# ─── 💳 U11: TO'LOVLAR TARIXI ────────────────────────────────────────────────
@router.callback_query(F.data == 'show_payment_history')
async def cb_show_payment_history(callback: CallbackQuery):
    uid = callback.from_user.id
    rows = await db_req.get_user_payment_history(uid, limit=20)
    if not rows:
        await callback.answer("❌ Sizda hali to'lovlar tarixi yo'q.", show_alert=True)
        return
    txt = "💳 <b>To'lovlar tarixim (oxirgi 20 ta):</b>\n\n"
    for idx, p in enumerate(rows, 1):
        pid, amount, plan, created, conf_by = p
        txt += f"{idx}. 💰 {amount:,} UZS — <i>{plan or 'Premium'}</i>\n   📅 {created or '?'}\n\n"
    await callback.message.answer(with_footer(txt), parse_mode='HTML')
    await callback.answer()


# ─── 👥 U13: REFERALLAR BATAFSIL (PAGINATION) ─────────────────────────────────
@router.callback_query(F.data == 'show_my_referrals_detailed')
async def cb_show_my_referrals(callback: CallbackQuery):
    await _render_referrals_page(callback, page=1, is_callback=True)

@router.callback_query(F.data.startswith('refs_page_'))
async def cb_referrals_page(callback: CallbackQuery):
    try:
        page = int(callback.data.split('_')[2])
    except Exception:
        page = 1
    await _render_referrals_page(callback, page=page, is_callback=True)

async def _render_referrals_page(event, page: int = 1, is_callback: bool = False):
    uid = event.from_user.id if hasattr(event, 'from_user') else event.message.from_user.id
    rows, total_count, total_pages = await db_req.get_user_referrals_detailed(uid, page=page, per_page=20)
    pending = await db_req.get_referrals_with_incomplete_sub(uid)
    page = max(1, min(page, total_pages))
    txt = f"👥 <b>Mening referallarim (Jami: {total_count} ta)</b>\n<i>Sahifa {page}/{total_pages}</i>\n\n"
    builder = InlineKeyboardBuilder()
    if rows:
        start_idx = (page - 1) * 20 + 1
        for idx, ref in enumerate(rows, start_idx):
            if len(ref) >= 9:
                rid, uname, fname, cat, rcount, pts, role, rewarded, prem = ref
            else:
                rid, uname, fname, cat, rcount, pts, role, rewarded = ref
                prem = None
            display = f"@{uname}" if uname else (fname or f"User {rid}")
            mark = "✅" if rewarded else "⏳"
            prem_mark = "👑" if prem else ""
            txt += f"{idx}. {display} {prem_mark} {mark}\n   📅 {cat} | 👥 ref: {rcount or 0} | 💎 pts: {pts or 0}\n"
    else:
        txt += "Hali referallingiz yo'q. Do'stlaringizni taklif qiling va sovg'alar oling! 🎁\n"
    if pending:
        txt += f"\n📩 <b>Obuna bo'lmaganlar ({len(pending)} ta):</b>\n"
        for p in pending[:5]:
            pid, puname, pfname, t = p
            d = f"@{puname}" if puname else (pfname or f"User {pid}")
            txt += f"  ⏳ {d} — {t}\n"
    if total_pages > 1:
        if page > 1:
            builder.button(text="⬅️ Oldingi", callback_data=f'refs_page_{page-1}')
        builder.button(text=f"📄 {page}/{total_pages}", callback_data='refs_page_dummy')
        if page < total_pages:
            builder.button(text="Keyingi ➡️", callback_data=f'refs_page_{page+1}')
        builder.adjust(3)
    builder.row(
        InlineKeyboardButton(text='🏠 Bosh menyu', callback_data='home_menu')
    )
    kb = builder.as_markup()
    msg_txt = with_footer(txt)
    target_msg = event.message if is_callback else event
    if is_callback:
        try:
            await target_msg.edit_text(msg_txt, parse_mode='HTML', reply_markup=kb)
        except Exception:
            await target_msg.answer(msg_txt, parse_mode='HTML', reply_markup=kb)
        await event.answer()
    else:
        await target_msg.answer(msg_txt, parse_mode='HTML', reply_markup=kb)


# ─── 🕒 KO'RILGAN KINOLAR GA JANR TRACK QO'SHISH ────────────────────────────
async def _movie_watched_extra(user_id: int, caption: str):
    """Kino ko'rilganda qo'shimcha: janrni track qilish"""
    try:
        await db_req.track_watch_genres(user_id, caption or "")
    except Exception:
        pass


@router.message(F.text == '🔥 Sizga mos kinolar')
async def cmd_user_recommendations(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    movies = await db_req.recommend_movies_by_genre(uid, limit=10)
    if not movies:
        await message.answer(with_footer("❌ <b>Hozircha siz uchun mos janrlar aniqlanmadi.</b>\n\nKo'proq kino ko'ring, shunda siz yoqtirgan janrlar bo'yicha saralangan kinolar shu yerda chiqadi! 🍿"), parse_mode='HTML')
        return
    txt = "🔥 <b>SIZGA MOS KINOLAR (JANR TAVSIYASI):</b>\n\n"
    for idx, mv in enumerate(movies, 1):
        m_id, caption, views = mv
        name = (caption or 'Nomsiz').split('\n')[0][:50]
        txt += f"{idx}. 🎬 /{m_id} — {name} (👁 {views or 0})\n"
    txt += "\n<i>Kinoni tomosha qilish uchun kodi (masalan /101) ustiga bosing.</i>"
    await message.answer(with_footer(txt), parse_mode='HTML')


@router.message(F.text == 'Tarixim 🕐')
async def cmd_user_watch_history(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    history = await db_req.get_watch_history(uid, limit=100)
    if not history:
        await message.answer(with_footer("🕐 <b>Sizda hali ko'rilgan kinolar tarixi mavjud emas.</b>\n\nKinolarni tomosha qilganingiz sari ular avtomatik shu yerda saqlanib boradi! 🍿"), parse_mode='HTML')
        return
    txt = f"🕐 <b>OXIRGI KO'RGAN KINOLARINGIZ ({len(history)} ta):</b>\n\n"
    for idx, (m_id, cap, watched_at) in enumerate(history[:30], 1):
        name = (cap or 'Nomsiz').split('\n')[0][:45]
        t_str = str(watched_at)[:16] if watched_at else ''
        txt += f"{idx}. 🎬 /{m_id} — {name}\n   🕒 <i>{t_str}</i>\n\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧹 Tarixni tozalash", callback_data="clear_my_watch_history")]])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)


@router.callback_query(F.data == "clear_my_watch_history")
async def cb_clear_watch_history(callback: CallbackQuery):
    uid = callback.from_user.id
    await db_req.clear_watch_history(uid)
    await callback.message.edit_text(with_footer("✅ <b>Ko'rilgan kinolar tarixingiz muvaffaqiyatli tozalandi!</b>"), parse_mode='HTML')
    await callback.answer()


@router.message(F.text.in_(['💳 To\'lovlarim', 'To\'lovlarim']))
async def cmd_user_payment_history(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    rows = await db_req.get_user_payment_history(uid, limit=20)
    if not rows:
        await message.answer(with_footer("💳 <b>Sizda hali to'lovlar tarixi yo'q.</b>\n\nPremium obuna sotib olganingizda barcha to'lovlar va muddatlar shu yerda ko'rinadi! 👑"), parse_mode='HTML')
        return
    txt = "💳 <b>SIZNING TO'LOVLARINGIZ TARIXI (oxirgi 20 ta):</b>\n\n"
    for idx, p in enumerate(rows, 1):
        pid, amount, plan, created, conf_by = p
        txt += f"{idx}. 💰 <b>{amount:,} UZS</b> — <i>{plan or 'Premium'}</i>\n   📅 {created or '?'}\n\n"
    await message.answer(with_footer(txt), parse_mode='HTML')

