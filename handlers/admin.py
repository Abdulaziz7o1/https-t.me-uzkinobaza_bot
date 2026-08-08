from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Filter, Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import os
import config
from database import requests as db_req
from keyboards import inline
router = Router()

CONTACT_FOOTER = "\n\n📩 <b>Murojaat uchun:</b> @Abdulaziz7o1"

def with_footer(text):
    if text is None:
        return text
    if not isinstance(text, str):
        return text
    if "@Abdulaziz7o1" in text or "Murojaat uchun" in text:
        return text
    return f"{text}{CONTACT_FOOTER}"


class IsAdminOrMod(Filter):

    async def __call__(self, message: Message) -> bool:
        if message.from_user.id in config.ADMINS:
            return True
        admins = await db_req.get_all_admins()
        return message.from_user.id in admins
router.message.filter(IsAdminOrMod())

class AdminStates(StatesGroup):
    waiting_for_movie_id = State()
    waiting_for_movie_video = State()
    waiting_for_movie_caption = State()
    waiting_for_movie_id_for_video = State()
    waiting_for_movie_delete = State()
    waiting_for_broadcast_msg = State()
    waiting_for_channel_id = State()
    waiting_for_channel_name = State()
    waiting_for_mod_id = State()
    waiting_for_movie_edit_id = State()
    waiting_for_movie_edit_caption = State()
    waiting_for_movie_replace_id = State()
    waiting_for_movie_replace_video = State()
    waiting_for_scheduled_broadcast_msg = State()
    waiting_for_scheduled_broadcast_time = State()
    waiting_for_referral_promo_video = State()
    waiting_for_referral_promo_caption = State()
    waiting_for_bulk_movies = State()
    waiting_for_config_value = State()
    waiting_for_bc_media = State()
    waiting_for_bc_caption = State()
    waiting_for_bc_button = State()
    waiting_for_bc_button_url = State()
    waiting_for_bc_button_title_after_url = State()
    waiting_for_bc_confirm = State()
    waiting_for_bc_target = State()
    waiting_for_ticket_reply = State()
    waiting_for_setpin = State()
    waiting_for_user_search = State()
    waiting_for_inactive_confirm = State()
    waiting_for_card_number = State()
    waiting_for_bonus_limit_value = State()
    waiting_for_promo_code = State()
    waiting_for_promo_type = State()
    waiting_for_promo_value = State()
    waiting_for_promo_uses = State()
    waiting_for_promo_edit_value = State()
    waiting_for_promo_edit_name = State()
    waiting_for_prem_price_1w = State()
    waiting_for_prem_price_1m = State()
    waiting_for_prem_price_3m = State()
    waiting_for_prem_price_6m = State()
    waiting_for_prem_price_1y = State()
    waiting_for_kassa_add_amount = State()
    waiting_for_backup_channel = State()
    waiting_for_manual_prem_amount = State()
    waiting_for_manual_prem_username_id = State()
    waiting_for_manual_prem_payment_amount = State()
    waiting_for_manual_prem_premium_type = State()
    waiting_for_manual_prem_period_until = State()
    waiting_for_manual_prem_expiration_date = State()
    waiting_for_manual_prem_purchase_date = State()

async def auto_post_movie_to_channel(bot, movie_id: int, file_id: str, caption: str):
    """Yangi kino joylanganda Zaxira (Backup) kanaliga video hamda kassa/baza ma'lumotlarini avtomatik yuborish"""
    try:
        backup_channel = await db_req.get_backup_channel_id()
        if backup_channel:
            cap = (
                f"🎬 <b>KINO ZAXIRA BAZASI</b>\n\n"
                f"📌 <b>Nomi / Tavsifi:</b> <i>{caption or '(Nomsiz kino)'}</i>\n"
                f"🎬 <b>Kino kodi:</b> <code>{movie_id}</code>\n"
                f"🖥 <b>Sifati:</b> 1080p Full HD 🍿\n\n"
                f"🤖 {config.BOT_USERNAME}\n"
                f"📩 <b>Murojaat uchun:</b> @Abdulaziz7o1"
            )
            await bot.send_video(
                chat_id=backup_channel,
                video=file_id,
                caption=cap,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Zaxira kanalga video yuborishda xato: {e}")
    await sync_movies_backup_storage(bot)

async def sync_movies_backup_storage(bot):
    """Har safar kino qo'shilganda yoki o'chirilganda Bosh Admin chatiga va Zaxira Kanaliga #MOVIES_BACKUP zaxira faylini yuboradi"""
    try:
        json_data = await db_req.export_movies_backup_json()
        backup_file_path = 'movies_backup.json'
        with open(backup_file_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        file = FSInputFile(backup_file_path)
        for admin_id in config.ADMINS:
            try:
                sent_msg = await bot.send_document(chat_id=admin_id, document=file, caption='💾 #MOVIES_BACKUP — Barcha kinolarning avtomatik bulutli zaxira fayli.')
                if sent_msg and sent_msg.document:
                    await db_req.save_telegram_backup_file_id(sent_msg.document.file_id)
            except Exception:
                pass

        backup_channel = await db_req.get_backup_channel_id()
        if backup_channel:
            try:
                b_file = FSInputFile(backup_file_path)
                sent_msg = await bot.send_document(chat_id=backup_channel, document=b_file, caption='💾 #MOVIES_BACKUP — Rasmiy Zaxira Kanali uchun avtomatik zaxira fayli.')
                if sent_msg and sent_msg.document:
                    await db_req.save_telegram_backup_file_id(sent_msg.document.file_id)
            except Exception as err:
                print(f"Zaxira kanalga zaxira fayli yuborishda xato: {err}")
    except Exception as e:
        print(f'Backup sync error: {e}')

def get_resolve_request_keyboard(request_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text='Bajarildi ✅', callback_data=f'resolve_req_{request_id}')
    return builder.as_markup()

def get_sponsor_channels_keyboard(channels: list):
    builder = InlineKeyboardBuilder()
    for db_id, ch_id, ch_name in channels:
        builder.button(text=f'❌ {ch_name}', callback_data=f'del_channel_{db_id}')
    builder.button(text="Yangi kanal qo'shish ➕", callback_data='add_channel_start')
    builder.adjust(1)
    return builder.as_markup()

def get_moderators_keyboard(mods: list):
    builder = InlineKeyboardBuilder()
    for user_id, username, full_name in mods:
        display_name = username or full_name or str(user_id)
        builder.button(text=f'❌ {display_name}', callback_data=f'del_mod_{user_id}')
    builder.button(text="Moderator qo'shish ➕", callback_data='add_mod_start')
    builder.adjust(1)
    return builder.as_markup()

def get_admin_list_keyboard(mods: list):
    """Boshqarish ⚙️ — Moderatorlar ro'yxati (har birini bosish settings ochiladigan)"""
    builder = InlineKeyboardBuilder()
    for user_id, username, full_name in mods:
        display_name = f'@{username}' if username else full_name or str(user_id)
        builder.button(text=f'👤 {display_name}', callback_data=f'mod_settings_{user_id}')
    builder.adjust(1)
    return builder.as_markup()

def get_mod_perms_keyboard(user_id: int, perms: dict):
    """Moderator ruxsatnomalari (toggle ✅/❌)"""
    perm_labels = {'add_movie': "Kino qo'shish ➕", 'delete_movie': "Kino o'chirish ❌", 'view_stats': 'Statistika 📊', 'send_broadcast': 'Reklama yuborish 📢', 'manage_sponsors': 'Homiy Kanallar 📢', 'view_trends': 'Kino Trendlari 📈', 'backup_db': 'Zaxira (Backup) 💾'}
    builder = InlineKeyboardBuilder()
    for key, label in perm_labels.items():
        icon = '✅' if perms.get(key) else '❌'
        builder.button(text=f'{icon} {label}', callback_data=f'toggleperm_{user_id}_{key}')
    builder.button(text='🔙 Orqaga', callback_data='boshqarish_back')
    builder.adjust(1)
    return builder.as_markup()

@router.message(CommandStart(), StateFilter('*'))
@router.message(Command('start'), StateFilter('*'))
async def admin_start_handler(message: Message, state: FSMContext):
    await state.clear()
    from handlers.user import execute_start_logic
    await execute_start_logic(message, state)

@router.message(F.document, F.document.file_name.endswith('.json'))
async def admin_restore_json_backup(message: Message):
    if message.from_user.id not in config.ADMINS:
        return
    try:
        file_id = message.document.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        downloaded_file = await message.bot.download_file(file_path)
        content = downloaded_file.read().decode('utf-8')
        stats = await db_req.import_master_backup_json(content)
        m_cnt = stats.get('movies', 0)
        ch_cnt = stats.get('sponsor_channels', 0)
        set_cnt = stats.get('settings', 0)
        with open('master_bot_backup.json', 'w', encoding='utf-8') as f:
            f.write(content)
        txt = f"✅ <b>MASTER ZAXIRA FAYLI MUVAFFAQIYATLI TIKLANDI!</b> 🚀\n\n🎬 <b>Kinolar:</b> {m_cnt} ta\n📢 <b>Homiy kanallar:</b> {ch_cnt} ta\n⚙️ <b>Sozlamalar va Kassa:</b> {set_cnt} ta\n\n<i>Barcha 15 ta ma'lumotlar jadvallari SQLite bazasiga va xotiraga 100% tiklandi!</i>"
        await message.answer(with_footer(txt), parse_mode='HTML')
    except Exception as e:
        await message.answer(with_footer(f'❌ Zaxirani tiklashda xato yuz berdi: {e}'))

@router.message(Command('backup'))
@router.message(F.text == '💾 Baza zaxirasi')
@router.message(F.text == 'Zaxira (Backup) 💾')
async def send_movies_backup_to_admin(message: Message):
    if message.from_user.id not in config.ADMINS and (not await db_req.has_permission(message.from_user.id, 'backup_db')):
        return
    json_data = await db_req.export_master_backup_json()
    backup_file_path = 'master_bot_backup.json'
    with open(backup_file_path, 'w', encoding='utf-8') as f:
        f.write(json_data)
    file = FSInputFile(backup_file_path)
    caption_txt = f"💾 <b>BOTNING FULL MASTER ZAXIRA FAYLI (Backup).</b>\n\nUshbu `.json` faylda barcha kinolar, homiy kanallar, ballar, kassa, promo kodlar va sozlamalar 100% jamlangan!\n\n📌 <b>Tiklash usuli:</b> Render restart bo'lganda bot avtomatik tiklaydi yoki ushbu faylni botga shunchaki yuborsangiz 100% qayta tiklaydi!"
    await message.answer_document(document=file, caption=caption_txt, parse_mode='HTML')

@router.message(F.text == 'Statistika 📊')
async def get_bot_statistics(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'view_stats'):
        return
    stats = await db_req.get_stats()
    inactive_count = await db_req.get_inactive_users_count(6)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🧹 Nofaol a'zolarni tozalash ({inactive_count} ta)", callback_data='clean_inactive_start')]])
    await message.answer(with_footer(f"📊 <b>Bot Statistikasi:</b>\n\n👥 Barcha a'zolar: {stats['users']} ta\n🚫 Bloklanganlar (ban): {stats['banned']} ta\n🎬 Kinolar soni: {stats['movies']} ta\n💤 Nofaol a'zolar (6 oydan ko'p kirmagan): {inactive_count} ta"), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'clean_inactive_start')
async def clean_inactive_users_callback(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer('❌ Faqat Bosh Adminlar tozalashi mumkin!', show_alert=True)
        return
    deleted_count = await db_req.delete_inactive_users(6)
    await callback.answer(f"Tozalash yakunlandi! {deleted_count} ta nofaol a'zolar o'chirildi. 🧹", show_alert=True)
    stats = await db_req.get_stats()
    await callback.message.edit_text(with_footer(f"📊 <b>Bot Statistikasi (Tozalangandan so'ng):</b>\n\n👥 Barcha a'zolar: {stats['users']} ta\n🚫 Bloklanganlar (ban): {stats['banned']} ta\n🎬 Kinolar soni: {stats['movies']} ta\n💤 Nofaol a'zolar: 0 ta"), parse_mode='HTML')

@router.message(F.text.regexp("(?i).*(kino qo'shish|add movie).*"))
async def add_movie_start(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    next_free = await db_req.get_next_available_movie_id()
    await state.set_state(AdminStates.waiting_for_movie_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'⚡ Avto-kod ({next_free}) ni tanlash', callback_data=f'auto_select_code_{next_free}')]])
    await message.answer(with_footer(f"📥 <b>KINO QO'SHISH REJIMI</b>\n\n💡 <b>Ushbu kino uchun nechinchi kod berasiz?</b>\n<i>Tavsiya etilgan eng birinchi bo'sh kod:</i> <b>{next_free}</b>\n\nIstalgan kod raqamini matn shaklida yuboring (masalan: <code>{next_free}</code> yoki <code>501</code>), YOKI to'g'ridan-to'g'ri video faylingizni yuboring:"), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('auto_select_code_'))
async def auto_select_code_callback(callback: CallbackQuery, state: FSMContext):
    code_val = int(callback.data.split('_')[-1])
    await state.update_data(movie_id=code_val)
    await state.set_state(AdminStates.waiting_for_movie_video)
    await callback.message.edit_text(with_footer(f'✅ <b>Kino kodi tanlandi: {code_val}</b>\n\n🎬 Endi kino video faylini yuboring:'), parse_mode='HTML')
    await callback.answer(f'Kod {code_val} tanlandi ✅')

@router.message(AdminStates.waiting_for_movie_id, F.text)
async def add_movie_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if text in MENU_BUTTONS:
        await state.clear()
        return
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat sonlardan iborat kino kodini kiriting!'))
        return
    movie_id = int(text)
    exists = await db_req.movie_exists_db(movie_id)
    if exists:
        next_free = await db_req.get_next_available_movie_id()
        await message.answer(with_footer(f"❌ <b>{movie_id}</b> kodli kino allaqachon mavjud!\n\n💡 Bo'sh bo'lgan navbatdagi kod: <code>{next_free}</code>\nIltimos, boshqa kod kiriting:"), parse_mode='HTML')
        return
    await state.update_data(movie_id=movie_id)
    await state.set_state(AdminStates.waiting_for_movie_video)
    await message.answer(with_footer(f'✅ <b>Kino kodi qabul qilindi: {movie_id}</b>\n\n🎬 Endi kino video faylini yuboring:'), parse_mode='HTML')

@router.message(StateFilter(None), F.video | F.document | F.animation | F.video_note)
@router.message(AdminStates.waiting_for_movie_id, F.video | F.document | F.animation | F.video_note)
async def admin_direct_video_handler(message: Message, state: FSMContext):
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    file_id = message.video.file_id if message.video else message.document.file_id if message.document else message.animation.file_id if message.animation else message.video_note.file_id
    raw_caption = (message.caption or '').strip()
    import re
    code_match = re.match('^(\\d+)\\s*[-:]?\\s*(.*)$', raw_caption, re.DOTALL)
    if code_match:
        target_id = int(code_match.group(1))
        candidate_cap = code_match.group(2).strip()
        exists = await db_req.movie_exists_db(target_id)
        if not exists:
            formatted_caption = db_req.clean_and_format_caption(candidate_cap)
            await db_req.add_movie_with_id(target_id, file_id, formatted_caption)
            await sync_movies_backup_storage(message.bot)
            total_movies = await db_req.get_total_movies_count()
            next_free = await db_req.get_next_available_movie_id()
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎬 Kinoni Ko'rish", callback_data=f'get_movie_{target_id}'), InlineKeyboardButton(text='✏️ Tahrirlash', callback_data=f'edit_movie_start_{target_id}')]])
            await message.answer(with_footer(f"✅ <b>KINO MUVAFFAQIYATLI SAQLANDI!</b>\n\n📌 <b>Nomi / Tavsifi:</b> <i>{(candidate_cap[:50] if candidate_cap else '(Nomsiz)')}</i>\n🎬 <b>Biriktirilgan Kod:</b> <code>{target_id}</code>\n📊 <b>Bazadagi jami kinolar:</b> <code>{total_movies} ta</code>\n💡 <b>Navbatdagi bo'sh kod:</b> <code>{next_free}</code>"), parse_mode='HTML', reply_markup=kb)
            await state.clear()
            return
    recommended_code = await db_req.get_next_available_movie_id()
    await state.update_data(direct_file_id=file_id, direct_caption=raw_caption, recommended_code=recommended_code)
    await state.set_state(AdminStates.waiting_for_movie_id_for_video)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'⚡ Avto-kod ({recommended_code}) bilan saqlash', callback_data=f'save_direct_auto_{recommended_code}')]])
    cap_display = raw_caption[:50] if raw_caption else '(Nomsiz video fayl)'
    await message.answer(with_footer(f"📥 <b>VIDEO FAYL QABUL QILINDI!</b>\n\n📌 <b>Nomi / Tavsifi:</b> <i>{cap_display}</i>\n\n💡 <b>Ushbu kino uchun nechinchi kod berasiz?</b>\n<i>Tavsiya etilgan bo'sh kod:</i> <b>{recommended_code}</b>\n\nSiz istalgan kod raqamini matn sifatida yuboring (masalan: <code>{recommended_code}</code> yoki <code>501</code>), YOKI quyidagi avto-kod tugmasini bosing:"), parse_mode='HTML', reply_markup=kb)

async def process_and_save_movie_with_code(event_obj, state: FSMContext, movie_id: int, file_id: str, raw_caption: str, is_callback: bool=False):
    try:
        exists = await db_req.movie_exists_db(movie_id)
        if exists:
            next_free = await db_req.get_next_available_movie_id()
            msg_txt = f"❌ <b>{movie_id}</b> kodli kino allaqachon bazada mavjud!\n\n💡 Bo'sh bo'lgan navbatdagi kod: <code>{next_free}</code>\nIltimos, boshqa kod kiriting (masalan: {next_free} yoki 501):"
            if is_callback:
                await event_obj.message.answer(with_footer(msg_txt), parse_mode='HTML')
                await event_obj.answer(with_footer('Kino allaqachon mavjud ⚠️'))
            else:
                await event_obj.answer(with_footer(msg_txt), parse_mode='HTML')
            return False
        formatted_caption = db_req.clean_and_format_caption(raw_caption)
        await db_req.add_movie_with_id(movie_id, file_id, formatted_caption)
        await state.clear()
        bot_inst = event_obj.bot
        # ✅ KANALGA VIDEO VA BACKUP FAYL YUBORISH
        await auto_post_movie_to_channel(bot_inst, movie_id, file_id, formatted_caption)
        await db_req.notify_requesting_users_for_movie(bot_inst, movie_id, formatted_caption)
        total_movies = await db_req.get_total_movies_count()
        next_free = await db_req.get_next_available_movie_id()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎬 Kinoni Ko'rish", callback_data=f'get_movie_{movie_id}'), InlineKeyboardButton(text='✏️ Tahrirlash', callback_data=f'edit_movie_start_{movie_id}')]])
        cap_display = raw_caption[:50] if raw_caption else '(Nomsiz video fayl)'
        confirm_txt = f"✅ <b>KINO BAZAGA MUVAFFAQIYATLI QO'SHILDI!</b>\n\n📌 <b>Kino nomi / tavsifi:</b> <i>{cap_display}</i>\n🎬 <b>Biriktirilgan Kod:</b> <code>{movie_id}</code>\n📊 <b>Bazadagi jami kinolar:</b> <code>{total_movies} ta</code>\n💡 <b>Navbatdagi bo'sh kod:</b> <code>{next_free}</code>\n\n☁️ <i>Kino SQLite hamda MongoDB Atlas Cloud bulutingizga 100% saqlandi!</i>"
        if is_callback:
            try:
                await event_obj.message.edit_text(with_footer(confirm_txt), parse_mode='HTML', reply_markup=kb)
            except Exception:
                await event_obj.message.answer(with_footer(confirm_txt), parse_mode='HTML', reply_markup=kb)
            await event_obj.answer(with_footer(f'Kino {movie_id} kodi bilan saqlandi ✅'))
        else:
            await event_obj.answer(with_footer(confirm_txt), parse_mode='HTML', reply_markup=kb)
        return True
    except Exception as e:
        import logging
        logging.error(f'process_and_save_movie_with_code error: {e}')
        if is_callback:
            await event_obj.answer(with_footer('❌ Xatolik yuz berdi!'), show_alert=True)
        else:
            await event_obj.answer(with_footer(f'❌ Xatolik yuz berdi: {e}'))
        return False

@router.message(StateFilter(AdminStates.waiting_for_movie_id_for_video, AdminStates.waiting_for_movie_id), F.text)
async def admin_save_direct_video_code(message: Message, state: FSMContext):
    text = message.text.strip()
    if text in MENU_BUTTONS or text.startswith('/'):
        await state.clear()
        if text == '/start' or text == '/cancel':
            from handlers.user import execute_start_logic
            await execute_start_logic(message, state)
        return
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat sonlardan iborat kino kodini kiriting (masalan: 1 yoki 501):'))
        return
    movie_id = int(text)
    data = await state.get_data()
    file_id = data.get('direct_file_id')
    raw_caption = data.get('direct_caption', '')
    if not file_id:
        exists = await db_req.movie_exists_db(movie_id)
        if exists:
            next_free = await db_req.get_next_available_movie_id()
            await message.answer(with_footer(f"❌ <b>{movie_id}</b> kodli kino allaqachon mavjud!\n\n💡 Bo'sh bo'lgan navbatdagi kod: <code>{next_free}</code>\nIltimos, boshqa kod kiriting:"), parse_mode='HTML')
            return
        await state.update_data(movie_id=movie_id)
        await state.set_state(AdminStates.waiting_for_movie_video)
        await message.answer(with_footer(f'✅ <b>Kino kodi qabul qilindi: {movie_id}</b>\n\n🎬 Endi kino video faylini yuboring:'), parse_mode='HTML')
        return
    await process_and_save_movie_with_code(message, state, movie_id, file_id, raw_caption, is_callback=False)

@router.callback_query(F.data.startswith('save_direct_auto_'))
async def save_direct_auto_callback(callback: CallbackQuery, state: FSMContext):
    try:
        movie_id = int(callback.data.split('_')[-1])
        data = await state.get_data()
        file_id = data.get('direct_file_id')
        raw_caption = data.get('direct_caption', '')
        if not file_id:
            await callback.answer("⚠️ Video ma'lumotlari toza bo'lgan. Qaytadan video yuboring.", show_alert=True)
            await state.clear()
            return
        await process_and_save_movie_with_code(callback, state, movie_id, file_id, raw_caption, is_callback=True)
    except Exception as err:
        import logging
        logging.error(f'save_direct_auto_callback error: {err}')
        await callback.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.", show_alert=True)
MENU_BUTTONS = ["Kino qo'shish ➕", "Kino o'chirish ❌", 'Statistika 📊', 'Reklama yuborish 📢', 'Homiy Kanallar 📢', 'Moderatorlar 👥', 'Boshqarish ⚙️', 'Moderatorlarni boshqarish ⚙️', 'Kino Trendlari 📈', 'Zaxira (Backup) 💾', 'Kino tahrirlash ✏️', 'Kino faylini yangilash 🔄', "Kino so'rovlari 📥", 'Rejalashtirilgan reklama 📅', 'Referal sozlash 👥', 'Shubhali harakatlar 🚨', 'Keshni tozalash 🧹', '➕ Mannual Premium Qo\'shish']

@router.message(AdminStates.waiting_for_movie_video, F.text)
async def add_movie_video_invalid(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await state.clear()
        return
    data = await state.get_data()
    m_id = data.get('movie_id', '?')
    await message.answer(with_footer(f"⚠️ Siz <b>{m_id}</b> kodi uchun video yuklash bosqichidasiz.\n\n🎬 <b>Iltimos, kino video faylini yuboring!</b>\n\n📌 <i>Eslatma: Video fayli yuklanib jarayon to'liq yakunlanmaguncha <b>{m_id}</b> kodi bazaga saqlanmaydi va bo'sh qoladi.\nJarayonni bekor qilish uchun /cancel yoki /start yuboring.</i>"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_caption, F.text, ~F.text.in_(MENU_BUTTONS))
async def add_movie_caption(message: Message, state: FSMContext):
    caption = message.text
    if caption == '.':
        caption = ''
    data = await state.get_data()
    file_id = data['file_id']
    movie_id = data['movie_id']
    await db_req.add_movie_with_id(movie_id, file_id, caption)
    await state.clear()
    await message.answer(with_footer(f"✅ Kino muvaffaqiyatli qo'shildi!\n\n🎬 <b>Kino kodi:</b> <code>{movie_id}</code>"), parse_mode='HTML')
    await auto_post_movie_to_channel(message.bot, movie_id, file_id, caption)
    await db_req.notify_requesting_users_for_movie(message.bot, movie_id, caption)

@router.message(Command('delete'), StateFilter('*'))
@router.message(F.text.startswith('/del_'), StateFilter('*'))
async def direct_delete_command_handler(message: Message, state: FSMContext):
    if not await db_req.has_permission(message.from_user.id, 'delete_movie'):
        return
    import re
    ids = re.findall('\\d+', message.text)
    if not ids:
        await message.answer(with_footer("⚠️ Iltimos, o'chirmoqchi bo'lgan kino kodini yuboring (masalan: /delete 1)"))
        return
    for id_str in ids:
        movie_id = int(id_str)
        deleted_flag, m_cap = await db_req.delete_movie(movie_id)
        if deleted_flag:
            total_movies = await db_req.get_total_movies_count()
            name_str = m_cap[:50] if m_cap else '(Nomsiz kino)'
            await message.answer(with_footer(f"🗑️ <b>KINO BAZADAN O'CHIRILDI!</b>\n\n🎬 <b>O'chirilgan Kino kodi:</b> <code>{movie_id}</code>\n📌 <b>O'chirilgan Kino nomi:</b> <i>{name_str}</i>\n📊 <b>Bazada qolgan jami kinolar:</b> <code>{total_movies} ta</code>\n☁️ <i>O'chirish SQLite hamda MongoDB Atlas Cloud bulutingizdan to'liq amamalga oshirildi!</i>"), parse_mode='HTML')
            await sync_movies_backup_storage(message.bot)
        else:
            await message.answer(with_footer(f"❌ <b>Bunday kodli kino bazada mavjud emas: {movie_id}</b>\n\n<i>Kino ilgari o'chirilgan yoki bazaga qo'shilmadi.</i>"), parse_mode='HTML')

@router.message(F.text.regexp("(?i).*(kino o'chirish|delete movie).*"))
async def delete_movie_start(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'delete_movie'):
        return
    await state.set_state(AdminStates.waiting_for_movie_delete)
    await message.answer(with_footer("🗑️ <b>KINO O'CHIRISH REJIMI FAOLLASHDI!</b>\n\nO'chirmoqchi bo'lgan kino kodlarini yuboring (masalan: <code>1</code>, <code>2</code>, <code>501</code> yoki birga: <code>1, 2, 3</code>).\n<i>Eslatma: Bitta yuborishda 1 ta yoki bir nechta kino kodlarini yuborib o'chirishingiz mumkin.</i>"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_delete, F.text)
async def delete_movie_exec(message: Message, state: FSMContext):
    raw_text = message.text.strip()
    if raw_text in MENU_BUTTONS or raw_text.startswith('/'):
        await state.clear()
        if raw_text == '/start' or raw_text == '/cancel':
            from handlers.user import execute_start_logic
            await execute_start_logic(message, state)
        return
    import re
    ids_found = re.findall('\\d+', raw_text)
    if not ids_found:
        await message.answer(with_footer('⚠️ Iltimos, faqat kino kodlarini (raqam) kiriting (masalan: 1, 2, 3):'))
        return
    for id_str in ids_found:
        movie_id = int(id_str)
        deleted_flag, m_cap = await db_req.delete_movie(movie_id)
        if deleted_flag:
            total_movies = await db_req.get_total_movies_count()
            name_str = m_cap[:50] if m_cap else '(Nomsiz kino)'
            await message.answer(with_footer(f"🗑️ <b>KINO BAZADAN O'CHIRILDI!</b>\n\n🎬 <b>O'chirilgan Kino kodi:</b> <code>{movie_id}</code>\n📌 <b>O'chirilgan Kino nomi:</b> <i>{name_str}</i>\n📊 <b>Bazada qolgan jami kinolar:</b> <code>{total_movies} ta</code>\n☁️ <i>O'chirish SQLite hamda MongoDB Atlas Cloud bulutingizdan to'liq amalga oshirildi!</i>"), parse_mode='HTML')
            await sync_movies_backup_storage(message.bot)
        else:
            await message.answer(with_footer(f"❌ <b>Bunday kodli kino bazada mavjud emas: {movie_id}</b>\n\n<i>Kino ilgari o'chirilgan yoki bazaga qo'shilmadi.</i>"), parse_mode='HTML')

@router.message(F.text.regexp('(?i).*(kino trendlari|trending movies).*'))
async def show_trending_movies(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'view_trends'):
        return
    trends = await db_req.get_trending_movies()
    if not trends:
        await message.answer(with_footer("📈 <b>Hozircha trenddagi kinolar statistikasi yetarli emas!</b>\n\n<i>Foydalanuvchilar kinolarni tomosha qilishni boshlagach, eng ko'p ko'rilgan TOP 10 kinolar avtomatik bu yerda ko'rinadi.</i>"), parse_mode='HTML')
        return
    text = "📈 <b>Eng ko'p ko'rilgan TOP 10 kino:</b>\n\n"
    for idx, (movie_id, caption, views) in enumerate(trends, 1):
        name = caption[:40] if caption else '(nomsiz)'
        text += f'{idx}. 🎬 /{movie_id} — {name} (👁 <b>{views} marta</b>)\n'
    await message.answer(with_footer(text), parse_mode='HTML')

@router.message(F.text == 'Homiy Kanallar 📢')
async def sponsor_channels_list(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'manage_sponsors'):
        return
    channels = await db_req.get_sponsor_channels()
    await message.answer(with_footer("📢 <b>Hamkor (Sponsor) kanallar ro'yxati:</b>\n\nKanalni o'chirish uchun uning oldidagi tugmani bosing yoki yangi kanal qo'shing."), reply_markup=get_sponsor_channels_keyboard(channels), parse_mode='HTML')

@router.callback_query(F.data == 'add_channel_start')
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_channel_id)
    await callback.message.answer(with_footer('Kanalning username yoki ID raqamini yuboring:\nMasalan: <code>@Kanal_Username</code> yoki <code>-1001234567</code>'))
    await callback.answer()

@router.message(AdminStates.waiting_for_channel_id, F.text)
async def add_channel_id(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    await state.update_data(channel_id=channel_id)
    await state.set_state(AdminStates.waiting_for_channel_name)
    await message.answer(with_footer("Kanal nomini (tugmada ko'rinadigan matn) yuboring:"))

@router.message(AdminStates.waiting_for_channel_name)
async def add_channel_name(message: Message, state: FSMContext):
    channel_name = message.text.strip() if message.text else 'Kanal'
    data = await state.get_data()
    channel_id = data.get('channel_id')
    if not channel_id:
        await message.answer(with_footer("⚠️ Qayta urinib ko'ring. Iltimos, «Yangi kanal qo'shish ➕» tugmasini qayta bosing."))
        await state.clear()
        return
    success = await db_req.add_sponsor_channel(channel_id, channel_name)
    await state.clear()
    if success:
        await message.answer(with_footer(f"✅ Hamkor kanal muvaffaqiyatli qo'shildi: <b>{channel_name}</b>"), parse_mode='HTML')
    else:
        await message.answer(with_footer("❌ Kanal qo'shishda xatolik yuz berdi. Ehtimol, bu kanal allaqachon mavjud."))

@router.callback_query(F.data.startswith('del_channel_'))
async def delete_channel(callback: CallbackQuery):
    db_id = int(callback.data.split('_')[2])
    await db_req.remove_sponsor_channel(db_id)
    channels = await db_req.get_sponsor_channels()
    await callback.message.edit_reply_markup(reply_markup=get_sponsor_channels_keyboard(channels))
    await callback.answer("Hamkor kanal o'chirildi! ❌")

@router.message(F.text.in_(['Moderatorlar 🛠', 'Moderatorlar 👥', 'Moderatorlarni boshqarish 🛠']))
async def moderators_list(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    mods = await db_req.get_moderators()
    await message.answer(with_footer("🛠 <b>Moderatorlar boshqaruvi:</b>\n\nModerator qo'shish uchun quyidagi tugmani bosing."), reply_markup=get_moderators_keyboard(mods), parse_mode='HTML')

@router.message(F.text.in_(['Boshqarish ⚙️', 'Moderatorlarni boshqarish ⚙️']))
async def admin_boshqarish(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    mods = await db_req.get_moderators()
    if not mods:
        await message.answer(with_footer("⚙️ <b>Moderator sozlamalari</b>\n\nHozircha hech qanday moderator yo'q.\nAvval «Moderatorlar 👥» bo'limidan moderator qo'shing."), parse_mode='HTML')
        return
    await message.answer(with_footer('⚙️ <b>Moderator sozlamalari</b>\n\nSozlashni xohlagan moderatorni tanlang:'), reply_markup=get_admin_list_keyboard(mods), parse_mode='HTML')

@router.callback_query(F.data.startswith('mod_settings_'))
async def mod_settings_callback(callback: CallbackQuery):
    """Moderator ruxsatnomalari ekranini ochish"""
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    mod_user_id = int(callback.data[len('mod_settings_'):])
    perms = await db_req.get_moderator_permissions(mod_user_id)
    mods = await db_req.get_moderators()
    mod_name = str(mod_user_id)
    for uid, uname, fname in mods:
        if uid == mod_user_id:
            mod_name = f'@{uname}' if uname else fname or str(mod_user_id)
            break
    await callback.message.edit_text(with_footer(f"⚙️ <b>{mod_name}</b> uchun ruxsatlar:\n\nTugmalarni bosib ruxsatlarni yoqing yoki o'chiring:"), reply_markup=get_mod_perms_keyboard(mod_user_id, perms), parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data.startswith('toggleperm_'))
async def toggle_permission_callback(callback: CallbackQuery):
    """Moderator ruxsatini toggle qilish"""
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    rest = callback.data[len('toggleperm_'):]
    uid_str, perm_name = rest.split('_', 1)
    mod_user_id = int(uid_str)
    await db_req.toggle_moderator_permission(mod_user_id, perm_name)
    perms = await db_req.get_moderator_permissions(mod_user_id)
    perm_labels = {'add_movie': "Kino qo'shish ➕", 'delete_movie': "Kino o'chirish ❌", 'view_stats': 'Statistika 📊', 'send_broadcast': 'Reklama yuborish 📢', 'manage_sponsors': 'Homiy Kanallar 📢', 'view_trends': 'Kino Trendlari 📈', 'backup_db': 'Zaxira (Backup) 💾'}
    changed = perm_labels.get(perm_name, perm_name)
    status = '✅ yoqildi' if perms.get(perm_name) else "❌ o'chirildi"
    await callback.answer(f'{changed}: {status}', show_alert=False)
    mods = await db_req.get_moderators()
    mod_name = str(mod_user_id)
    for uid, uname, fname in mods:
        if uid == mod_user_id:
            mod_name = f'@{uname}' if uname else fname or str(mod_user_id)
            break
    await callback.message.edit_text(with_footer(f"⚙️ <b>{mod_name}</b> uchun ruxsatlar:\n\nTugmalarni bosib ruxsatlarni yoqing yoki o'chiring:"), reply_markup=get_mod_perms_keyboard(mod_user_id, perms), parse_mode='HTML')

@router.callback_query(F.data == 'boshqarish_back')
async def boshqarish_back_callback(callback: CallbackQuery):
    """Moderatorlar ro'yxatiga qaytish"""
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    mods = await db_req.get_moderators()
    await callback.message.edit_text(with_footer('⚙️ <b>Moderator sozlamalari</b>\n\nSozlashni xohlagan moderatorni tanlang:'), reply_markup=get_admin_list_keyboard(mods), parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data == 'add_mod_start')
async def add_mod_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_mod_id)
    await callback.message.answer(with_footer('Yangi moderatorning Telegram ID raqamini kiriting:'))
    await callback.answer()

@router.message(AdminStates.waiting_for_mod_id, F.text)
async def add_mod_exec(message: Message, state: FSMContext):
    text = message.text.strip()
    if text in MENU_BUTTONS:
        await state.clear()
        return
    if text.startswith('-') or text.startswith('@'):
        await message.answer(with_footer("❌ <b>Kanal yoki guruh kiritish mumkin emas!</b>\n\nIltimos, faqat moderator qilmoqchi bo'lgan foydalanuvchining shaxsiy Telegram ID raqamini kiriting."))
        return
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat sonlardan iborat shaxsiy Telegram ID raqamini kiriting.'))
        return
    user_id = int(text)
    success = await db_req.set_role(user_id, 'moderator')
    await state.clear()
    if success:
        await message.answer(with_footer(f'✅ Foydalanuvchi moderator qilib tayinlandi! ID: {user_id}'))
    else:
        await message.answer(with_footer("❌ Foydalanuvchi topilmadi. Avval u botga kirib ro'yxatdan o'tgan bo'lishi kerak."))

@router.callback_query(F.data.startswith('del_mod_'))
async def delete_moderator(callback: CallbackQuery):
    user_id = int(callback.data.split('_')[2])
    await db_req.set_role(user_id, 'member')
    mods = await db_req.get_moderators()
    await callback.message.edit_reply_markup(reply_markup=get_moderators_keyboard(mods))
    await callback.answer('Moderatorlik huquqi olib tashlandi! ❌')

@router.message(Command('ban'))
async def ban_user_cmd(message: Message):
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(with_footer('Foydalanish: <code>/ban [Foydalanuvchi ID]</code>'))
        return
    user_id = int(args[1])
    success = await db_req.ban_user(user_id)
    if success:
        await message.answer(with_footer(f'🚫 Foydalanuvchi bloklandi! ID: <code>{user_id}</code>'))
    else:
        await message.answer(with_footer('❌ Bunday foydalanuvchi bazada topilmadi.'))

@router.message(Command('unban'))
async def unban_user_cmd(message: Message):
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(with_footer('Foydalanish: <code>/unban [Foydalanuvchi ID]</code>'))
        return
    user_id = int(args[1])
    success = await db_req.unban_user(user_id)
    if success:
        await message.answer(with_footer(f'✅ Foydalanuvchi blokdan chiqarildi! ID: <code>{user_id}</code>'))
    else:
        await message.answer(with_footer('❌ Bunday foydalanuvchi bazada topilmadi.'))

@router.message(F.text == 'Zaxira (Backup) 💾')
async def backup_database(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'backup_db'):
        return
    if os.path.exists('kino_bot.db'):
        db_file = FSInputFile('kino_bot.db')
        await message.answer_document(db_file, caption="💾 <b>Kino Bot ma'lumotlar bazasi zaxira nusxasi (SQLite)</b>")
        try:
            import csv
            users = await db_req.get_users_detailed_list()
            csv_path = 'users_list.csv'
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['ID', 'Username', "To'liq ismi", 'Rol', 'Holati', 'Ballari', 'Taklif qilganlari', "Ro'yxatdan o'tgan sana"])
                for row in users:
                    writer.writerow(row)
            excel_file = FSInputFile(csv_path, filename='users_detailed_list.csv')
            await message.answer_document(excel_file, caption="📊 <b>Foydalanuvchilarning batafsil Excel (CSV) ro'yxati</b>")
            if os.path.exists(csv_path):
                os.remove(csv_path)
        except Exception as e:
            await message.answer(with_footer(f"⚠️ Foydalanuvchilar ro'yxatini yaratishda xato: {e}"))
    else:
        await message.answer(with_footer('Baza fayli topilmadi.'))

@router.message(F.text == 'Reklama yuborish 📢')
async def broadcast_wizard_start(message: Message, state: FSMContext):
    if not await db_req.has_permission(message.from_user.id, 'send_broadcast'):
        return
    await state.clear()
    await state.set_state(AdminStates.waiting_for_bc_target)
    from keyboards.inline import get_broadcast_target_keyboard
    await message.answer(with_footer('📢 <b>Reklama yuborish - Auditoriyani tanlang:</b>\n\nReklama qaysi guruhdagi foydalanuvchilarga yuborilsin?'), parse_mode='HTML', reply_markup=get_broadcast_target_keyboard())

@router.callback_query(F.data.startswith('bc_target_'))
async def bc_target_selected(callback: CallbackQuery, state: FSMContext):
    target = callback.data[len('bc_target_'):]
    await state.update_data(target_group=target)
    await state.set_state(AdminStates.waiting_for_bc_media)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Faqat matn)", callback_data='bc_skip_media')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await callback.message.edit_text(with_footer("📸 <b>Reklama uchun rasm yoki video yuboring:</b>\n\n<i>Eslatma: Agar reklama faqat matndan iborat bo'lsa, «O'tkazib yuborish ⏭» tugmasini bosing.</i>"), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == 'bc_cancel')
async def bc_cancel_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(with_footer('❌ <b>Reklama tayyorlash bekor qilindi.</b>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_bc_media, F.photo | F.video | F.animation)
async def bc_media_handler(message: Message, state: FSMContext):
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        media_id = message.video.file_id
        media_type = 'video'
    elif message.animation:
        media_id = message.animation.file_id
        media_type = 'animation'
    else:
        media_id = None
        media_type = None
    await state.update_data(bc_media_id=media_id, bc_media_type=media_type)
    if message.caption:
        await state.update_data(bc_caption=message.caption.strip())
        await state.set_state(AdminStates.waiting_for_bc_button)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Standart bot tugmasi)", callback_data='bc_skip_button')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
        await message.answer(with_footer(f'✅ Media va matn qabul qilindi.\n\n🔗 <b>Reklama ostidagi tugma uchun nom va havola yuboring:</b>\n<i>Format: Tugma nomi - https://havola.com</i>\n<i>Masalan: Botga kirish - https://t.me/{config.BOT_USERNAME.lstrip('@')}?start=start</i>'), parse_mode='HTML', reply_markup=kb)
    else:
        await state.set_state(AdminStates.waiting_for_bc_caption)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Matnsiz)", callback_data='bc_skip_caption')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
        await message.answer(with_footer('✅ Media qabul qilindi!\n\n📝 <b>Endi reklama matnini (izoh) kiriting:</b>'), parse_mode='HTML', reply_markup=kb)

@router.message(AdminStates.waiting_for_bc_media, F.text, ~F.text.in_(MENU_BUTTONS))
async def bc_media_text_fallback(message: Message, state: FSMContext):
    caption = message.text.strip()
    await state.update_data(bc_media_id=None, bc_media_type=None, bc_caption=caption)
    await state.set_state(AdminStates.waiting_for_bc_button)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Standart bot tugmasi)", callback_data='bc_skip_button')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await message.answer(with_footer(f'✅ Matn reklama sarlavhasi sifatida qabul qilindi!\n\n🔗 <b>Reklama ostidagi tugma uchun nom va havola yuboring:</b>\n<i>Format: Tugma nomi - https://havola.com</i>\n<i>Masalan: Botga kirish - https://t.me/{config.BOT_USERNAME.lstrip('@')}?start=start</i>'), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'bc_skip_media')
async def bc_skip_media_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(bc_media_id=None, bc_media_type=None)
    await state.set_state(AdminStates.waiting_for_bc_caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await callback.message.edit_text(with_footer('📝 <b>Reklama matnini kiriting:</b>'), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.message(AdminStates.waiting_for_bc_caption)
async def bc_caption_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    media_type = data.get('bc_media_type')
    if message.sticker:
        if media_type in ['photo', 'video', 'animation']:
            await message.answer(with_footer("⚠️ <b>Rasm yoki videoli reklama uchun stiker yuborib bo'lmaydi!</b>\n\n<i>Telegram cheklovlari sababli rasm/video ostida stiker ko'rinmaydi. Iltimos, reklama uchun matn (text) yoki emojili matn yozib yuboring:</i>"), parse_mode='HTML')
            return
        else:
            await state.update_data(bc_media_id=message.sticker.file_id, bc_media_type='sticker', bc_caption='')
            await state.set_state(AdminStates.waiting_for_bc_button)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Standart bot tugmasi)", callback_data='bc_skip_button')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
            await message.answer(with_footer('✅ Stiker reklama classi sifatida qabul qilindi!\n\n🔗 <b>Reklama ostidagi tugma uchun nom va havola yuboring:</b>\n<i>Format: Tugma nomi - https://havola.com</i>'), parse_mode='HTML', reply_markup=kb)
            return
    caption = ''
    if message.text:
        caption = message.text.strip()
    elif message.caption:
        caption = message.caption.strip()
    await state.update_data(bc_caption=caption)
    await state.set_state(AdminStates.waiting_for_bc_button)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Standart bot tugmasi)", callback_data='bc_skip_button')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await message.answer(with_footer(f'🔗 <b>Reklama ostidagi tugma uchun nom va havola yuboring:</b>\n<i>Format: Tugma nomi - https://havola.com</i>\n<i>Masalan: Botga kirish - https://t.me/{config.BOT_USERNAME.lstrip('@')}?start=start</i>'), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'bc_skip_caption')
async def bc_skip_caption_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(bc_caption='')
    await state.set_state(AdminStates.waiting_for_bc_button)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Standart bot tugmasi)", callback_data='bc_skip_button')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await callback.message.edit_text(with_footer('🔗 <b>Reklama ostidagi tugma uchun nom va havola yuboring:</b>\n<i>Format: Tugma nomi - https://havola.com</i>'), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.message(AdminStates.waiting_for_bc_button, F.text, ~F.text.in_(MENU_BUTTONS))
async def bc_button_handler(message: Message, state: FSMContext):
    text = message.text.strip()
    if '-' in text and ('http://' in text or 'https://' in text or 't.me/' in text or ('://' in text)):
        parts = text.split('-', 1)
        btn_text = parts[0].strip()
        btn_url = parts[1].strip()
        if not btn_url.startswith('http'):
            btn_url = 'https://' + btn_url
        await state.update_data(bc_btn_text=btn_text, bc_btn_url=btn_url)
        await show_bc_preview(message, state)
        return
    if 'http://' in text or 'https://' in text or 't.me/' in text or ('://' in text):
        btn_url = text
        if not btn_url.startswith('http'):
            btn_url = 'https://' + btn_url
        await state.update_data(bc_btn_url=btn_url)
        await state.set_state(AdminStates.waiting_for_bc_button_title_after_url)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='O\'tkazib yuborish ⏭ (Standart "📍 Havolaga o\'tish")', callback_data='bc_skip_button_title')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
        await message.answer(with_footer("✅ <b>Havola qabul qilindi!</b>\n\n📝 <b>Endi ushbu tugma uchun maxsus nom yuboring:</b>\n<i>Masalan: Botga kirish 🚀 yoki Premyerani ko'rish 🎬</i>\n\n<i>(Nom bermasangiz «O'tkazib yuborish ⏭» tugmasini bosing — bot avtomatik «📍 Havolaga o'tish» nomini qo'yadi)</i>"), parse_mode='HTML', reply_markup=kb)
        return
    btn_text = text
    await state.update_data(bc_btn_text=btn_text)
    await state.set_state(AdminStates.waiting_for_bc_button_url)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Standart bot havolasi)", callback_data='bc_skip_button_url')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await message.answer(with_footer(f'✅ Tugma nomi qabul qilindi: <b>«{btn_text}»</b>\n\n🔗 <b>Endi ushbu tugma uchun havolani (link) yuboring:</b>\n<i>Masalan: https://t.me/{config.BOT_USERNAME.lstrip('@')}?start=start</i>'), parse_mode='HTML', reply_markup=kb)

@router.message(AdminStates.waiting_for_bc_button_title_after_url, F.text, ~F.text.in_(MENU_BUTTONS))
async def bc_button_title_after_url_handler(message: Message, state: FSMContext):
    btn_text = message.text.strip()
    await state.update_data(bc_btn_text=btn_text)
    await show_bc_preview(message, state)

@router.callback_query(F.data == 'bc_skip_button_title')
async def bc_skip_button_title_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(bc_btn_text="📍 Havolaga o'tish")
    await show_bc_preview(callback.message, state, is_callback=True)
    await callback.answer()

@router.message(AdminStates.waiting_for_bc_button_url, F.text, ~F.text.in_(MENU_BUTTONS))
async def bc_button_url_handler(message: Message, state: FSMContext):
    btn_url = message.text.strip()
    if not btn_url.startswith('http'):
        btn_url = 'https://' + btn_url
    await state.update_data(bc_btn_url=btn_url)
    await show_bc_preview(message, state)

@router.callback_query(F.data == 'bc_skip_button_url')
async def bc_skip_button_url_callback(callback: CallbackQuery, state: FSMContext):
    bot_username = config.BOT_USERNAME.lstrip('@')
    default_btn_url = f'https://t.me/{bot_username}?start=start'
    await state.update_data(bc_btn_url=default_btn_url)
    await show_bc_preview(callback.message, state, is_callback=True)
    await callback.answer()

@router.callback_query(F.data == 'bc_skip_button')
async def bc_skip_button_callback(callback: CallbackQuery, state: FSMContext):
    bot_username = config.BOT_USERNAME.lstrip('@')
    default_btn_text = f'🚀 Botga kirish: @{bot_username}'
    default_btn_url = f'https://t.me/{bot_username}?start=start'
    await state.update_data(bc_btn_text=default_btn_text, bc_btn_url=default_btn_url)
    await show_bc_preview(callback.message, state, is_callback=True)
    await callback.answer()

async def show_bc_preview(event: Message, state: FSMContext, is_callback: bool=False):
    data = await state.get_data()
    media_id = data.get('bc_media_id')
    media_type = data.get('bc_media_type')
    caption = data.get('bc_caption', '')
    btn_text = data.get('bc_btn_text')
    btn_url = data.get('bc_btn_url')
    bot_username = config.BOT_USERNAME
    if not bot_username.startswith('@'):
        bot_username = f'@{bot_username}'
    final_caption = caption
    if bot_username not in final_caption:
        final_caption = f'{final_caption}\n\n🤖 {bot_username}'.strip()
    await state.update_data(bc_final_caption=final_caption)
    await state.set_state(AdminStates.waiting_for_bc_confirm)
    ad_kb = None
    if btn_text and btn_url:
        ad_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=btn_url)]])
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Yuborish 🚀 (Start)', callback_data='bc_send_confirm')], [InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    if not is_callback:
        await event.answer("👁 <b>Reklama Tayyor! Oldindan ko'rish (Preview):</b>", parse_mode='HTML')
    if media_id and media_type == 'photo':
        try:
            await event.bot.send_photo(chat_id=event.chat.id, photo=media_id, caption=with_footer(final_caption), reply_markup=ad_kb, parse_mode='HTML')
        except Exception:
            await event.bot.send_photo(chat_id=event.chat.id, photo=media_id, caption=with_footer(final_caption), reply_markup=ad_kb)
    elif media_id and media_type == 'video':
        try:
            await event.bot.send_video(chat_id=event.chat.id, video=media_id, caption=with_footer(final_caption), reply_markup=ad_kb, parse_mode='HTML')
        except Exception:
            await event.bot.send_video(chat_id=event.chat.id, video=media_id, caption=with_footer(final_caption), reply_markup=ad_kb)
    elif media_id and media_type == 'animation':
        try:
            await event.bot.send_animation(chat_id=event.chat.id, animation=media_id, caption=final_caption, reply_markup=ad_kb, parse_mode='HTML')
        except Exception:
            await event.bot.send_animation(chat_id=event.chat.id, animation=media_id, caption=final_caption, reply_markup=ad_kb)
    elif media_id and media_type == 'sticker':
        await event.bot.send_sticker(chat_id=event.chat.id, sticker=media_id, reply_markup=ad_kb)
        if final_caption:
            await event.bot.send_message(chat_id=event.chat.id, text=final_caption, parse_mode='HTML')
    else:
        try:
            await event.bot.send_message(chat_id=event.chat.id, text=final_caption, reply_markup=ad_kb, parse_mode='HTML')
        except Exception:
            await event.bot.send_message(chat_id=event.chat.id, text=final_caption, reply_markup=ad_kb)
    await event.bot.send_message(chat_id=event.chat.id, text='⚠️ <b>Yuqoridagi reklama xabari barcha foydalanuvchilar va kanallarga yuborilsinmi?</b>', parse_mode='HTML', reply_markup=confirm_kb)

@router.callback_query(F.data == 'bc_send_confirm')
async def bc_send_confirm_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    media_id = data.get('bc_media_id')
    media_type = data.get('bc_media_type')
    final_caption = data.get('bc_final_caption', '')
    btn_text = data.get('bc_btn_text')
    btn_url = data.get('bc_btn_url')
    await state.clear()
    ad_kb = None
    if btn_text and btn_url:
        ad_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=btn_text, url=btn_url)]])
    target_group = data.get('target_group', 'all')
    users = await db_req.get_target_users(target_group)
    if not users:
        await callback.message.edit_text(with_footer("Ushbu maqsadli guruhda hali foydalanuvchilar yo'q."))
        await callback.answer()
        return
    group_labels = {'all': 'barcha', 'premium': 'Premium', 'active_7d': 'faol (7 kunlik)'}
    g_label = group_labels.get(target_group, 'tanlangan')
    await callback.message.edit_text(with_footer(f'🚀 Reklama {len(users)} ta ({g_label}) foydalanuvchiga va kanallarga yuborilmoqda. Iltimos kuting...'))
    bot = callback.bot
    sent_count = 0
    failed_count = 0
    cleaned_count = 0
    for user_id in users:
        try:
            if media_id and media_type == 'photo':
                try:
                    await bot.send_photo(chat_id=user_id, photo=media_id, caption=with_footer(final_caption), reply_markup=ad_kb, parse_mode='HTML')
                except Exception:
                    await bot.send_photo(chat_id=user_id, photo=media_id, caption=with_footer(final_caption), reply_markup=ad_kb)
            elif media_id and media_type == 'video':
                try:
                    await bot.send_video(chat_id=user_id, video=media_id, caption=with_footer(final_caption), reply_markup=ad_kb, parse_mode='HTML')
                except Exception:
                    await bot.send_video(chat_id=user_id, video=media_id, caption=with_footer(final_caption), reply_markup=ad_kb)
            elif media_id and media_type == 'animation':
                try:
                    await bot.send_animation(chat_id=user_id, animation=media_id, caption=final_caption, reply_markup=ad_kb, parse_mode='HTML')
                except Exception:
                    await bot.send_animation(chat_id=user_id, animation=media_id, caption=final_caption, reply_markup=ad_kb)
            elif media_id and media_type == 'sticker':
                await bot.send_sticker(chat_id=user_id, sticker=media_id, reply_markup=ad_kb)
                if final_caption:
                    await bot.send_message(chat_id=user_id, text=final_caption)
            else:
                try:
                    await bot.send_message(chat_id=user_id, text=final_caption, reply_markup=ad_kb, parse_mode='HTML')
                except Exception:
                    await bot.send_message(chat_id=user_id, text=final_caption, reply_markup=ad_kb)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed_count += 1
            err_str = str(e).lower()
            if any((kw in err_str for kw in ['forbidden', 'blocked', 'deactivated', 'chat not found'])):
                await db_req.delete_user(user_id)
                cleaned_count += 1
    channel_report = []
    try:
        db_channels = await db_req.get_sponsor_channels()
        all_ch = list(config.CHANNELS)
        for _, ch_id, ch_name in db_channels:
            if ch_id not in all_ch:
                all_ch.append(ch_id)
        for ch in all_ch:
            ch_display = ch
            try:
                chat_info = await bot.get_chat(ch)
                ch_display = f'@{chat_info.username}' if chat_info.username else chat_info.title or str(ch)
            except Exception:
                pass
            try:
                if media_id and media_type == 'photo':
                    await bot.send_photo(chat_id=ch, photo=media_id, caption=with_footer(final_caption), reply_markup=ad_kb, parse_mode='HTML')
                elif media_id and media_type == 'video':
                    await bot.send_video(chat_id=ch, video=media_id, caption=with_footer(final_caption), reply_markup=ad_kb, parse_mode='HTML')
                elif media_id and media_type == 'animation':
                    await bot.send_animation(chat_id=ch, animation=media_id, caption=final_caption, reply_markup=ad_kb, parse_mode='HTML')
                else:
                    await bot.send_message(chat_id=ch, text=final_caption, reply_markup=ad_kb, parse_mode='HTML')
                channel_report.append(f'✅ <b>{ch_display}</b> — Muvaffaqiyatli')
            except Exception as e:
                channel_report.append(f'❌ <b>{ch_display}</b> — Xato (Admin emas)')
    except Exception as e:
        print(f'Channel broadcast error: {e}')
    ch_report_str = '\n'.join(channel_report) if channel_report else '<i>Tizimda kanallar topilmadi.</i>'
    summary_text = f'📢 <b>Reklama yuborish yakunlandi:</b>\n\n✅ <b>Muvaffaqiyatli yuborildi:</b> {sent_count} ta\n❌ <b>Yuborilmaganlar:</b> {failed_count} ta\n🧹 <b>Bloklagani uchun tozalanganlar:</b> {cleaned_count} ta\n\n📢 <b>Homiy kanallarga yuborilish holati:</b>\n{ch_report_str}'
    await callback.message.answer(with_footer(summary_text), parse_mode='HTML')
    await callback.answer()

@router.message(F.text == "Kino so'rovlari 📥")
async def show_movie_requests(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'view_stats'):
        return
    reqs = await db_req.get_pending_requests()
    if not reqs:
        await message.answer(with_footer("📥 <b>Kino buyurtmalari (so'rovlari):</b>\n\nHozircha hech qanday buyurtma yo'q."), parse_mode='HTML')
        return
    await message.answer(with_footer("📥 <b>Kino buyurtmalari (so'rovlari):</b>\n\nQuyida foydalanuvchilar so'ragan kinolar ro'yxati:"))
    for req_id, movie_name, username, full_name, created_at in reqs[:20]:
        name = f'@{username}' if username else full_name or 'Foydalanuvchi'
        text = f"🎬 <b>Kino:</b> {movie_name}\n👤 <b>Kim so'radi:</b> {name}\n📅 <b>Sana:</b> {created_at}"
        await message.answer(with_footer(text), reply_markup=get_resolve_request_keyboard(req_id), parse_mode='HTML')

@router.callback_query(F.data.startswith('resolve_req_'))
async def resolve_movie_request(callback: CallbackQuery):
    req_id = int(callback.data.split('_')[2])
    success, user_id, movie_name = await db_req.resolve_request(req_id)
    if success:
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n✅ <b>Bajarildi deb belgilandi!</b>'), parse_mode='HTML')
        await callback.answer('Bajarildi ✅')
        try:
            await callback.bot.send_message(chat_id=user_id, text=f"🎉 <b>Sizning so'rovingiz bajarildi!</b>\n\n🎬 Siz so'ragan kino: <b>{movie_name}</b>\nSiz uni kanal orqali kodini ko'rishingiz mumkin.", parse_mode='HTML')
        except Exception:
            pass
    else:
        await callback.answer('Xatolik yuz berdi!', show_alert=True)

@router.message(F.text == 'Kino tahrirlash ✏️')
async def edit_movie_start(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    await state.set_state(AdminStates.waiting_for_movie_edit_id)
    await message.answer(with_footer("✏️ <b>Tahrirlamoqchi bo'lgan kino kodini yuboring:</b>"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_edit_id, F.text, ~F.text.in_(MENU_BUTTONS))
async def edit_movie_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat raqamlardan iborat kino kodini kiriting:'))
        return
    movie_id = int(text)
    movie = await db_req.get_movie(movie_id)
    if not movie:
        await message.answer(with_footer(f'❌ <b>{movie_id}</b> kodli kino topilmadi! Qayta kiriting:'))
        return
    await state.update_data(edit_movie_id=movie_id)
    await state.set_state(AdminStates.waiting_for_movie_edit_caption)
    await message.answer(with_footer(f"🎬 Tanlangan kino kodi: <b>{movie_id}</b>\nHozirgi tavsif: <i>{movie[1] or '(tavsifsiz)'}</i>\n\n✏️ <b>Kino uchun yangi tavsif (caption) yuboring:</b>\n<i>Tavsifni o'chirish uchun nuqta (.) yuboring.</i>"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_edit_caption, F.text, ~F.text.in_(MENU_BUTTONS))
async def edit_movie_caption(message: Message, state: FSMContext):
    caption = message.text.strip()
    if caption == '.':
        caption = ''
    data = await state.get_data()
    movie_id = data['edit_movie_id']
    await db_req.update_movie_caption(movie_id, caption)
    await state.clear()
    await message.answer(with_footer(f'✅ <b>{movie_id}</b> kodli kino tavsifi muvaffaqiyatli tahrirlandi!'), parse_mode='HTML')

@router.message(F.text.regexp('(?i).*(kino faylini yangilash|replace movie|replace video).*'))
async def replace_movie_start(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    await state.set_state(AdminStates.waiting_for_movie_replace_id)
    await message.answer(with_footer("🔄 <b>Video faylini almashtirmoqchi bo'lgan kino kodini yuboring (masalan: 1):</b>"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_replace_id, F.text, ~F.text.in_(MENU_BUTTONS))
async def replace_movie_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat raqamlardan iborat kino kodini kiriting:'))
        return
    movie_id = int(text)
    movie = await db_req.get_movie(movie_id)
    if not movie:
        await message.answer(with_footer(f'❌ <b>{movie_id}</b> kodli kino topilmadi! Qayta kiriting:'))
        return
    await state.update_data(replace_movie_id=movie_id)
    await state.set_state(AdminStates.waiting_for_movie_replace_video)
    await message.answer(with_footer(f'🎬 Tanlangan kino kodi: <b>{movie_id}</b>\n\n🔄 <b>Kino uchun yangi video faylini yuboring (video yoki document shaklida):</b>'), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_replace_video, F.video | F.document | F.animation | F.video_note)
async def replace_movie_video(message: Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id if message.document else message.animation.file_id if message.animation else message.video_note.file_id
    data = await state.get_data()
    movie_id = data['replace_movie_id']
    await db_req.update_movie_video(movie_id, file_id)
    await state.clear()
    await sync_movies_backup_storage(message.bot)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎬 Kinoni Ko'rish", callback_data=f'get_movie_{movie_id}'), InlineKeyboardButton(text='✏️ Tahrirlash', callback_data=f'edit_movie_start_{movie_id}')]])
    await message.answer(with_footer(f'✅ <b>KINO FAYLI MUVAFFAQIYATLI ALMASHTIRILDI!</b>\n\n🎬 <b>Kino kodi:</b> <code>{movie_id}</code>\n🔄 <i>Yangi video fayl SQLite va MongoDB Atlas Cloud bulutingizga saqlandi!</i>'), parse_mode='HTML', reply_markup=kb)

@router.message(F.text == 'Rejalashtirilgan reklama 📅')
async def scheduled_broadcast_start(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'send_broadcast'):
        return
    await state.set_state(AdminStates.waiting_for_scheduled_broadcast_msg)
    await message.answer(with_footer("📅 <b>Rejalashtirilgan reklama xabarini yozing:</b>\nXabar rasm, video, matn yoki boshqa har qanday formatda bo'lishi mumkin.\n<i>Bekor qilish uchun /cancel yozing.</i>"))

@router.message(F.text == 'Shubhali harakatlar 🚨')
async def show_abuse_logs(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    abuse_logs = await db_req.get_recent_abuse_logs_with_user_info(limit=30)
    if not abuse_logs:
        await message.answer(with_footer("🚨 <b>Shubhali harakatlar jurnali:</b>\n\nHozircha hech qanday shubhali harakat yo'q."), parse_mode='HTML')
        return
    await message.answer(with_footer(f'🚨 <b>Shubhali harakatlar jurnali ({len(abuse_logs)} ta yozuv):</b>'), parse_mode='HTML')
    from keyboards.inline import get_abuse_action_keyboard
    for u_id, log_type, details, created_at, username, full_name, warn_cnt, b_stage in abuse_logs:
        name_disp = f'@{username}' if username else full_name or f'User {u_id}'
        w_count = warn_cnt if warn_cnt is not None else 0
        b_stg = b_stage if b_stage is not None else 0
        txt = f'👤 <b>Foydalanuvchi:</b> {name_disp} (ID: <code>{u_id}</code>)\n🔹 <b>Turi:</b> <code>{log_type}</code>\n📝 <b>Tafsilot:</b> {details}\n🕒 <b>Vaqt:</b> <code>{created_at}</code>\n⚠️ <b>Ogohlantirishlar:</b> <code>{w_count}/3</code> | <b>Ban bosqichi:</b> <code>{b_stg}</code>'
        await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=get_abuse_action_keyboard(u_id))

@router.callback_query(F.data.startswith('warn_usr_'))
async def warn_user_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[2])
    is_banned, warn_cnt, duration_text, new_stage = await db_req.warn_user_progressive(u_id)
    if is_banned:
        user_sent = False
        try:
            ban_msg = f'🚫 <b>HISOBINGIZ VAQTINCHA BLOKLANDI!</b>\n\nSiz 3 marta ogohlantirish oldingiz va hisobingiz <b>{duration_text}</b> muddatga bloklandi.\n\n<i>Muddat tugagach botdan qayta foydalanishingiz mumkin.</i>'
            await callback.bot.send_message(with_footer(u_id), ban_msg, parse_mode='HTML')
            user_sent = True
        except Exception:
            user_sent = False
        status_note = 'va foydalanuvchiga yuborildi 📩' if user_sent else '(Foydalanuvchi botni bloklagan, lekin bazada saqlandi ⚠️)'
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n🚫 <b>Foydalanuvchi {duration_text}ga avto-bloklandi! (Bosqich: {new_stage}) {status_note}</b>'), parse_mode='HTML')
        await callback.answer(f'Foydalanuvchi 3-ogohlantirish sababli {duration_text}ga bloklandi! 🚫', show_alert=True)
    else:
        user_sent = False
        try:
            warn_msg = f"⚠️ <b>OGOHLANTIRISH! ({warn_cnt}/3)</b>\n\nHurmatli foydalanuvchi, siz botda shubhali harakat bajardingiz.\n<b>3 ta ogohlantirishdan so'ng hisobingiz vaqtincha bloklanadi!</b>"
            await callback.bot.send_message(with_footer(u_id), warn_msg, parse_mode='HTML')
            user_sent = True
        except Exception:
            user_sent = False
        status_note = 'va foydalanuvchiga yuborildi 📩' if user_sent else "(Foydalanuvchi botni bloklagan/to'xtatgan)"
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n⚠️ <b>Ogohlantirildi ({warn_cnt}/3) {status_note}</b>'), parse_mode='HTML')
        await callback.answer(f'Foydalanuvchiga ogohlantirish berildi ({warn_cnt}/3)! {status_note}', show_alert=True)

@router.message(F.text == 'Keshni tozalash 🧹')
async def clear_all_caches_cmd(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    await db_req.clear_all_caches()
    await message.answer(with_footer("✅ <b>Barcha keshlar muvaffaqiyatli tozalandi!</b>\n\n🧹 Eski loglar, temp bans va eski kunlik balllar o'chirildi."), parse_mode='HTML')

@router.message(AdminStates.waiting_for_scheduled_broadcast_msg, ~F.text.in_(MENU_BUTTONS))
async def scheduled_broadcast_msg(message: Message, state: FSMContext):
    await state.update_data(sch_chat_id=message.chat.id, sch_msg_id=message.message_id)
    await state.set_state(AdminStates.waiting_for_scheduled_broadcast_time)
    await message.answer(with_footer("⏳ <b>Ushbu reklama necha daqiqadan so'ng yuborilsin?</b>\n\nFaqat butun son kiriting (masalan: 10, 60, 180, 1440):"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_scheduled_broadcast_time, F.text, ~F.text.in_(MENU_BUTTONS))
async def scheduled_broadcast_time(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat butun son kiriting (daqiqalarda):'))
        return
    minutes = int(text)
    from datetime import datetime, timedelta
    send_time = datetime.now() + timedelta(minutes=minutes)
    send_time_str = send_time.strftime('%Y-%m-%d %H:%M:%S')
    data = await state.get_data()
    chat_id = data['sch_chat_id']
    message_id = data['sch_msg_id']
    await db_req.add_scheduled_broadcast(chat_id, message_id, send_time_str)
    await state.clear()
    await message.answer(with_footer(f"📅 <b>Reklama muvaffaqiyatli rejalashtirildi!</b>\n\n⏰ <b>Yuborilish vaqti:</b> <code>{send_time_str}</code> ({minutes} daqiqadan so'ng)"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_movie_edit_id)
async def edit_movie_id_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, faqat sonlardan iborat kino kodini kiriting!'))

@router.message(AdminStates.waiting_for_movie_edit_caption)
async def edit_movie_caption_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, kino uchun yangi tavsif matnini yozib yuboring!'))

@router.message(AdminStates.waiting_for_movie_replace_id)
async def replace_movie_id_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, faqat sonlardan iborat kino kodini kiriting!'))

@router.message(AdminStates.waiting_for_movie_replace_video)
async def replace_movie_video_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, yangi video faylini yuboring (video yoki document)!'))

@router.message(AdminStates.waiting_for_scheduled_broadcast_msg)
async def scheduled_broadcast_msg_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, reklama xabari media fayli yoki matnini yuboring!'))

@router.message(AdminStates.waiting_for_scheduled_broadcast_time)
async def scheduled_broadcast_time_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, faqat daqiqalardan iborat butun son kiriting!'))

@router.message(F.text == 'Referal sozlash 👥')
async def set_referral_promo_start(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        return
    await state.set_state(AdminStates.waiting_for_referral_promo_video)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭", callback_data='ref_promo_skip')], [InlineKeyboardButton(text="Mediani o'chirish ❌ (Faqat matn)", callback_data='ref_promo_delete')], [InlineKeyboardButton(text='Bekor qilish 🚫', callback_data='ref_promo_cancel')]])
    await message.answer(with_footer("👥 <b>Referal taklif qilish uchun promo video yoki rasmni yuboring:</b>\n\n<i>Bu media foydalanuvchilar o'z do'stlariga yuborganda ulashish xabari sifatida ishlatiladi.</i>"), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'ref_promo_skip')
async def callback_ref_promo_skip(callback: CallbackQuery, state: FSMContext):
    file_id = await db_req.get_setting('ref_promo_file_id')
    media_type = await db_req.get_setting('ref_promo_media_type')
    await state.update_data(ref_file_id=file_id, ref_media_type=media_type)
    await state.set_state(AdminStates.waiting_for_referral_promo_caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Eski matn qolsin)", callback_data='ref_promo_caption_skip')], [InlineKeyboardButton(text='Bekor qilish 🚫', callback_data='ref_promo_cancel')]])
    await callback.message.edit_text(with_footer("📝 <b>Eski promo media saqlandi. Endi yangi tavsif matnini yozib yuboring:</b>\n\n<i>Eslatma: Matn ostiga taklif havolasi avtomatik ravishda qo'shiladi.</i>"), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == 'ref_promo_delete')
async def callback_ref_promo_delete(callback: CallbackQuery, state: FSMContext):
    await state.update_data(ref_file_id=None, ref_media_type=None)
    await state.set_state(AdminStates.waiting_for_referral_promo_caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Eski matn qolsin)", callback_data='ref_promo_caption_skip')], [InlineKeyboardButton(text='Bekor qilish 🚫', callback_data='ref_promo_cancel')]])
    await callback.message.edit_text(with_footer("❌ <b>Promo media o'chirildi (Faqat matn qoladi). Endi yangi tavsif matnini yuboring:</b>"), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == 'ref_promo_cancel')
async def callback_ref_promo_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(with_footer('✅ Amal bekor qilindi.'))
    await callback.answer()

@router.callback_query(F.data == 'ref_promo_caption_skip')
async def callback_ref_promo_caption_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    file_id = data.get('ref_file_id')
    media_type = data.get('ref_media_type')
    caption = await db_req.get_setting('ref_promo_caption')
    await db_req.set_setting('ref_promo_file_id', file_id)
    await db_req.set_setting('ref_promo_media_type', media_type)
    await db_req.set_setting('ref_promo_caption', caption)
    await state.clear()
    await callback.message.edit_text(with_footer("✅ <b>Referal promo xabari muvaffaqiyatli saqlandi!</b>\n\nMatn o'zgarishsiz qoldirildi."), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_referral_promo_video, F.video | F.photo | F.document)
async def set_referral_promo_video(message: Message, state: FSMContext):
    if message.video:
        file_id = message.video.file_id
        media_type = 'video'
    elif message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    else:
        file_id = message.document.file_id
        media_type = 'document'
    await state.update_data(ref_file_id=file_id, ref_media_type=media_type)
    await state.set_state(AdminStates.waiting_for_referral_promo_caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="O'tkazib yuborish ⏭ (Eski matn qolsin)", callback_data='ref_promo_caption_skip')], [InlineKeyboardButton(text='Bekor qilish 🚫', callback_data='ref_promo_cancel')]])
    await message.answer(with_footer("📝 <b>Yangi media qabul qilindi. Endi ushbu media ostidagi tavsif matnini yuboring:</b>\n\n<i>Eslatma: Matn ostiga taklif havolasi avtomatik ravishda qo'shiladi.</i>"), parse_mode='HTML', reply_markup=kb)

@router.message(AdminStates.waiting_for_referral_promo_caption, F.text, ~F.text.in_(MENU_BUTTONS))
async def set_referral_promo_caption(message: Message, state: FSMContext):
    caption = message.text.strip()
    data = await state.get_data()
    file_id = data.get('ref_file_id')
    media_type = data.get('ref_media_type')
    await db_req.set_setting('ref_promo_file_id', file_id)
    await db_req.set_setting('ref_promo_media_type', media_type)
    await db_req.set_setting('ref_promo_caption', caption)
    await state.clear()
    await message.answer(with_footer("✅ <b>Referal promo xabari muvaffaqiyatli saqlandi!</b>\n\nEndi foydalanuvchilar 'Takliflar (Referal)' tugmasini bosganida shu xabarni o'z taklif havolalari bilan birga olishadi."), parse_mode='HTML')

@router.message(AdminStates.waiting_for_referral_promo_video)
async def set_referral_promo_video_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, video, rasm yoki hujjat yuboring!'))

@router.message(AdminStates.waiting_for_referral_promo_caption)
async def set_referral_promo_caption_invalid(message: Message):
    if message.text and message.text in MENU_BUTTONS:
        return
    await message.answer(with_footer('⚠️ Iltimos, promo matnini yozib yuboring!'))

@router.message(Command('cancel'))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(with_footer("⚠️ Hozirda faol jarayon yo'q."))
        return
    await state.clear()
    await message.answer(with_footer('✅ Amal bekor qilindi. Menyudan davom eting.'))

@router.message(F.text == 'Kun Kinosi ☀️')
async def daily_movie_menu(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        return
    today_movie_id = await db_req.get_today_daily_movie()
    if today_movie_id:
        status_text = f'✅ Bugun yuborilgan: kino kodi <code>{today_movie_id}</code>'
    else:
        status_text = '❌ Bugun hali yuborilmagan'
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🎲 Tasodifiy kino yuborish', callback_data='daily_send_random')], [InlineKeyboardButton(text='🔢 Kino kodi bilan yuborish', callback_data='daily_send_manual')]])
    await message.answer(with_footer(f'☀️ <b>Kun Kinosi boshqaruvi</b>\n\n📅 <b>Bugungi holat:</b> {status_text}\n\nQuyidagi tugmalardan birini tanlang:'), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'daily_send_random')
async def daily_send_random(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    movie = await db_req.get_random_movie()
    if not movie:
        await callback.message.edit_text(with_footer("❌ Bazada hali kino yo'q."))
        return
    movie_id, file_id, caption = movie
    await db_req.set_today_daily_movie(movie_id)
    users = await db_req.get_all_users()
    success = 0
    for uid in users:
        try:
            cap = f'☀️ <b>Bugungi Kun Kinosi</b>\n\n{caption or ''}\n\n🎬 Kino kodi: <code>{movie_id}</code>\n🤖 {config.BOT_USERNAME}'
            await callback.bot.send_video(uid, file_id, caption=with_footer(cap), parse_mode='HTML')
            success += 1
            import asyncio
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await callback.message.edit_text(with_footer(f'✅ <b>Kun kinosi {success} ta foydalanuvchiga yuborildi!</b>\n🎬 Kino kodi: <code>{movie_id}</code>'), parse_mode='HTML')

@router.callback_query(F.data == 'daily_send_manual')
async def daily_send_manual_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_movie_id)
    await state.update_data(daily_movie_mode=True)
    await callback.message.edit_text(with_footer('🔢 <b>Kun kinosi uchun kino kodini yuboring:</b>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_movie_id, F.text.regexp('^\\d+$'))
async def daily_movie_by_id(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get('daily_movie_mode'):
        return
    movie_id = int(message.text)
    movie = await db_req.get_movie(movie_id)
    if not movie:
        await message.answer(with_footer(f'❌ <code>{movie_id}</code> kodli kino topilmadi.'))
        return
    file_id, caption = movie
    await db_req.set_today_daily_movie(movie_id)
    await state.clear()
    users = await db_req.get_all_users()
    success = 0
    for uid in users:
        try:
            cap = f'☀️ <b>Bugungi Kun Kinosi</b>\n\n{caption or ''}\n\n🎬 Kino kodi: <code>{movie_id}</code>\n🤖 {config.BOT_USERNAME}'
            await message.bot.send_video(uid, file_id, caption=with_footer(cap), parse_mode='HTML')
            success += 1
            import asyncio
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(with_footer(f'✅ <b>Kun kinosi {success} ta foydalanuvchiga yuborildi!</b>\n🎬 Kino kodi: <code>{movie_id}</code>'), parse_mode='HTML')

@router.message(Command('leaderboard'))
async def show_leaderboard_menu(message: Message):
    """Leaderboard menyusi"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏆 TOP 10 Users (Ballar)', callback_data='top_users_points'), InlineKeyboardButton(text='👥 TOP 10 Users (Referallar)', callback_data='top_users_referrals')], [InlineKeyboardButton(text='🔥 TOP 10 Users (Faollik)', callback_data='top_users_activity'), InlineKeyboardButton(text='👨\u200d💼 TOP 10 Admins', callback_data='top_admins')], [InlineKeyboardButton(text='📊 Barcha statistika', callback_data='full_stats')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='admin_menu')]])
    await message.answer(with_footer("📊 <b>Leaderboard - Reytinglar</b>\n\nQuyidagi bo'limlardan birini tanlang:"), parse_mode='HTML', reply_markup=keyboard)

@router.callback_query(F.data == 'top_users_points')
async def show_top_users_points(callback: CallbackQuery):
    """Ballar bo'yicha TOP 10 foydalanuvchilar"""
    top_users = await db_req.get_top_users_by_points(10)
    text = "🏆 <b>TOP 10 Foydalanuvchilar (Ballar bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, (user_id, username, full_name, points, referrals_count) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = username or full_name or f'User {user_id}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f'   💰 Ball: {points:,} | 👥 Referallar: {referrals_count}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='top_users_points')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'top_users_referrals')
async def show_top_users_referrals(callback: CallbackQuery):
    """Referallar bo'yicha TOP 10 foydalanuvchilar"""
    top_users = await db_req.get_top_users_by_referrals(10)
    text = "👥 <b>TOP 10 Foydalanuvchilar (Referallar bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, (user_id, username, full_name, referrals_count, points) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = username or full_name or f'User {user_id}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f'   👥 Referallar: {referrals_count} | 💰 Ball: {points:,}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='top_users_referrals')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'top_users_activity')
async def show_top_users_activity(callback: CallbackQuery):
    """Faollik bo'yicha TOP 10 foydalanuvchilar"""
    top_users = await db_req.get_top_users_by_activity(10)
    text = "🔥 <b>TOP 10 Foydalanuvchilar (Faollik bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, (user_id, username, full_name, last_active_at, points) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = username or full_name or f'User {user_id}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f'   ⏰ Oxirgi faollik: {last_active_at}\n'
        text += f'   💰 Ball: {points:,}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='top_users_activity')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'top_admins')
async def show_top_admins(callback: CallbackQuery):
    """TOP 10 adminlar"""
    top_admins = await db_req.get_all_admins_stats()
    text = "👨\u200d💼 <b>TOP 10 Adminlar (Harakatlar bo'yicha)</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for i, admin in enumerate(top_admins, 1):
        medal = medals[i - 1] if i <= 3 else f'#{i}'
        username_display = admin['username'] or admin['full_name'] or f'Admin {admin['id']}'
        text += f'{medal} <b>{username_display}</b>\n'
        text += f"   🎬 Kinolar: {admin['movies_added']} | ✅ To'lovlar: {admin['payments_approved']}\n"
        text += f'   🔧 Boshqa: {admin['other_actions']} | 📊 Jami: {admin['total_actions']}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='top_admins')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'full_stats')
async def show_full_stats(callback: CallbackQuery):
    """To'liq statistika"""
    total_users = await db_req.get_total_users_count()
    premium_users = await db_req.get_premium_users_count()
    total_movies = await db_req.get_total_movies_count()
    total_referrals = await db_req.get_total_referrals_count()
    admins = await db_req.get_all_admins()
    text = "📊 <b>To'liq Statistika</b>\n\n"
    text += '👥 <b>Foydalanuvchilar:</b>\n'
    text += f'   📊 Jami: {total_users:,}\n'
    text += f'   💎 Premium: {premium_users:,}\n'
    text += f'   🆕 Bugun: {await db_req.get_today_users_count()}\n\n'
    text += '🎬 <b>Kinolar:</b>\n'
    text += f'   📊 Jami: {total_movies:,}\n'
    text += f'   🔥 Trending: {len(await db_req.get_trending_movies())}\n\n'
    text += '👥 <b>Referallar:</b>\n'
    text += f'   📊 Jami: {total_referrals:,}\n\n'
    text += '👨\u200d💼 <b>Adminlar:</b>\n'
    text += f'   📊 Jami: {len(admins)}\n\n'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='full_stats')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='leaderboard')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer(text), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == 'leaderboard')
async def back_to_leaderboard(callback: CallbackQuery):
    """Leaderboard menyusiga qaytish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🏆 TOP 10 Users (Ballar)', callback_data='top_users_points'), InlineKeyboardButton(text='👥 TOP 10 Users (Referallar)', callback_data='top_users_referrals')], [InlineKeyboardButton(text='🔥 TOP 10 Users (Faollik)', callback_data='top_users_activity'), InlineKeyboardButton(text='👨\u200d💼 TOP 10 Admins', callback_data='top_admins')], [InlineKeyboardButton(text='📊 Barcha statistika', callback_data='full_stats')], [InlineKeyboardButton(text='🔙 Orqaga', callback_data='admin_menu')]])
    try:
        await callback.message.edit_text(with_footer("📊 <b>Leaderboard - Reytinglar</b>\n\nQuyidagi bo'limlardan birini tanlang:"), parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        await callback.message.answer(with_footer("📊 <b>Leaderboard - Reytinglar</b>\n\nQuyidagi bo'limlardan birini tanlang:"), parse_mode='HTML', reply_markup=keyboard)
    await callback.answer()

@router.message(F.text == 'Ballar 💎')
async def admin_ballar(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        return
    leaderboard = await db_req.get_points_leaderboard(15)
    if not leaderboard:
        await message.answer(with_footer("💎 <b>Hali hech kim ball to'plamagan.</b>"), parse_mode='HTML')
        return
    text = "💎 <b>Top 15 Ball Yig'uvchilar:</b>\n\n"
    medals = ['🥇', '🥈', '🥉']
    for idx, (uid, username, full_name, pts) in enumerate(leaderboard, 1):
        name = f'@{username}' if username else full_name or str(uid)
        icon = medals[idx - 1] if idx <= 3 else f'{idx}.'
        text += f'{icon} {name} — <code>{pts}</code> 💎\n'
    await message.answer(with_footer(text), parse_mode='HTML')

@router.message(F.text == 'Sozlamalar ⚙️')
async def show_admin_config_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    pts_ref = await db_req.get_config_int('points_referral', 10)
    pts_rat = await db_req.get_config_int('points_rating', 2)
    pts_com = await db_req.get_config_int('points_comment', 3)
    daily_pts = await db_req.get_config_int('daily_points_limit', 40)
    daily_rat = await db_req.get_config_int('daily_ratings_limit', 10)
    cooldown = await db_req.get_config_int('comment_cooldown', 30)
    mod_on = await db_req.get_config_int('comment_moderation', 0)
    mod_status_str = 'Yoqilgan ✅' if mod_on == 1 else "O'chirilgan ❌"
    text = f"⚙️ <b>Bot Tizim Sozlamalari (Inline Config):</b>\n\n💎 <b>Referal balli:</b> {pts_ref} 💎\n⭐️ <b>Baholash balli:</b> {pts_rat} 💎\n💬 <b>Izoh yozish balli:</b> {pts_com} 💎\n📊 <b>Kunlik ball limiti:</b> {daily_pts} 💎\n⭐ <b>Kunlik baholash limiti:</b> {daily_rat} ta\n⏱ <b>Izoh cooldown vaqti:</b> {cooldown} soniya\n🛡 <b>Izohlar moderatsiyasi:</b> {mod_status_str}\n\n<i>Tugmalarni bosib qiymatlarni o'zgartirishingiz mumkin:</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'💎 Referal: {pts_ref} ✏️', callback_data='cfg_points_referral'), InlineKeyboardButton(text=f'⭐️ Baho: {pts_rat} ✏️', callback_data='cfg_points_rating')], [InlineKeyboardButton(text=f'💬 Izoh: {pts_com} ✏️', callback_data='cfg_points_comment'), InlineKeyboardButton(text=f'📊 Max ball: {daily_pts} ✏️', callback_data='cfg_daily_points_limit')], [InlineKeyboardButton(text=f'⭐ Max baho: {daily_rat} ✏️', callback_data='cfg_daily_ratings_limit'), InlineKeyboardButton(text=f'⏱ Cooldown: {cooldown}s ✏️', callback_data='cfg_comment_cooldown')], [InlineKeyboardButton(text=f'🛡 Moderatsiya: {('ON ✅' if mod_on == 1 else 'OFF ❌')}', callback_data='cfg_toggle_moderation')]])
    await message.answer(with_footer(text), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'cfg_toggle_moderation')
async def toggle_moderation_callback(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    current = await db_req.get_config_int('comment_moderation', 0)
    new_val = 0 if current == 1 else 1
    await db_req.set_setting('comment_moderation', str(new_val))
    status_str = 'yoqildi ✅' if new_val == 1 else "o'chirildi ❌"
    await callback.answer(f'Izohlar moderatsiyasi {status_str}', show_alert=True)
    pts_ref = await db_req.get_config_int('points_referral', 10)
    pts_rat = await db_req.get_config_int('points_rating', 2)
    pts_com = await db_req.get_config_int('points_comment', 3)
    daily_pts = await db_req.get_config_int('daily_points_limit', 40)
    daily_rat = await db_req.get_config_int('daily_ratings_limit', 10)
    cooldown = await db_req.get_config_int('comment_cooldown', 30)
    mod_status_str = 'Yoqilgan ✅' if new_val == 1 else "O'chirilgan ❌"
    text = f"⚙️ <b>Bot Tizim Sozlamalari (Inline Config):</b>\n\n💎 <b>Referal balli:</b> {pts_ref} 💎\n⭐️ <b>Baholash balli:</b> {pts_rat} 💎\n💬 <b>Izoh yozish balli:</b> {pts_com} 💎\n📊 <b>Kunlik ball limiti:</b> {daily_pts} 💎\n⭐ <b>Kunlik baholash limiti:</b> {daily_rat} ta\n⏱ <b>Izoh cooldown vaqti:</b> {cooldown} soniya\n🛡 <b>Izohlar moderatsiyasi:</b> {mod_status_str}\n\n<i>Tugmalarni bosib qiymatlarni o'zgartirishingiz mumkin:</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'💎 Referal: {pts_ref} ✏️', callback_data='cfg_points_referral'), InlineKeyboardButton(text=f'⭐️ Baho: {pts_rat} ✏️', callback_data='cfg_points_rating')], [InlineKeyboardButton(text=f'💬 Izoh: {pts_com} ✏️', callback_data='cfg_points_comment'), InlineKeyboardButton(text=f'📊 Max ball: {daily_pts} ✏️', callback_data='cfg_daily_points_limit')], [InlineKeyboardButton(text=f'⭐ Max baho: {daily_rat} ✏️', callback_data='cfg_daily_ratings_limit'), InlineKeyboardButton(text=f'⏱ Cooldown: {cooldown}s ✏️', callback_data='cfg_comment_cooldown')], [InlineKeyboardButton(text=f'🛡 Moderatsiya: {('ON ✅' if new_val == 1 else 'OFF ❌')}', callback_data='cfg_toggle_moderation')]])
    try:
        await callback.message.edit_text(with_footer(text), parse_mode='HTML', reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data.startswith('cfg_'))
async def config_edit_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    key = callback.data[len('cfg_'):]
    if key == 'toggle_moderation':
        return
    labels = {'points_referral': 'Referal uchun beriladigan ball', 'points_rating': 'Kinoni baholash uchun ball', 'points_comment': 'Izoh yozish uchun ball', 'daily_points_limit': 'Kunlik maksimal ball limiti', 'daily_ratings_limit': 'Kunlik maksimal baholashlar soni', 'comment_cooldown': 'Izohlar orasidagi kutish vaqti (soniyalarda)'}
    label = labels.get(key, key)
    await state.set_state(AdminStates.waiting_for_config_value)
    await state.update_data(config_key=key, config_label=label)
    await callback.message.answer(with_footer(f'✏️ <b>{label} uchun yangi musbat butun son kiriting:</b>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_config_value, F.text, ~F.text.in_(MENU_BUTTONS))
async def config_edit_save(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun son kiriting:'))
        return
    val = int(text)
    data = await state.get_data()
    key = data['config_key']
    label = data['config_label']
    await db_req.set_setting(key, str(val))
    await state.clear()
    await message.answer(with_footer(f'✅ <b>{label} muvaffaqiyatli saqlandi: {val}</b>'), parse_mode='HTML')

@router.message(F.text == 'Izohlar moderatsiyasi 💬')
async def show_moderation_panel(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    pending = await db_req.get_pending_comments(limit=20)
    if not pending:
        await message.answer(with_footer("🛡 <b>Izohlar Moderatsiyasi:</b>\n\nHozircha tasdiqlash kutilayotgan izohlar yo'q! ✅"), parse_mode='HTML')
        return
    await message.answer(with_footer(f'🛡 <b>Izohlar Moderatsiyasi ({len(pending)} ta kutilmoqda):</b>'), parse_mode='HTML')
    for comm_id, u_id, m_id, comm_text, username, full_name, movie_cap, created_at in pending:
        name = f'@{username}' if username else full_name or str(u_id)
        m_name = movie_cap[:30] if movie_cap else f'Kino {m_id}'
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Tasdiqlash ✅', callback_data=f'appr_comm_{comm_id}'), InlineKeyboardButton(text="O'chirish ❌", callback_data=f'rej_comm_{comm_id}')]])
        txt = f'💬 <b>Izoh #{comm_id}</b>\n🎬 <b>Kino:</b> {m_name} (Kodi: <code>{m_id}</code>)\n👤 <b>Muallif:</b> {name} (ID: <code>{u_id}</code>)\n📝 <b>Izoh:</b> <i>{comm_text}</i>\n🕒 <b>Vaqt:</b> {created_at}'
        await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('appr_comm_'))
async def approve_comment_callback(callback: CallbackQuery):
    if not await db_req.has_permission(callback.from_user.id, 'add_movie'):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    comm_id = int(callback.data.split('_')[2])
    await db_req.approve_comment(comm_id)
    await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n✅ <b>Tasdiqlandi!</b>'), parse_mode='HTML')
    await callback.answer('Izoh tasdiqlandi va chop etildi! ✅')

@router.callback_query(F.data.startswith('rej_comm_'))
async def reject_comment_callback(callback: CallbackQuery):
    if not await db_req.has_permission(callback.from_user.id, 'add_movie'):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    comm_id = int(callback.data.split('_')[2])
    await db_req.reject_comment(comm_id)
    await callback.message.edit_text(with_footer(f"{callback.message.text}\n\n❌ <b>Rad etildi va o'chirildi!</b>"), parse_mode='HTML')
    await callback.answer("Izoh o'chirildi! ❌")

@router.message(F.text.regexp('(?i).*(ommaviy yuklash).*'))
async def bulk_upload_start(message: Message, state: FSMContext):
    await state.clear()
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    await state.set_state(AdminStates.waiting_for_bulk_movies)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Yakunlash ✅ (Done)', callback_data='bulk_upload_finish')]])
    first_free = await db_req.get_next_available_movie_id()
    await message.answer(with_footer(f"🔄 <b>Ommaviy kino yuklash rejimi faollashtirildi!</b>\n\nSiz ketma-ket istalgancha video yoki hujjat shaklidagi kinolarni yuborishingiz mumkin.\n\n💡 <b>Avtomatik kodlash tartibi:</b>\n• Kinolarga avtomatik ravishda bo'sh bo'lgan eng birinchi kodlar ketma-ket beriladi (masalan: <b>{first_free}</b>, <b>{first_free + 1}</b>, <b>{first_free + 2}</b>...)\n• Agar video tavsifida (caption) aniq raqam bo'lsa (masalan: <code>501 - Spiderman</code>), bot <b>501</b> ni kino kodi deb oladi.\n\nYuklab bo'lgach, quyidagi <b>«Yakunlash ✅»</b> tugmasini bosing."), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'bulk_upload_finish')
async def bulk_upload_finish_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(with_footer('✅ <b>Ommaviy yuklash yakunlandi!</b>'), parse_mode='HTML')
    await callback.answer('Ommaviy yuklash yakunlandi ✅')

@router.message(AdminStates.waiting_for_bulk_movies)
async def bulk_upload_process(message: Message, state: FSMContext):
    if message.text:
        if message.text in MENU_BUTTONS or message.text.startswith('/'):
            await state.clear()
            if message.text == '/start' or message.text == '/cancel':
                from handlers.user import execute_start_logic
                await execute_start_logic(message, state)
            return
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.animation:
        file_id = message.animation.file_id
    elif message.video_note:
        file_id = message.video_note.file_id
    if not file_id:
        await message.answer(with_footer('⚠️ Iltimos, kino video faylini yuboring yoki «Yakunlash ✅» tugmasini bosing.'))
        return
    raw_caption = (message.caption or '').strip()
    import re
    code_match = re.match('^(\\d+)\\s*[-:]?\\s*(.*)$', raw_caption, re.DOTALL)
    movie_id = None
    movie_caption = raw_caption
    if code_match:
        target_id = int(code_match.group(1))
        candidate_cap = code_match.group(2).strip()
        existing = await db_req.movie_exists_db(target_id)
        if not existing:
            movie_id = target_id
            movie_caption = candidate_cap
    if movie_id is None:
        movie_id = await db_req.get_next_available_movie_id()
    formatted_caption = db_req.clean_and_format_caption(movie_caption)
    await db_req.add_movie_with_id(movie_id, file_id, formatted_caption)
    await sync_movies_backup_storage(message.bot)
    total_movies = await db_req.get_total_movies_count()
    next_free = await db_req.get_next_available_movie_id()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎬 Kinoni Ko'rish", callback_data=f'get_movie_{movie_id}'), InlineKeyboardButton(text='✏️ Tahrirlash', callback_data=f'edit_movie_start_{movie_id}')], [InlineKeyboardButton(text='🏁 Yakunlash ✅ (Done)', callback_data='bulk_upload_finish')]])
    cap_display = movie_caption[:50] if movie_caption else '(Nomsiz video fayl)'
    await message.answer(with_footer(f"✅ <b>KINO OMMAVIY MUVAFFAQIYATLI YUKLANDI!</b>\n\n📌 <b>Nomi / Tavsifi:</b> <i>{cap_display}</i>\n🎬 <b>Biriktirilgan Kod:</b> <code>{movie_id}</code>\n📊 <b>Bazadagi jami kinolar:</b> <code>{total_movies} ta</code>\n💡 <b>Navbatdagi bo'sh kod:</b> <code>{next_free}</code>\n\n<i>Kino avtomatik SQLite hamda MongoDB Atlas Cloud bazangizga saqlandi! Yana yuborishingiz mumkin.</i>"), parse_mode='HTML', reply_markup=kb)

@router.message(F.text == '🚫 Bloklanganlar')
async def show_banned_users_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    banned = await db_req.get_banned_users_list()
    if not banned:
        await message.answer(with_footer("🚫 <b>Bloklangan foydalanuvchilar yo'q.</b>"), parse_mode='HTML')
        return
    await message.answer(with_footer(f"🚫 <b>Bloklangan foydalanuvchilar ro'yxati ({len(banned)} ta):</b>"), parse_mode='HTML')
    for u_id, username, full_name, role in banned[:20]:
        name = f'@{username}' if username else full_name or str(u_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔓 Blokdan chiqarish (Unban)', callback_data=f'unban_usr_{u_id}')]])
        txt = f'👤 <b>Foydalanuvchi:</b> {name}\n🆔 <b>ID:</b> <code>{u_id}</code>\n🚫 <b>Holati:</b> Bloklangan (Banned)'
        await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('unban_usr_'))
async def unban_user_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[2])
    success = await db_req.unban_user(u_id)
    if success:
        user_sent = False
        try:
            unban_msg = "🔓 <b>HISOBINGIZ BLOKDAN CHIQARILDI!</b>\n\nHurmatli foydalanuvchi, sizning hisobingiz administrator tomonidan blokdan chiqarildi. Endi botdan qayta to'liq foydalanishingiz mumkin! 🍿"
            await callback.bot.send_message(with_footer(u_id), unban_msg, parse_mode='HTML')
            user_sent = True
        except Exception:
            user_sent = False
        status_note = 'va foydalanuvchiga bildirishnoma yuborildi 📩' if user_sent else '(Foydalanuvchi botni bloklagan)'
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n✅ <b>Blokdan chiqarildi {status_note}!</b>'), parse_mode='HTML')
        await callback.answer(f'Foydalanuvchi blokdan chiqarildi! {status_note}', show_alert=True)
    else:
        await callback.answer('Xatolik yuz berdi!', show_alert=True)

@router.callback_query(F.data.startswith('warn_usr_'))
async def warn_user_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[2])
    is_banned, cnt, dur_txt, stage = await db_req.warn_user_progressive(u_id)
    if is_banned:
        try:
            await callback.bot.send_message(with_footer(u_id), f'⚠️ <b>Sizga 3 ta ogohlantirish berildi!</b>\n\nHisobingiz <b>{dur_txt}</b> muddatga avtomatik bloklandi.', parse_mode='HTML')
        except Exception:
            pass
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n⚠️ <b>3-ogohlantirish berildi! Foydalanuvchi {dur_txt} ga bloklandi.</b>'), parse_mode='HTML')
        await callback.answer(f'Foydalanuvchiga 3-ogohlantirish berildi ({dur_txt} ban)!', show_alert=True)
    else:
        try:
            await callback.bot.send_message(with_footer(u_id), f'⚠️ <b>OGOHLANTIRISH!</b>\n\nSiz bot qoidalarini buzdingiz ({cnt}/3). Iltimos, spam bermang va odob saqlang!', parse_mode='HTML')
        except Exception:
            pass
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n⚠️ <b>Ogohlantirish yuborildi ({cnt}/3)!</b>'), parse_mode='HTML')
        await callback.answer(f'Ogohlantirish yuborildi ({cnt}/3)! ⚠️', show_alert=True)

@router.callback_query(F.data.startswith('admin_ban_'))
async def admin_ban_start_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[2])
    from keyboards.inline import get_ban_duration_keyboard
    await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n⏳ <b>Bloklash muddatini tanlang:</b>'), parse_mode='HTML', reply_markup=get_ban_duration_keyboard(u_id))
    await callback.answer()

@router.callback_query(F.data.startswith('do_ban_'))
async def execute_ban_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split('_')
    u_id = int(parts[2])
    dur_code = parts[3]
    dur_map = {'1h': (1, '1 soat'), '24h': (24, '24 soat (1 kun)'), '7d': (168, '7 kun (1 hafta)'), '30d': (720, '30 kun (1 oy)'), 'perm': (None, 'Doimiy (Permanent)')}
    hours, dur_text = dur_map.get(dur_code, (None, 'Doimiy'))
    await db_req.ban_user_custom(u_id, hours=hours)
    try:
        user_msg = f'🚫 <b>HISOBINGIZ BLOKLANDI!</b>\n\n<b>Bloklash muddati:</b> <code>{dur_text}</code>\n<i>Qoidabuzarlik sababli botdan foydalanishingiz cheklandi.</i>'
        await callback.bot.send_message(with_footer(u_id), user_msg, parse_mode='HTML')
    except Exception:
        pass
    await callback.message.edit_text(with_footer(f'🚫 <b>Foydalanuvchi (ID: <code>{u_id}</code>) {dur_text} muddatga muvaffaqiyatli bloklandi!</b>'), parse_mode='HTML')
    await callback.answer(f'Foydalanuvchi {dur_text} ga bloklandi! 🚫', show_alert=True)

@router.callback_query(F.data.startswith('cancel_ban_'))
async def cancel_ban_callback(callback: CallbackQuery):
    u_id = int(callback.data.split('_')[2])
    from keyboards.inline import get_abuse_action_keyboard
    await callback.message.edit_text(with_footer(f'🚨 <b>SHOSHILINCH OGOHLANTIRISH! (Spam Alert)</b>\n\n👤 <b>Foydalanuvchi ID:</b> <code>{u_id}</code>\n⚠️ <i>Boshqaruv paneli orqali ushbu foydalanuvchini bloklashingiz mumkin.</i>'), parse_mode='HTML', reply_markup=get_abuse_action_keyboard(u_id))
    await callback.answer('Bekor qilindi.')

@router.callback_query(F.data.startswith('reply_ticket_'))
async def reply_ticket_callback(callback: CallbackQuery, state: FSMContext):
    if not await db_req.has_permission(callback.from_user.id, 'add_movie'):
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    ticket_id = int(callback.data.split('_')[2])
    ticket = await db_req.get_ticket(ticket_id)
    if not ticket:
        await callback.answer('❌ Ushbu ticket topilmadi!', show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_ticket_reply)
    await state.update_data(reply_ticket_id=ticket_id, reply_ticket_user_id=ticket[1])
    await callback.message.answer(with_footer(f'✍️ <b>Ticket #{ticket_id} uchun javob xabaringizni yozib yuboring:</b>\n\n<i>Murojaat matni:</i> {ticket[2]}'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_ticket_reply, ~F.text.in_(MENU_BUTTONS))
async def save_ticket_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data['reply_ticket_id']
    user_id = data['reply_ticket_user_id']
    reply_text = message.text or message.caption or '(Media / Rasm / Stiker javob)'
    success = await db_req.reply_to_ticket(ticket_id, message.from_user.id, reply_text)
    await state.clear()
    if success:
        try:
            await message.bot.send_message(with_footer(user_id), f'📩 <b>Admin sizning murojaatingizga javob berdi:</b>', parse_mode='HTML')
            await message.copy_to(chat_id=user_id)
            await message.answer(with_footer(f"✅ <b>Ticket #{ticket_id} bo'yicha javob foydalanuvchiga muvaffaqiyatli yuborildi!</b>"), parse_mode='HTML')
        except Exception as e:
            await message.answer(with_footer(f'⚠️ Javob saqlandi, lekin foydalanuvchiga xabar yetkazishda xatolik: {e}'))
    else:
        await message.answer(with_footer('❌ Xatolik yuz berdi. Javob saqlanmadi.'))

@router.message(Command('setpin'))
async def set_admin_pin_cmd(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        pin = args[1].strip()
        if not pin.isdigit() or len(pin) < 4 or len(pin) > 30:
            await message.answer(with_footer("⚠️ <b>PIN-kod faqat raqamlardan iborat va 4 dan 30 xonagacha bo'lishi kerak!</b>"), parse_mode='HTML')
            return
        await db_req.set_admin_pin(message.from_user.id, pin)
        await message.answer(with_footer('✅ <b>2FA Admin PIN-kodingiz muvaffaqiyatli saqlandi!</b>'), parse_mode='HTML')
    else:
        await state.set_state(AdminStates.waiting_for_setpin)
        await message.answer(with_footer('🔐 <b>Yangi 2FA Admin PIN-kodingizni kiriting:</b>\n\n<i>Eslatma: Faqat raqamlar kiritilishi lozim (uzunligi minimum 4, maksimum 30 xona).</i>'), parse_mode='HTML')

@router.message(AdminStates.waiting_for_setpin, F.text, ~F.text.in_(MENU_BUTTONS))
async def save_admin_pin_state(message: Message, state: FSMContext):
    pin = message.text.strip()
    if not pin.isdigit() or len(pin) < 4 or len(pin) > 30:
        await message.answer(with_footer("⚠️ <b>Noto'g'ri PIN! Faqat raqamlardan iborat va 4 dan 30 xonagacha bo'lishi kerak!</b>"), parse_mode='HTML')
        return
    await db_req.set_admin_pin(message.from_user.id, pin)
    await state.clear()
    await message.answer(with_footer('✅ <b>Yangi 2FA Admin PIN-kodingiz muvaffaqiyatli saqlandi va faollashtirildi!</b>'), parse_mode='HTML')

@router.message(Command('user'))
async def search_user_cmd(message: Message, state: FSMContext):
    if not await db_req.has_permission(message.from_user.id, 'add_movie'):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await state.set_state(AdminStates.waiting_for_user_search)
        await message.answer(with_footer("🔎 <b>Qidirmoqchi bo'lgan foydalanuvchi ID si yoki @username'ini kiriting:</b>"), parse_mode='HTML')
        return
    query = args[1].strip()
    await process_user_search(message, query)

@router.message(AdminStates.waiting_for_user_search, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_user_search_state(message: Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    await process_user_search(message, query)

async def process_user_search(message: Message, query: str):
    from keyboards.inline import get_user_manage_keyboard
    user = await db_req.search_user_by_query(query)
    if not user:
        await message.answer(with_footer(f"❌ <code>{query}</code> bo'yicha foydalanuvchi topilmadi."), parse_mode='HTML')
        return
    u_id, username, full_name, role, status, points, referrals_count, created_at, birthday = user
    name_display = f'@{username}' if username else full_name or str(u_id)
    level_name, level_emoji, _ = db_req.get_user_level(points)
    bday_display = birthday if birthday else 'Kiritilmagan ❌'
    txt = f"👤 <b>FOYDALANUVCHI MA'LUMOTLARI:</b>\n\n🆔 <b>ID:</b> <code>{u_id}</code>\n👤 <b>Ismi / Username:</b> {name_display}\n🎭 <b>Rol:</b> <code>{role}</code> | <b>Holati:</b> <code>{status}</code>\n💎 <b>Ballari:</b> <code>{points}</code> 💎 ({level_emoji} {level_name})\n👥 <b>Referallari:</b> {referrals_count} ta\n🎂 <b>Tug'ilgan kuni:</b> {bday_display}\n📅 <b>Ro'yxatdan o'tgan:</b> {created_at}\n\n<i>Boshqarish uchun tugmalardan foydalaning:</i>"
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=get_user_manage_keyboard(u_id))

@router.callback_query(F.data.startswith('admin_ban_'))
async def admin_ban_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[2])
    await db_req.ban_user(u_id)
    await callback.answer('Foydalanuvchi doimiy bloklandi 🚫', show_alert=True)
    await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n🚫 <b>Holati: Doimiy Bloklangan!</b>'), parse_mode='HTML')

@router.callback_query(F.data.startswith('admin_unban_'))
async def admin_unban_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[2])
    await db_req.unban_user(u_id)
    user_sent = False
    try:
        unban_msg = "🔓 <b>HISOBINGIZ BLOKDAN CHIQARILDI!</b>\n\nHurmatli foydalanuvchi, sizning hisobingiz administrator tomonidan blokdan chiqarildi. Endi botdan qayta to'liq foydalanishingiz mumkin! 🍿"
        await callback.bot.send_message(with_footer(u_id), unban_msg, parse_mode='HTML')
        user_sent = True
    except Exception:
        user_sent = False
    status_note = 'va foydalanuvchiga bildirishnoma yuborildi 📩' if user_sent else '(Foydalanuvchi botni bloklagan)'
    await callback.answer(f'Foydalanuvchi blokdan chiqarildi 🔓 {status_note}', show_alert=True)
    await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n🔓 <b>Holati: Faol (Unbanned) {status_note}!</b>'), parse_mode='HTML')

@router.callback_query(F.data.startswith('admin_addpts_'))
async def admin_addpts_callback(callback: CallbackQuery):
    parts = callback.data.split('_')
    u_id = int(parts[2])
    pts = int(parts[3])
    new_pts = await db_req.add_points_to_user(u_id, pts)
    await callback.answer(f"+{pts} ball qo'shildi! Jami: {new_pts} 💎", show_alert=True)

@router.callback_query(F.data.startswith('admin_subpts_'))
async def admin_subpts_callback(callback: CallbackQuery):
    parts = callback.data.split('_')
    u_id = int(parts[2])
    pts = int(parts[3])
    new_pts = await db_req.add_points_to_user(u_id, -pts)
    await callback.answer(f'-{pts} ball ayirildi! Jami: {new_pts} 💎', show_alert=True)

@router.callback_query(F.data.startswith('admin_premium_'))
async def admin_premium_callback(callback: CallbackQuery):
    u_id = int(callback.data.split('_')[2])
    await db_req.set_user_premium(u_id, days=7)
    await callback.answer('Foydalanuvchiga 7 kunlik Premium berildi 👑', show_alert=True)

@router.callback_query(F.data.startswith('admin_approve_prem_'))
async def admin_approve_prem_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split('_')
    u_id = int(parts[3])
    days = int(parts[4]) if len(parts) > 4 else 30
    amount = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 55000 if days == 90 else 20000
    await db_req.set_user_premium(u_id, days=days)
    period_text = f'{days // 30} oylik' if days % 30 == 0 else f'{days} kunlik'
    plan_str = f'{period_text} Premium'
    await db_req.add_payment_record(u_id, amount, plan_str, confirmed_by=callback.from_user.id)
    try:
        user_msg = f"🎉 <b>TO'LOV TASDIQLANDI!</b>\n\nHurmatli foydalanuvchi, sizning to'lov chekingiz adminlar tomonidan tasdiqlandi va sizga <b>{period_text} Premium obunasi</b> faollashtirildi! 👑\n\n<i>Endi botimizdan kunlik cheklovlarsiz va barcha imtiyozlar bilan foydalanishingiz mumkin! Maroqli hordiq chiqaring!</i> 🍿"
        await callback.bot.send_message(with_footer(u_id), user_msg, parse_mode='HTML')
    except Exception:
        pass
    await callback.answer(f'✅ {period_text} Premium faollashtirildi!', show_alert=True)
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ <b>To'lov tasdiqlandi: {period_text} Premium berildi!</b>", parse_mode='HTML')
        else:
            await callback.message.edit_text(text=f"{callback.message.text}\n\n✅ <b>To'lov tasdiqlandi: {period_text} Premium berildi!</b>", parse_mode='HTML')
    except Exception:
        pass

@router.callback_query(F.data.startswith('admin_reject_receipt_'))
async def admin_reject_receipt_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[3])
    try:
        user_msg = f"❌ <b>TO'LOV CHEKI QABUL QILINMADI!</b>\n\nHurmatli foydalanuvchi, siz yuborgan to'lov cheki yaroqsiz (xato) yoki hisobimizga pul tushmagan bo'lishi mumkin.\n\n<i>Iltimos, to'lov chekini (skrinshotini) to'g'ri va aniq ko'rinadigan holda qayta yuboring yoki adminlarga murojaat qiling.</i> 📩"
        await callback.bot.send_message(with_footer(u_id), user_msg, parse_mode='HTML')
        user_sent = True
    except Exception:
        user_sent = False
    await callback.answer('❌ Chek rad etildi va foydalanuvchiga xabar yuborildi!', show_alert=True)
    try:
        note = '(Foydalanuvchiga xabar yuborildi)' if user_sent else '(Foydalanuvchi botni bloklagan)'
        if callback.message.caption:
            await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ <b>To'lov cheki rad etildi (Xato/pul tushmagan)! {note}</b>", parse_mode='HTML')
        else:
            await callback.message.edit_text(text=f"{callback.message.text}\n\n❌ <b>To'lov cheki rad etildi (Xato/pul tushmagan)! {note}</b>", parse_mode='HTML')
    except Exception:
        pass

@router.callback_query(F.data.startswith('admin_warn_receipt_'))
async def admin_warn_receipt_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[3])
    warn_count, is_banned, ban_until, stage = await db_req.warn_user_progressive(u_id, reason='fake_receipt')
    try:
        if is_banned:
            user_msg = f"🚨 <b>HISOBINGIZ VAQTINCHALIK BLOKLANDI!</b>\n\nSiz <b>3 marta</b> ogohlantirish oldingiz! (Sabab: Soxta/xato to'lov cheki yuborish).\n⏳ <b>Bloklash muddati:</b> <code>{ban_until}</code> gacha.\n\n<i>Iltimos, bot qoidalariga amal qiling!</i>"
        else:
            user_msg = f"⚠️ <b>OGOHLANTIRISH!</b>\n\nHurmatli foydalanuvchi, siz noto'g'ri yoki soxta to'lov chekini yuborganingiz sababli administratorlar tomonidan ogohlantirildingiz!\n\n📊 <b>Sizdagi ogohlantirishlar:</b> {warn_count}/3 ta\n<i>(Eslatma: 3 ta ogohlantirishdan so'ng hisobingiz avtomatik bloklanadi)</i> 🚨"
        await callback.bot.send_message(with_footer(u_id), user_msg, parse_mode='HTML')
        user_sent = True
    except Exception:
        user_sent = False
    status_msg = f'⚠️ Foydalanuvchiga ogohlantirish ({warn_count}/3) berildi!' if not is_banned else f'🚨 3-ogohlantirish! Foydalanuvchi {ban_until} gacha avto-bloklandi!'
    await callback.answer(status_msg, show_alert=True)
    try:
        note = f'(Ogohlantirish: {warn_count}/3)'
        if callback.message.caption:
            await callback.message.edit_caption(caption=f'{callback.message.caption}\n\n⚠️ <b>Foydalanuvchiga ogohlantirish yuborildi {note}!</b>', parse_mode='HTML')
        else:
            await callback.message.edit_text(text=f'{callback.message.text}\n\n⚠️ <b>Foydalanuvchiga ogohlantirish yuborildi {note}!</b>', parse_mode='HTML')
    except Exception:
        pass

@router.callback_query(F.data.startswith('admin_ban_receipt_'))
async def admin_ban_receipt_callback(callback: CallbackQuery):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    u_id = int(callback.data.split('_')[3])
    await db_req.ban_user(u_id)
    try:
        user_msg = f"🚫 <b>HISOBINGIZ BLOKLANDI!</b>\n\nHurmatli foydalanuvchi, soxta yoki noto'g'ri to'lov chekini yuborganingiz sababli hisobingiz administratorlar tomonidan bloklandi.\n\n<i>Bot qoidalariga rioya qilishingizni so'raymiz!</i> 🛑"
        await callback.bot.send_message(with_footer(u_id), user_msg, parse_mode='HTML')
        user_sent = True
    except Exception:
        user_sent = False
    status_note = 'va foydalanuvchiga xabar yuborildi 📩' if user_sent else '(Foydalanuvchi botni bloklagan)'
    await callback.answer(f'🚫 Foydalanuvchi bloklandi {status_note}', show_alert=True)
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=f'{callback.message.caption}\n\n🚫 <b>Foydalanuvchi bloklandi! {status_note}</b>', parse_mode='HTML')
        else:
            await callback.message.edit_text(text=f'{callback.message.text}\n\n🚫 <b>Foydalanuvchi bloklandi! {status_note}</b>', parse_mode='HTML')
    except Exception:
        pass

@router.callback_query(F.data.startswith('admin_resetbday_'))
async def admin_resetbday_callback(callback: CallbackQuery):
    u_id = int(callback.data.split('_')[2])
    async with db_req.get_db() as db:
        await db.execute('UPDATE users SET birthday = NULL WHERE id = ?', (u_id,))
        await db.commit()
    await callback.answer("Tug'ilgan kuni tozalandi! Endi u qayta kiritishi mumkin. 🎂", show_alert=True)

@router.message(Command('cleanup_inactive'))
async def cleanup_inactive_cmd(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    inactives = await db_req.get_inactive_users(days=90)
    if not inactives:
        await message.answer(with_footer("🧹 <b>3 oy davomida nofaol bo'lgan foydalanuvchilar topilmadi.</b>"), parse_mode='HTML')
        return
    await state.set_state(AdminStates.waiting_for_inactive_confirm)
    await state.update_data(inactive_ids=[u[0] for u in inactives])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"Ha, {len(inactives)} ta foydalanuvchini o'chirish 🧹", callback_data='confirm_clean_inactives'), InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await message.answer(with_footer(f"🧹 <b>Nofaol foydalanuvchilarni tozalash (3 oy+):</b>\n\nOxirgi 90 kun ichida botga kirmagan <b>{len(inactives)} ta</b> foydalanuvchi topildi.\nUlarni bazadan butunlay o'chirishni tasdiqlaysizmi?"), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'confirm_clean_inactives')
async def confirm_clean_inactives_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ids = data.get('inactive_ids', [])
    await state.clear()
    if ids:
        deleted = await db_req.delete_users_batch(ids)
        await callback.message.edit_text(with_footer(f"✅ <b>{deleted} ta nofaol foydalanuvchi bazadan o'chirildi!</b>"), parse_mode='HTML')
    else:
        await callback.message.edit_text(with_footer("O'chirish uchun foydalanuvchilar topilmadi."))
    await callback.answer()

@router.message(F.text == 'Card 💳')
async def show_admin_card_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    card_number = await db_req.get_admin_card_number()
    from keyboards.inline import get_admin_card_keyboard
    if card_number:
        txt = f'💳 <b>Hozirgi karta raqamingiz:</b>\n\n<code>{card_number}</code>'
        kb = get_admin_card_keyboard(card_exists=True)
    else:
        txt = "💳 <b>Hozircha karta raqami kiritilmagan.</b>\n\nKarta raqamini qo'shish uchun quyidagi tugmani bosing:"
        kb = get_admin_card_keyboard(card_exists=False)
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

def format_card_number_text(raw_text: str) -> str:
    """16 xonali karta raqamini har 4 ta raqamdan so'ng bo'shliq (space) bilan formatlaydi"""
    import re

    def replacer(match):
        digits = match.group(0)
        return f'{digits[0:4]} {digits[4:8]} {digits[8:12]} {digits[12:16]}'
    return re.sub('\\b\\d{16}\\b', replacer, raw_text)

@router.callback_query(F.data == 'admin_card_edit')
async def edit_admin_card_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_card_number)
    await callback.message.answer(with_footer('✏️ <b>Yangi karta raqamini va karta egasining ismini kiriting:</b>\n\n<i>Masalan: 5614681820328148 GANIYEV ABDULXAY</i>\n<i>(Bot 16 xonali raqamlarni avtomatik 4 tadan joy ajratib saqlaydi)</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_card_number, F.text, ~F.text.in_(MENU_BUTTONS))
async def save_admin_card_handler(message: Message, state: FSMContext):
    card_text = message.text.strip()
    formatted_card = format_card_number_text(card_text)
    await db_req.set_admin_card_number(formatted_card)
    await state.clear()
    from keyboards.inline import get_admin_card_keyboard
    kb = get_admin_card_keyboard(card_exists=True)
    await message.answer(with_footer(f'✅ <b>Karta raqami muvaffaqiyatli saqlandi!</b>\n\n💳 <b>Karta:</b> <code>{formatted_card}</code>'), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'admin_card_delete')
async def delete_admin_card_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.clear()
    await db_req.delete_admin_card_number()
    from keyboards.inline import get_admin_card_keyboard
    kb = get_admin_card_keyboard(card_exists=False)
    await callback.message.edit_text(with_footer("❌ <b>Karta raqami o'chirildi!</b>\n\nYangi karta raqamini qo'shishingiz mumkin."), parse_mode='HTML', reply_markup=kb)
    await callback.answer("Karta raqami o'chirildi ❌")

@router.message(F.text == 'Limit ⏳')
async def show_bonus_limit_panel(message: Message, state: FSMContext):
    await state.clear()
    db_admins = await db_req.get_all_admins()
    if message.from_user.id not in config.ADMINS and message.from_user.id not in db_admins:
        await message.answer(with_footer('❌ Bu amal faqat Adminlar uchun ruxsat etilgan.'))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📢 Foydalanuvchilarga bonus', callback_data='limit_target_ordinary')], [InlineKeyboardButton(text="⚡ Oxirgi 7 kunda faol bo'lganlar", callback_data='limit_target_active7d')], [InlineKeyboardButton(text='❌ Bekor qilish', callback_data='bc_cancel')]])
    await message.answer(with_footer("⏳ <b>Kunlik bonus limitini sozlash:</b>\n\nFoydalanuvchilarga bugungi kun uchun qo'shimcha bonus kino ko'rish limitini berish uchun maqsadli auditoriyani tanlang:\n\n<i>Eslatma: Berilgan bonus limit faqat bugungi kun uchun amal qiladi va ertaga avtomatik 0 ga tushib, standart 3 ta limit qaytadi.</i>"), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('limit_target_'))
async def limit_target_callback(callback: CallbackQuery, state: FSMContext):
    db_admins = await db_req.get_all_admins()
    if callback.from_user.id not in config.ADMINS and callback.from_user.id not in db_admins:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    target_type = callback.data.split('_')[2]
    target_label = 'Foydalanuvchilar' if target_type == 'ordinary' else "Oxirgi 7 kunda faol bo'lganlar"
    await state.set_state(AdminStates.waiting_for_bonus_limit_value)
    await state.update_data(bonus_target_type=target_type, bonus_target_label=target_label)
    await callback.message.edit_text(with_footer(f"🎯 <b>Tanlangan auditoriya:</b> {target_label}\n\n🔢 <b>Ushbu foydalanuvchilarga bugungi kun uchun necha ta bonus kino kodi kiritish limiti qo'shilsin?</b>\n\n<i>Iltimos, butun raqam yuboring (masalan: 1, 2, 3, 5):</i>"), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_bonus_limit_value, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_bonus_limit_value(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun son (masalan: 1, 2, 3) kiriting:'))
        return
    bonus_amount = int(text)
    data = await state.get_data()
    target_type = data.get('bonus_target_type', 'ordinary')
    target_label = data.get('bonus_target_label', 'Foydalanuvchilar')
    await state.clear()
    if target_type == 'active7d':
        target_users = await db_req.get_target_users('active_7d')
    else:
        target_users = await db_req.get_target_users('ordinary')
    if not target_users:
        await message.answer(with_footer('❌ Belgilangan guruhda foydalanuvchilar topilmadi.'))
        return
    saved_cnt = await db_req.add_daily_bonus_limit_batch(target_users, bonus_amount)
    sent_cnt = 0
    notify_msg = f"🎁 <b>BUGUN UCHUN BONUS KINO LIMITI!</b>\n\nHurmatli foydalanuvchi, sizga bugungi kun uchun <b>+{bonus_amount} ta</b> qo'shimcha kino ko'rish bonusi berildi! 🎬\n\n<i>Eslatma: Ushbu bonus faqat bugungi kun uchun amal qiladi. Bugun maroqli kino tomosha qiling!</i> 🍿"
    for uid in target_users:
        try:
            await message.bot.send_message(with_footer(uid), notify_msg, parse_mode='HTML')
            sent_cnt += 1
            import asyncio
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await message.answer(with_footer(f'✅ <b>BONUS KINO LIMITI MUVAFFAQIYATLI BERILDI!</b>\n\n🎯 <b>Auditoriya:</b> {target_label}\n🎁 <b>Bonus miqdori:</b> +{bonus_amount} ta kino\n👥 <b>Bonus berilganlar:</b> {saved_cnt} ta\n📩 <b>Bildirishnoma yetkazildi:</b> {sent_cnt} ta\n\n<i>Ushbu bonus faqat bugungi kun uchun amal qiladi, ertaga avtomatik ravishda 0 ga tushib standart limit tiklanadi.</i>'), parse_mode='HTML')

@router.message(F.text == 'Kassa 💰')
async def show_kassa_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS and (not await db_req.has_permission(message.from_user.id, 'view_stats')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    kassa_total = await db_req.get_kassa_total()
    payments = await db_req.get_recent_payments(limit=10)
    txt = f'💰 <b>BOT KASSA HISOBOTI:</b>\n\n'
    txt += f'💵 <b>Hozirgi Kassa Balansi:</b> <code>{kassa_total:,} UZS</code>\n\n'
    if payments:
        txt += "📋 <b>So'nggi 10 ta to'lovlar tarixi (Namangan / Uzb vaqti):</b>\n\n"
        for p_id, u_id, amount, plan, created_at, username, full_name in payments:
            name = f'@{username}' if username else full_name or str(u_id)
            time_str = str(created_at)[:19] if created_at else '—'
            txt += f'• 👤 {name} — <b>{amount:,} UZS</b> ({plan})\n  🕒 <i>{time_str}</i>\n'
    else:
        txt += "📋 <i>Hali to'lovlar tarixi mavjud emas.</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ To'lov qo'shish", callback_data='kassa_add_payment_start')],
        [InlineKeyboardButton(text='♻️ Kassani 0 ga tenglash', callback_data='kassa_reset_confirm')]
    ])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'kassa_add_payment_start')
async def kassa_add_payment_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS and not await db_req.has_permission(callback.from_user.id, 'manage_sponsors'):
        await callback.answer("❌ Bu amal uchun sizda ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_kassa_add_amount)
    await callback.message.answer(
        with_footer("➕ <b>KASSAGA TO'LOV QO'SHISH</b>\n\nKassaga qo'shmoqchi bo'lgan summani so'mda kiriting (masalan: <code>14000</code> yoki <code>50000</code>):"),
        parse_mode='HTML'
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_kassa_add_amount, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_kassa_add_amount(message: Message, state: FSMContext):
    txt_input = message.text.strip()
    if not txt_input.isdigit() or int(txt_input) <= 0:
        await message.answer(with_footer("⚠️ Iltimos, faqat musbat son kiriting (masalan: 14000):"))
        return
    amount = int(txt_input)
    await state.clear()
    admin_id = message.from_user.id
    new_total = await db_req.add_payment_record(
        user_id=admin_id,
        amount=amount,
        plan="Manual Admin To'lov",
        confirmed_by=admin_id
    )
    await message.answer(
        with_footer(
            f"✅ <b>KASSAGA TO'LOV MUVAFFAQIYATLI QO'SHILDI!</b> 💰\n\n"
            f"💵 <b>Qo'shilgan summa:</b> <code>{amount:,} UZS</code>\n"
            f"📊 <b>Yangi Kassa Balansi:</b> <code>{new_total:,} UZS</code>"
        ),
        parse_mode='HTML'
    )

@router.callback_query(F.data == 'kassa_reset_confirm')
async def kassa_reset_confirm_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan!', show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Ha, 0 ga tenglash ♻️', callback_data='kassa_reset_exec'), InlineKeyboardButton(text='Bekor qilish ❌', callback_data='bc_cancel')]])
    await callback.message.edit_text(with_footer('⚠️ <b>Kassani 0 ga tenglashni tasdiqlaysizmi?</b>\n\nHozirgi kassa balansi 0 UZS ga tushadi va statistikalar qayta hisoblanadi.'), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == 'kassa_reset_exec')
async def kassa_reset_exec_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await db_req.reset_kassa()
    await callback.message.edit_text(with_footer('✅ <b>Kassa balansi muvaffaqiyatli 0 UZS ga tenglandi!</b>'), parse_mode='HTML')
    await callback.answer('Kassa 0 ga tenglandi ♻️')

@router.message(F.text == 'Promo Kodlar 🎁')
async def show_promo_codes_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    codes = await db_req.get_all_promo_codes()
    txt = '🎁 <b>PROMO KODLAR BOSHQARUVI:</b>\n\n'
    if codes:
        for code, r_type, r_val, max_u, used_c, exp_at in codes:
            r_str = f'{r_val} kun Premium' if r_type == 'days' else f'{r_val}% skidka' if r_type == 'discount' else f'{r_val} ball'
            txt += f'🔑 <code>{code}</code> — {r_str} | {used_c}/{max_u}\n'
    else:
        txt += "<i>Mavjud promo kodlar yo'q.</i>\n"
    rows = []
    if codes:
        for code, r_type, r_val, max_u, used_c, exp_at in codes:
            rows.append([InlineKeyboardButton(text=f'✏️ {code}', callback_data=f'pedit_menu_{code}'), InlineKeyboardButton(text='🗑️', callback_data=f'pdel_ask_{code}')])
    rows.append([InlineKeyboardButton(text='➕ Yangi Promo Kod Yaratish', callback_data='promo_create_start')])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('pdel_ask_'))
async def promo_delete_confirm_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    code = callback.data.replace('pdel_ask_', '')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f'pdel_ok_{code}'), InlineKeyboardButton(text='❌ Bekor qilish', callback_data='pdel_cancel')]])
    await callback.message.answer(with_footer(f"🗑️ <b>Rostdan ham <code>{code}</code> promo kodini o'chirmoqchimisiz?</b>"), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith('pdel_ok_'))
async def promo_delete_exec_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    code = callback.data.replace('pdel_ok_', '')
    await db_req.delete_promo_code(code)
    await callback.message.edit_text(with_footer(f"✅ <b><code>{code}</code> promo kodi muvaffaqiyatli o'chirildi!</b>"), parse_mode='HTML')
    await callback.answer("O'chirildi ✅")

@router.callback_query(F.data == 'pdel_cancel')
async def promo_del_cancel_cb(callback: CallbackQuery):
    await callback.message.edit_text(with_footer("❌ <b>O'chirish bekor qilindi.</b>"), parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data.startswith('pedit_menu_'))
async def promo_edit_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    code = callback.data.replace('pedit_menu_', '')
    info = await db_req.get_promo_code_info(code)
    if not info:
        await callback.answer('❌ Promo kod topilmadi!', show_alert=True)
        return
    r_type = info['reward_type']
    r_val = info['reward_value']
    max_u = info['max_uses']
    used_c = info['used_count']
    exp_at = info['expires_at']
    r_str = f'{r_val} kun Premium' if r_type == 'days' else f'{r_val}% skidka' if r_type == 'discount' else f'{r_val} ball'
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔑 Kod nomini o'zgartirish", callback_data=f'pedit_name_{code}')], [InlineKeyboardButton(text="✏️ Qiymatini o'zgartirish", callback_data=f'pedit_val_{code}')], [InlineKeyboardButton(text="🔢 Limitini o'zgartirish", callback_data=f'pedit_lim_{code}')], [InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f'pdel_ask_{code}')], [InlineKeyboardButton(text='◀️ Orqaga', callback_data='promo_back')]])
    await callback.message.answer(with_footer(f"✏️ <b>PROMO KOD TAHRIRLASH:</b>\n\n🔑 <b>Kod:</b> <code>{code}</code>\n🎁 <b>Turi:</b> {r_str}\n👥 <b>Limit:</b> {used_c}/{max_u}\n⏳ <b>Tugash:</b> {(exp_at[:10] if exp_at else '—')}\n\n<b>Nimani o'zgartirishni tanlang:</b>"), parse_mode='HTML', reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith('pedit_name_'))
async def promo_edit_name_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    code = callback.data.replace('pedit_name_', '')
    await state.update_data(editing_promo_code=code)
    await state.set_state(AdminStates.waiting_for_promo_edit_name)
    await callback.message.answer(with_footer(f'🔑 <b><code>{code}</code> kodi uchun yangi nom/matn kiriting:</b>\n\n<i>(Kamida 3 ta belgi, masalan: NEWPROMO2026, SKIDKA50)</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_promo_edit_name, F.text, ~F.text.in_(MENU_BUTTONS))
async def promo_edit_name_exec(message: Message, state: FSMContext):
    new_code = message.text.strip().upper()
    data = await state.get_data()
    old_code = data.get('editing_promo_code', '')
    await state.clear()
    success, msg = await db_req.update_promo_code_text(old_code, new_code)
    await message.answer(with_footer(msg), parse_mode='HTML')

@router.callback_query(F.data.startswith('pedit_val_'))
async def promo_edit_value_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    code = callback.data.replace('pedit_val_', '')
    await state.update_data(editing_promo_code=code, editing_promo_field='value')
    await state.set_state(AdminStates.waiting_for_promo_edit_value)
    await callback.message.answer(with_footer(f'✏️ <b><code>{code}</code> uchun yangi qiymatni kiriting:</b>\n\n<i>(Kun soni, foiz (1-100%) yoki ball — faqat raqam yuboring)</i>'), parse_mode='HTML')
    await callback.answer()

@router.callback_query(F.data.startswith('pedit_lim_'))
async def promo_edit_limit_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    code = callback.data.replace('pedit_lim_', '')
    await state.update_data(editing_promo_code=code, editing_promo_field='limit')
    await state.set_state(AdminStates.waiting_for_promo_edit_value)
    await callback.message.answer(with_footer(f'🔢 <b><code>{code}</code> uchun yangi limit (max ishlatish soni) kiriting:</b>\n\n<i>(Faqat musbat butun raqam yuboring)</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_promo_edit_value, F.text, ~F.text.in_(MENU_BUTTONS))
async def promo_edit_value_exec(message: Message, state: FSMContext):
    val_str = message.text.strip()
    if not val_str.isdigit() or int(val_str) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, musbat butun raqam kiriting:'))
        return
    data = await state.get_data()
    code = data.get('editing_promo_code', '')
    field = data.get('editing_promo_field', 'value')
    new_val = int(val_str)
    if field == 'value':
        info = await db_req.get_promo_code_info(code)
        if info and info.get('reward_type') == 'discount':
            if new_val < 1 or new_val > 100:
                await message.answer(with_footer("⚠️ <b>Skidka foizi noto'g'ri!</b>\n\n📌 Skidka faqat <b>1% dan 100% gacha</b> bo'lishi mumkin.\nMasalan: <code>10</code>, <code>25</code>, <code>50</code>, <code>100</code>\n\nQaytadan kiriting:"), parse_mode='HTML')
                return
    await state.clear()
    if field == 'limit':
        await db_req.update_promo_code_max_uses(code, new_val)
        await message.answer(with_footer(f"✅ <b><code>{code}</code> kodi ishlatish limiti <b>{new_val}</b> ga o'zgartirildi!</b>"), parse_mode='HTML')
    else:
        await db_req.update_promo_code_value(code, new_val)
        await message.answer(with_footer(f"✅ <b><code>{code}</code> kodi qiymati <b>{new_val}</b> ga o'zgartirildi!</b>"), parse_mode='HTML')

@router.callback_query(F.data == 'promo_back')
async def promo_back_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == 'promo_create_start')
async def promo_create_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.message.edit_text(with_footer('🔑 <b>Yangi promo kod matnini kiriting:</b>\n\n<i>Masalan: PROMO2026, SKIDKA25, KINOVIP</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_promo_code, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_promo_code_text(message: Message, state: FSMContext):
    code_text = message.text.strip().upper()
    is_avail, reason = await db_req.check_promo_code_availability(code_text)
    if not is_avail:
        await message.answer(with_footer(reason), parse_mode='HTML')
        return
    await state.update_data(promo_code=code_text)
    await state.set_state(AdminStates.waiting_for_promo_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='👑 Premium Kunlar (days)', callback_data='promotype_days')], [InlineKeyboardButton(text='🏷️ Skidka Foizi (discount %)', callback_data='promotype_discount')], [InlineKeyboardButton(text='💎 Bonus Ballar (points)', callback_data='promotype_points')]])
    await message.answer(with_footer(f'🔑 Promo kod: <code>{code_text}</code>\n\n🎁 <b>Mukofot turini tanlang:</b>'), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('promotype_'))
async def process_promo_type_cb(callback: CallbackQuery, state: FSMContext):
    p_type = callback.data.split('_')[1]
    await state.update_data(promo_type=p_type)
    await state.set_state(AdminStates.waiting_for_promo_value)
    if p_type == 'days':
        label = '⏳ <b>Necha kunlik Premium bermoqchisiz?</b>\n\n📌 <i>Faqat <b>kun sonini</b> yuboring. Masalan:\n• <code>30</code> → 1 oylik Premium\n• <code>60</code> → 2 oylik Premium\n• <code>90</code> → 3 oylik Premium\n• <code>365</code> → 1 yillik Premium</i>'
    elif p_type == 'discount':
        label = "🏷️ <b>Necha foiz (%) skidka berasiz?</b>\n\n📌 <i>Faqat <b>foiz sonini</b> yuboring (1-100).\nMasalan: <code>50</code> → 50% skidka\n<code>100</code> → To'liq bepul (1 oy premium beriladi)</i>"
    else:
        label = '💎 <b>Necha ball bermoqchisiz?</b>\n\n📌 <i>Faqat <b>ball sonini</b> yuboring.\nMasalan: <code>50</code>, <code>100</code>, <code>150</code></i>'
    await callback.message.edit_text(with_footer(label), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_promo_value, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_promo_value_text(message: Message, state: FSMContext):
    val = message.text.strip()
    if not val.isdigit() or int(val) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, musbat butun raqam kiriting:'))
        return
    int_val = int(val)
    data = await state.get_data()
    p_type = data.get('promo_type', '')
    if p_type == 'discount':
        if int_val < 1 or int_val > 100:
            await message.answer(with_footer("⚠️ <b>Skidka foizi noto'g'ri!</b>\n\n📌 Skidka faqat <b>1% dan 100% gacha</b> bo'lishi mumkin.\nMasalan: <code>10</code>, <code>25</code>, <code>50</code>\n\nQaytadan kiriting:"), parse_mode='HTML')
            return
    if p_type == 'days' and int_val > 3650:
        await message.answer(with_footer('⚠️ <b>Kun soni juda katta!</b>\n\n📌 Maksimal: <code>3650</code> kun (10 yil).\n\nQaytadan kiriting:'), parse_mode='HTML')
        return
    await state.update_data(promo_val=int_val)
    await state.set_state(AdminStates.waiting_for_promo_uses)
    if p_type == 'days':
        if int_val == 1:
            friendly = '1 kunlik Premium'
        elif int_val <= 7:
            friendly = f'{int_val} kunlik Premium (≈ {int_val} kun)'
        elif int_val <= 14:
            friendly = f'{int_val} kunlik Premium (≈ {int_val // 7} haftalik)'
        elif int_val <= 31:
            months = round(int_val / 30, 1)
            friendly = f'{int_val} kunlik Premium (≈ {months} oylik)'
        else:
            months = round(int_val / 30, 1)
            friendly = f'{int_val} kunlik Premium (≈ {months} oylik)'
    elif p_type == 'discount':
        friendly = f'{int_val}% skidka'
    else:
        friendly = f'+{int_val} ball'
    await message.answer(with_footer(f"✅ <b>Mukofot tanlandi:</b> {friendly}\n\n👥 <b>Jami nechta foydalanuvchi ushbu promo kodni ishlata olsin?</b>\n\n📌 <i>Eslatma: Har bir foydalanuvchi ushbu promo koddan faqat 1 marta foydalana oladi.\nMasalan: <b>100</b> kiritsangiz — birinchi tergan 100 ta har xil odam 1 martadan ishlatishi mumkin bo'ladi.</i>"), parse_mode='HTML')

@router.message(AdminStates.waiting_for_promo_uses, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_promo_uses_text(message: Message, state: FSMContext):
    uses = message.text.strip()
    if not uses.isdigit() or int(uses) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, musbat butun raqam kiriting:'))
        return
    data = await state.get_data()
    code = data['promo_code']
    p_type = data['promo_type']
    p_val = data['promo_val']
    max_u = int(uses)
    await state.clear()
    success = await db_req.create_promo_code(code, p_type, p_val, max_uses=max_u, expires_in_days=30, created_by=message.from_user.id)
    if success:
        r_str = f'{p_val} kunlik Premium' if p_type == 'days' else f'{p_val}% skidka' if p_type == 'discount' else f'{p_val} ball'
        await message.answer(with_footer(f'✅ <b>PROMO KOD MUVAFFAQIYATLI YARATILDI!</b>\n\n🔑 <b>Kod:</b> <code>{code}</code>\n🎁 <b>Mukofot:</b> {r_str}\n👥 <b>Max ishlatish:</b> {max_u} marta'), parse_mode='HTML')
    else:
        await message.answer(with_footer("❌ Xatolik yuz berdi. Ushbu kod allaqachon mavjud bo'lishi mumkin."))

@router.message(F.text == '2X Referal ⚡')
async def show_2x_referral_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS and (not await db_req.has_permission(message.from_user.id, 'send_broadcast')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    status = await db_req.get_setting('referral_2x_event')
    is_on = status == '1'
    base_pts = await db_req.get_config_int('points_referral', 5)
    double_pts = base_pts * 2
    status_txt = f'FAOL ✅ (+{double_pts} 💎 ball)' if is_on else f"O'CHIRILGAN ❌ (Standart +{base_pts} 💎 ball)"
    txt = f"⚡ <b>2X REFERAL BALLARI EVENTI:</b>\n\n📊 <b>Hozirgi holat:</b> {status_txt}\n💎 <b>Sozlamadagi ball:</b> +{base_pts} 💎 → Eventda 2X: <b>+{double_pts} 💎 ball</b>\n\n<i>Eslatma: Event yoqilganda do'stini taklif qilib, u majburiy kanallarga obuna bo'lib tekshirgach 2X baravar (+{double_pts} 💎) ball beriladi!</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⚡ Eventni Yoqish (2X)', callback_data='toggle_2x_event_on'), InlineKeyboardButton(text="🔕 Eventni O'chirish", callback_data='toggle_2x_event_off')], [InlineKeyboardButton(text='📢 Shoshilinch 2X Xabar Yuborish', callback_data='broadcast_2x_event_msg')]])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'toggle_2x_event_on')
async def toggle_2x_event_on_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    base_pts = await db_req.get_config_int('points_referral', 5)
    double_pts = base_pts * 2
    await db_req.set_setting('referral_2x_event', '1')
    await callback.answer(f'⚡ 2X Referal Event yoqildi! (+{double_pts} 💎)', show_alert=True)
    await callback.message.edit_text(with_footer(f'⚡ <b>2X Referal Event muvaffaqiyatli yoqildi! (Har bir referal uchun +{double_pts} 💎 ball beriladi)</b>\n\nFoydalanuvchilarga bildirishnoma yuborishingiz mumkin.'), parse_mode='HTML')

@router.callback_query(F.data == 'toggle_2x_event_off')
async def toggle_2x_event_off_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    base_pts = await db_req.get_config_int('points_referral', 5)
    await db_req.set_setting('referral_2x_event', '0')
    await callback.answer("🔕 2X Referal Event o'chirildi!", show_alert=True)
    await callback.message.edit_text(with_footer(f"🔕 <b>2X Referal Event o'chirildi. Standart +{base_pts} 💎 ball rejimiga qaytildi.</b>"), parse_mode='HTML')

@router.callback_query(F.data == 'broadcast_2x_event_msg')
async def broadcast_2x_event_msg_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await callback.answer('📢 Shoshilinch 2X Xabar yuborish boshlandi...', show_alert=True)
    base_pts = await db_req.get_config_int('points_referral', 5)
    double_pts = base_pts * 2
    users = await db_req.get_all_users()
    alert_msg = f"🚨 <b>SHOSHILINCH SUPER EVENT! 2X REFERAL BALLARI!</b> ⚡\n\nHurmatli foydalanuvchilar! Hozirdan boshlab taklif qilingan har bir do'stingiz uchun <b>2X BARAVAR KO'PROQ BALL (+{double_pts} 💎)</b> beriladi! 🚀\n<i>(Standart +{base_pts} 💎 ball o'rniga aynan bugun 2X: +{double_pts} 💎 ball!)</i>\n\n📌 <i>Eslatma: Ballar faqat do'stingiz taklif havolangiz orqali kirib, majburiy kanallarga to'liq obuna bo'lib va tasdiqlangach beriladi! Imkoniyatni boy bermang!</i> 🍿"
    sent_cnt = 0
    for uid in users:
        try:
            await callback.bot.send_message(with_footer(uid), alert_msg, parse_mode='HTML')
            sent_cnt += 1
            import asyncio
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await callback.message.edit_text(with_footer(f'✅ <b>Shoshilinch 2X Xabar {sent_cnt} ta foydalanuvchiga muvaffaqiyatli yetkazildi!</b>'), parse_mode='HTML')

@router.message(F.text == 'Audit Log 🛡️')
async def show_audit_logs_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    logs = await db_req.get_audit_logs(limit=20)
    txt = '🛡️ <b>ADMIN VA TIZIM HARAKATLARI JURNALI (AUDIT LOG):</b>\n\n'
    if logs:
        for log_id, u_id, log_type, details, created_at, username, full_name in logs:
            uname = f'@{username}' if username else full_name or str(u_id)
            txt += f'• <b>{created_at}</b> | 👤 {uname}\n  🔹 <i>{log_type}</i>: {details}\n'
    else:
        txt += "<i>Hali jurnalda yozuvlar yo'q.</i>"
    await message.answer(with_footer(txt), parse_mode='HTML')

@router.message(F.text == 'Faollik Tahlili 📊')
async def show_activity_stats_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS and (not await db_req.has_permission(message.from_user.id, 'view_stats')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    stats = await db_req.get_user_activity_stats()
    txt = f"📊 <b>FOYDALANUVCHILAR FAOLLIGI VA RETENTION TAHLILI:</b>\n\n👥 <b>Jami Foydalanuvchilar:</b> <code>{stats['total']:,} ta</code>\n\n🟢 <b>Bugun Faol Bo'lganlar:</b> <code>{stats['today']:,} ta</code>\n⚡ <b>Oxirgi 7 Kunda Faol:</b> <code>{stats['active_7d']:,} ta</code>\n📅 <b>Oxirgi 30 Kunda Faol:</b> <code>{stats['active_30d']:,} ta</code>\n😴 <b>Nofaol (90+ kun kirmagan):</b> <code>{stats['inactive_90d']:,} ta</code>\n\n📈 <b>Foydalanuvchilar Qaytish Darajasi (Retention Rate):</b> <b>{stats['retention_rate']}%</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='refresh_activity_stats')]])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'refresh_activity_stats')
async def refresh_activity_stats_cb(callback: CallbackQuery):
    stats = await db_req.get_user_activity_stats()
    txt = f"📊 <b>FOYDALANUVCHILAR FAOLLIGI VA RETENTION TAHLILI:</b>\n\n👥 <b>Jami Foydalanuvchilar:</b> <code>{stats['total']:,} ta</code>\n\n🟢 <b>Bugun Faol Bo'lganlar:</b> <code>{stats['today']:,} ta</code>\n⚡ <b>Oxirgi 7 Kunda Faol:</b> <code>{stats['active_7d']:,} ta</code>\n📅 <b>Oxirgi 30 Kunda Faol:</b> <code>{stats['active_30d']:,} ta</code>\n😴 <b>Nofaol (90+ kun kirmagan):</b> <code>{stats['inactive_90d']:,} ta</code>\n\n📈 <b>Foydalanuvchilar Qaytish Darajasi (Retention Rate):</b> <b>{stats['retention_rate']}%</b>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Yangilash', callback_data='refresh_activity_stats')]])
    try:
        await callback.message.edit_text(with_footer(txt), parse_mode='HTML', reply_markup=kb)
    except Exception:
        pass
    await callback.answer('Statistika yangilandi 🔄')

@router.message(F.text == 'Yuborilgan reklamalar 📢')
async def show_broadcasts_history_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS and (not await db_req.has_permission(message.from_user.id, 'send_broadcast')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    batches = await db_req.get_recent_broadcast_batches(limit=10)
    txt = '📢 <b>YUBORILGAN REKLAMALAR TARIXI:</b>\n\n'
    keyboard_buttons = []
    if batches:
        for b_id, cnt, created_at in batches:
            txt += f'• <b>ID:</b> <code>{b_id}</code> | <b>{cnt} ta userga</b> | <i>{created_at}</i>\n'
            keyboard_buttons.append([InlineKeyboardButton(text=f"🗑️ O'chirish: {b_id} ({cnt} ta)", callback_data=f'del_bc_{b_id}')])
    else:
        txt += '<i>Hali yuborilgan va saqlangan reklamalar tarixi mavjud emas.</i>'
    kb = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('del_bc_'))
async def delete_broadcast_batch_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan!', show_alert=True)
        return
    b_id = callback.data.split('_')[2]
    await callback.answer("🗑️ Reklama o'chirilmoqda...", show_alert=True)
    success, failed = await db_req.delete_broadcast_batch(callback.bot, b_id)
    await callback.message.edit_text(with_footer(f"✅ <b>REKLAMA OMMAVIY O'CHIRILDI!</b>\n\n🗑️ <b>O'chirildi:</b> {success} ta chatdan\n❌ <b>O'chirilmadi:</b> {failed} ta chatdan"), parse_mode='HTML')

@router.message(F.text == 'Bot Rejimi 🛠️')
async def show_maintenance_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan.'))
        return
    m_mode = await db_req.get_setting('bot_maintenance_mode')
    is_on = m_mode == '1'
    status_txt = 'YANGILANMOQDA (FAOL) 🛠️' if is_on else "ODDIY REJIM (O'CHIRILGAN) ✅"
    txt = f"🛠️ <b>BOT YANGILANISH REJIMI BOSHQARUVI:</b>\n\n📊 <b>Hozirgi holat:</b> {status_txt}\n\n<i>Eslatma: Ushbu rejim yoqilganda oddiy foydalanuvchilarga chiroyli tarzda 'Bot yangilanmoqda, yanada ko'p yangi va zo'r funksiyalar qo'shilmoqda!' xabari chiqadi.</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🛠️ Yangilanish Rejimini Yoqish', callback_data='toggle_maint_on'), InlineKeyboardButton(text='✅ Oddiy Rejimga Qaytish', callback_data='toggle_maint_off')]])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'toggle_maint_on')
async def toggle_maint_on_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await db_req.set_setting('bot_maintenance_mode', '1')
    await callback.answer('🛠️ Bot Yangilanmoqda rejimi yoqildi!', show_alert=True)
    await callback.message.edit_text(with_footer("🛠️ <b>Bot 'Yangilanmoqda' rejimiga o'tkazildi!</b> Oddiy userlar uchun xabarlar vaqtinchalik to'xtatildi."), parse_mode='HTML')

@router.callback_query(F.data == 'toggle_maint_off')
async def toggle_maint_off_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await db_req.set_setting('bot_maintenance_mode', '0')
    await callback.answer('✅ Bot oddiy rejimga qaytarildi!', show_alert=True)
    await callback.message.edit_text(with_footer("✅ <b>Bot oddiy ishchi rejimga qaytarildi. Barcha foydalanuvchilar botdan to'liq foydalanishi mumkin!</b>"), parse_mode='HTML')

@router.message(F.text == 'Nofaollarga Eslatma 💤')
async def show_inactive_reminder_panel(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS and (not await db_req.has_permission(message.from_user.id, 'send_broadcast')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    inactives = await db_req.get_inactive_users(days=15)
    cnt = len(inactives) if inactives else 0
    txt = f"💤 <b>NOFAOL FOYDALANUVCHILARGA ESLATMA (FEATURE #14):</b>\n\nOxirgi 15 kun ichida botga kirmagan <b>{cnt} ta</b> foydalanuvchi aniqlandi.\n\n<i>Ularga 'Sizni sog'indik + 🎁 +5 💎 bonus ball' eslatma xabarini yuborishni tasdiqlaysizmi?</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'📢 {cnt} ta Nofaolga Xabar + 5 Ball Berish', callback_data='send_inactive_reminder_exec')]])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'send_inactive_reminder_exec')
async def send_inactive_reminder_exec_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await callback.answer('📢 Nofaollarga eslatma yuborilmoqda...', show_alert=True)
    inactives = await db_req.get_inactive_users(days=15)
    msg = f"🍿 <b>SIZNI SOG'INDIK!</b> ✨\n\nHurmatli foydalanuvchi, botimizga juda ko'p yangi eng sara va premyera kinolar qo'shildi! 🎬\n\n🎁 <b>Sizga qaytganingiz uchun +5 💎 bonus ball taqdim etildi!</b>\n\n👇 <i>Kiring va eng so'nggi kinolarni maza qilib tomosha qiling:</i>"
    sent_cnt = 0
    if inactives:
        for uid in inactives:
            try:
                await db_req.add_points(uid, 5)
                await callback.bot.send_message(with_footer(uid), msg, parse_mode='HTML')
                sent_cnt += 1
                import asyncio
                await asyncio.sleep(0.04)
            except Exception:
                pass
    await callback.message.edit_text(with_footer(f'✅ <b>Eslatma va +5 ballik bonus {sent_cnt} ta nofaol foydalanuvchiga muvaffaqiyatli yetkazildi!</b>'), parse_mode='HTML')

@router.message(Command('setwatermark'))
@router.message(Command('watermark'))
async def admin_set_watermark_cmd(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer('❌ Bu amal faqat Bosh Admin uchun!'))
        return
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        wm_text = args[1].strip()
        await db_req.set_setting('custom_watermark_text', wm_text)
        await message.answer(with_footer(f"✅ <b>Watermark matni muvaffaqiyatli o'rnatildi:</b>\n\n{wm_text}"), parse_mode='HTML')
    else:
        current_wm = await db_req.get_setting('custom_watermark_text')
        disp = current_wm if current_wm else f'🎬 <b>@{config.BOT_USERNAME} — Eng sara kinolar bazasi 🍿</b>'
        await message.answer(with_footer(f"🏷️ <b>KINO WATERMARK / CAPTION SOZLAMASI (FEATURE #10):</b>\n\n📌 <b>Hozirgi watermark matni:</b>\n{disp}\n\n💡 <i>Yangi watermark o'rnatish uchun buyruqdan foydalaning:</i>\n<code>/setwatermark 🎬 @uzkinobaza_bot — Rasmiy kino kanali 🍿</code>"), parse_mode='HTML')

@router.message(Command('gift'))
async def admin_gift_points_cmd(message: Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer(with_footer("⚠️ <b>Buyruq formati noto'g'ri!</b>\n\n📌 <b>Foydalanish:</b> <code>/gift [ball_miqdori] [user_id]</code>\n<i>Masalan: <code>/gift 50 123456789</code></i>"), parse_mode='HTML')
        return
    arg1, arg2 = (args[1], args[2])
    if not arg1.isdigit() or not arg2.isdigit():
        await message.answer(with_footer('⚠️ Iltimos, ball va User ID sini faqat butun raqamda kiriting!'))
        return
    num1, num2 = (int(arg1), int(arg2))
    if num1 > 100000 and num2 <= 10000:
        target_uid, amount = (num1, num2)
    else:
        amount, target_uid = (num1, num2)
    target_user = await db_req.get_user(target_uid)
    if not target_user:
        await message.answer(with_footer(f"❌ User ID <code>{target_uid}</code> bo'yicha foydalanuvchi topilmadi!"), parse_mode='HTML')
        return
    added_pts, _ = await db_req.add_points(target_uid, amount, bypass_daily_limit=True)
    await db_req.check_notify_150pts_reward(message.bot, target_uid)
    await db_req.add_abuse_log(message.from_user.id, 'GIFT_POINTS', f"Admin {message.from_user.id} user {target_uid} ga +{amount} ball sovg'a qildi.")
    try:
        notify_msg = f"🎁 <b>ADMINDAN SOVG'A BALL!</b> 🎉\n\nAdmin tomonidan hisobingizga <b>+{amount} 💎 ball</b> taqdim etildi!\n\n<i>Balingizni oshirishda va botimizdan foydalanishda davom eting!</i> 🍿"
        await message.bot.send_message(with_footer(target_uid), notify_msg, parse_mode='HTML')
    except Exception:
        pass
    await message.answer(with_footer(f"✅ <b>BALL MUVAFFAQIYATLI SOVG'A QILINDI!</b>\n\n👤 <b>Foydalanuvchi ID:</b> <code>{target_uid}</code>\n💎 <b>Berilgan ball:</b> <code>+{amount} 💎</code>"), parse_mode='HTML')

@router.message(F.text.regexp('(?i).*(premium obunachilar).*'))
async def show_premium_subscribers_panel(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id not in config.ADMINS and (not await db_req.has_permission(user_id, 'view_stats')):
        await message.answer(with_footer("❌ Sizda ushbu bo'limga kirish huquqi yo'q!"))
        return
    subscribers = await db_req.get_active_premium_subscribers_list(50)
    if not subscribers:
        await message.answer(with_footer('💎 <b>Hozircha faol Premium foydalanuvchilar mavjud emas.</b>'), parse_mode='HTML')
        return
    await message.answer(with_footer(f"💎 <b>FAOL PREMIUM FOYDALANUVCHILAR RO'YXATI (Jami {len(subscribers)} ta):</b>"), parse_mode='HTML')
    for sub_uid, username, full_name, start_date, end_date, plan in subscribers:
        uname = f'@{username}' if username else 'Mavjud emas'
        fname = full_name or 'Foydalanuvchi'
        card = f'👑 <b>PREMIUM FOYDALANUVCHI:</b>\n\n👤 <b>Ism:</b> {fname}\n🏷 <b>Username:</b> {uname}\n🆔 <b>User ID:</b> <code>{sub_uid}</code>\n📋 <b>Reja / Narx:</b> <code>{plan or 'Premium VIP'}</code>\n📅 <b>Olingan sana:</b> <code>{start_date}</code>\n⏳ <b>Tugash sana:</b> <code>{end_date}</code>'
        kb = inline.get_premium_user_action_keyboard(sub_uid)
        await message.answer(with_footer(card), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('prem_warn_'))
async def prem_warn_user_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer('❌ Faqat Bosh Admin ogohlantirish bera oladi!', show_alert=True)
        return
    target_uid = int(callback.data.split('_')[2])
    async with db_req.get_db() as db:
        async with db.execute('SELECT warning_count, ban_stage FROM users WHERE id = ?', (target_uid,)) as cursor:
            row = await cursor.fetchone()
            curr_warn = (row[0] if row and row[0] is not None else 0) + 1
            curr_stage = row[1] if row and row[1] is not None else 0
        await db.execute('UPDATE users SET warning_count = ? WHERE id = ?', (curr_warn, target_uid))
        await db.commit()
    if curr_warn >= 3:
        dur_hours, dur_text = db_req.get_progressive_ban_duration(curr_stage)
        await db_req.temp_ban_user(target_uid, hours=dur_hours)
        try:
            ban_msg = f"🚨 <b>HISOB VAQTINCHA BLOKLANDI (3/3)</b>\n\nHurmatli foydalanuvchi! Qoidabuzarliklar va rasmiy ogohlantirishlar soni cheklangan limitga (3 marta) yetganligi sababli, hisobingiz xavfsizlik qoidalariga muvofiq <b>{dur_text}</b> muddatga bloklandi.\n\n⚖️ <i>Iltimos, belgilangan cheklov muddati tugagach, bot qoidalariga to'liq rioya qilgan holda foydalanishingizni so'raymiz.</i>"
            await callback.bot.send_message(with_footer(target_uid), ban_msg, parse_mode='HTML')
        except Exception:
            pass
        await callback.answer(f"🚨 Foydalanuvchida 3 ta ogohlantirish bo'ldi va {dur_text} ga bloklandi!", show_alert=True)
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n🚨 <b>HOLAT:</b> 3/3 Ogohlantirish sababli {dur_text} ga bloklandi!'), parse_mode='HTML')
    else:
        try:
            warn_msg = f"⚠️ <b>RASMIY OGOHLANTIRISH! ({curr_warn}/3)</b>\n\nHurmatli foydalanuvchi! Botimizdan foydalanish qoidalari va odob-axloq me'yorlariga rioya etilmaganligi sababli sizga admin tomonidan rasmiy ogohlantirish berildi.\n\n📌 <b>Eslatma:</b> Qoidabuzarliklar soni <b>3 taga</b> yetganda, hisobingiz avtomatik ravishda botdan bloklanadi!\n\n⚖️ <i>Iltimos, botimiz qoidalariga hamda qonunchilik me'yorlariga qat'iy rioya qilishingizni so'raymiz.</i>"
            await callback.bot.send_message(with_footer(target_uid), warn_msg, parse_mode='HTML')
        except Exception:
            pass
        await callback.answer(f'⚠️ Foydalanuvchiga {curr_warn}-ogohlantirish yuborildi!', show_alert=True)
        await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n⚠️ <b>OGOHLANTIRISH BERILDI:</b> ({curr_warn}/3)'), parse_mode='HTML')

@router.callback_query(F.data.startswith('prem_ban_'))
async def prem_ban_user_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    target_uid = int(callback.data.split('_')[2])
    kb = inline.get_ban_duration_keyboard(target_uid)
    await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n🛑 <b>Bloklash muddatini tanlang:</b>'), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('prem_remove_'))
async def prem_remove_user_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Faqat Bosh Admin Premium obunasini o'chira oladi!", show_alert=True)
        return
    target_uid = int(callback.data.split('_')[2])
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Ha, Premiumni O'chirish", callback_data=f'prem_del_confirm_{target_uid}')
    builder.button(text='🔙 Bekor qilish', callback_data=f'prem_del_cancel_{target_uid}')
    builder.adjust(1)
    await callback.message.edit_text(with_footer(f'{callback.message.text}\n\n❓ <b>Ushbu foydalanuvchining Premium VIP obunasini bekor qilishga ishonchingiz komilmi?</b>'), parse_mode='HTML', reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith('prem_del_confirm_'))
async def prem_del_confirm_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    target_uid = int(callback.data.split('_')[3])
    await db_req.revoke_premium_subscription(target_uid)
    try:
        user_notify = f"❌ <b>PREMIUM VIP OBUNASI BEKOR QILINDI</b>\n\nHurmatli foydalanuvchi! Botimiz xavfsizligi va foydalanish shartlariga hamda rasmiy qoidalarga rioya etilmaganligi sababli, <b>👑 Premium VIP</b> obunangiz admin tomonidan muddatidan oldin bekor qilindi.\n\n📌 <b>Hisob holati:</b> Oddiy foydalanuvchi rejimiga o'tkazildi.\n\n⚖️ <i>Iltimos, botimiz qoidalariga hamda belgilangan me'yorlarga to'liq rioya etishingizni so'raymiz.</i>"
        await callback.bot.send_message(with_footer(target_uid), user_notify, parse_mode='HTML')
    except Exception:
        pass
    await callback.answer("❌ Premium VIP obunasi muvaffaqiyatli o'chirildi!", show_alert=True)
    await callback.message.edit_text(with_footer(f"✅ <b>ID <code>{target_uid}</code> bo'lgan foydalanuvchining Premium obunasi muvaffaqiyatli bekor qilindi!</b>"), parse_mode='HTML')

@router.callback_query(F.data.startswith('prem_del_cancel_'))
async def prem_del_cancel_cb(callback: CallbackQuery):
    target_uid = int(callback.data.split('_')[3])
    kb = inline.get_premium_user_action_keyboard(target_uid)
    await callback.answer('Amal bekor qilindi', show_alert=False)
    await callback.message.edit_text(with_footer(callback.message.text.split('\n\n❓')[0]), parse_mode='HTML', reply_markup=kb)

@router.message(F.text.regexp('(?i).*(moderatorlarni boshqarish).*'))
async def show_moderators_permission_list(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer("❌ Ushbu bo'lim faqat Bosh Admin uchun!"))
        return
    moderators = await db_req.get_moderators()
    if not moderators:
        await message.answer(with_footer("👥 <b>Hozircha moderatorlar tayinlanmagan.</b>\n\n<i>Yangi moderator qo'shish uchun 'Moderatorlar 👥' tugmasidan foydalaning.</i>"), parse_mode='HTML')
        return
    await message.answer(with_footer('⚙️ <b>MODERATORLAR VA ULARNING HUQUQLARINI BOSHQARISH:</b>\n<i>Quyidagi moderatorlardan birini tanlang:</i>'), parse_mode='HTML')
    for mod_uid, username, full_name in moderators:
        uname = f'@{username}' if username else 'Mavjud emas'
        fname = full_name or 'Moderator'
        perms = await db_req.get_moderator_permissions(mod_uid)
        kb = inline.get_moderator_perm_matrix_keyboard(mod_uid, perms)
        txt = f'👤 <b>Moderator:</b> {fname}\n🏷 <b>Username:</b> {uname}\n🆔 <b>ID:</b> <code>{mod_uid}</code>'
        await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data.startswith('mod_perm_toggle_'))
async def mod_perm_toggle_cb(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Faqat Bosh Admin moderator huquqlarini o'zgartira oladi!", show_alert=True)
        return
    parts = callback.data.split('_')
    mod_uid = int(parts[3])
    perm_name = '_'.join(parts[4:])
    success = await db_req.toggle_moderator_permission(mod_uid, perm_name)
    if success:
        perms = await db_req.get_moderator_permissions(mod_uid)
        new_kb = inline.get_moderator_perm_matrix_keyboard(mod_uid, perms)
        status_str = 'yoqildi ✅' if perms.get(perm_name, False) else "o'chirildi ❌"
        await callback.answer(f'Ruxsatnoma {status_str}', show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=new_kb)
    else:
        await callback.answer('❌ Xatolik yuz berdi!', show_alert=True)

@router.callback_query(F.data == 'mod_perms_list_back')
async def mod_perms_list_back_cb(callback: CallbackQuery):
    await callback.answer()
    await callback.message.delete()

@router.message(F.text == '➕ Mannual Premium Qo\'shish')
async def manual_premium_start(message: Message, state: FSMContext):
    """Mannual Premium qo'shish bosganda ketma-ket so'raladigan bosqichlarni ishga tushirish"""
    await state.clear()
    user_id = message.from_user.id
    if user_id not in config.ADMINS and (not await db_req.has_permission(user_id, 'manage_sponsors')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    await state.set_state(AdminStates.waiting_for_manual_prem_amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await message.answer(
        with_footer(
            "👑 <b>MANNUAL PREMIUM QO'SHISH REJIMI</b>\n\n"
            "<b>1-QADAM:</b> 💰 <i>Necha pul? (Plan summasi UZS so'mda)</i>\n\n"
            "Masalan: <code>180000</code> yoki <code>20000</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

@router.callback_query(F.data == 'mp_cancel')
async def mp_cancel_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(with_footer('❌ <b>Mannual Premium qo\'shish bekor qilindi.</b>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_manual_prem_amount, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_amount(message: Message, state: FSMContext):
    txt_input = message.text.strip().replace(' ', '').replace(',', '')
    if not txt_input.isdigit() or int(txt_input) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 180000):'))
        return
    amount = int(txt_input)
    await state.update_data(mp_amount=amount)
    await state.set_state(AdminStates.waiting_for_manual_prem_username_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await message.answer(
        with_footer(
            f"✅ <b>1-QADAM TUGALLANDI!</b>\n\n"
            f"💰 <b>Plan summasi:</b> <code>{amount:,} UZS</code>\n\n"
            f"<b>2-QADAM:</b> 👤 <i>@username va ID raqamini kiriting.</i>\n\n"
            f"Format: <code>@username ID</code>\n"
            f"Masalan: <code>@MadridPrimee_reklama 8352596257</code>\n"
            f"Yoki faqat ID: <code>8352596257</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

@router.message(AdminStates.waiting_for_manual_prem_username_id, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_username_id(message: Message, state: FSMContext):
    txt_input = message.text.strip()
    username = None
    user_id = None

    import re
    id_match = re.search(r'(\d{5,})', txt_input)
    username_match = re.search(r'@([a-zA-Z0-9_]{3,})', txt_input)

    if id_match:
        user_id = int(id_match.group(1))
    if username_match:
        username = '@' + username_match.group(1)

    if not user_id:
        await message.answer(
            with_footer(
                '⚠️ <b>Foydalanuvchi ID raqamini aniqlab bo\'lmadi!</b>\n\n'
                'Iltimos, to\'g\'ri formatda yuboring:\n'
                'Masalan: <code>@MadridPrimee_reklama 8352596257</code>\n'
                'Yoki: <code>8352596257</code>'
            ),
            parse_mode='HTML'
        )
        return

    await state.update_data(mp_user_id=user_id, mp_username=username)
    await state.set_state(AdminStates.waiting_for_manual_prem_payment_amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    disp_name = f"{username or ''} (ID: <code>{user_id}</code>)"
    await message.answer(
        with_footer(
            f"✅ <b>2-QADAM TUGALLANDI!</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {disp_name}\n\n"
            f"<b>3-QADAM:</b> 💵 <i>Foydalanuvchi qancha to'lov qildi? (UZS so'mda)</i>\n\n"
            f"Agar plan summasi bilan to'langan bo'lsa, xuddi shu sonni yozing.\n"
            f"Masalan: <code>180000</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

@router.message(AdminStates.waiting_for_manual_prem_payment_amount, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_payment_amount(message: Message, state: FSMContext):
    txt_input = message.text.strip().replace(' ', '').replace(',', '')
    if not txt_input.isdigit() or int(txt_input) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 180000):'))
        return
    payment_amount = int(txt_input)
    await state.update_data(mp_payment_amount=payment_amount)
    await state.set_state(AdminStates.waiting_for_manual_prem_premium_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='1 haftalik Premium', callback_data='mp_ptype_1w')],
        [InlineKeyboardButton(text='1 oylik Premium', callback_data='mp_ptype_1m')],
        [InlineKeyboardButton(text='3 oylik Premium', callback_data='mp_ptype_3m')],
        [InlineKeyboardButton(text='6 oylik Premium', callback_data='mp_ptype_6m')],
        [InlineKeyboardButton(text='1 yillik Premium', callback_data='mp_ptype_1y')],
        [InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]
    ])
    await message.answer(
        with_footer(
            f"✅ <b>3-QADAM TUGALLANDI!</b>\n\n"
            f"💵 <b>To'langan summa:</b> <code>{payment_amount:,} UZS</code>\n\n"
            f"<b>4-QADAM:</b> 📋 <i>Qaysi premiumni sotib oldi?</i>\n\n"
            f"Quyidagi tugmalardan birini tanlang <b>yoki</b> o'zingiz xohlagan nomini yozing:\n"
            f"Masalan: <code>1 yillik Premium</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

@router.callback_query(F.data.startswith('mp_ptype_'))
async def mp_ptype_callback(callback: CallbackQuery, state: FSMContext):
    ptype_map = {
        '1w': '1 haftalik Premium',
        '1m': '1 oylik Premium',
        '3m': '3 oylik Premium',
        '6m': '6 oylik Premium',
        '1y': '1 yillik Premium'
    }
    ptype_key = callback.data.split('_')[2]
    premium_type = ptype_map.get(ptype_key, 'Premium')
    await state.update_data(mp_premium_type=premium_type)
    await state.set_state(AdminStates.waiting_for_manual_prem_period_until)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await callback.message.edit_text(
        with_footer(
            f"✅ <b>4-QADAM TUGALLANDI!</b>\n\n"
            f"📋 <b>Premium turi:</b> <b>{premium_type}</b>\n\n"
            f"<b>5-QADAM:</b> 📅 <i>Qachongacha muddati?</i>\n\n"
            f"Format: <code>YYYY-MM-DD</code> yoki <code>YYYY-MM-DD HH:MM:SS</code>\n"
            f"Masalan: <code>2027-08-07</code> yoki <code>2027-08-07 10:41:00</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_manual_prem_premium_type, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_premium_type(message: Message, state: FSMContext):
    premium_type = message.text.strip()
    if not premium_type:
        await message.answer(with_footer('⚠️ Iltimos, premium turini yozing:'))
        return
    await state.update_data(mp_premium_type=premium_type)
    await state.set_state(AdminStates.waiting_for_manual_prem_period_until)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await message.answer(
        with_footer(
            f"✅ <b>4-QADAM TUGALLANDI!</b>\n\n"
            f"📋 <b>Premium turi:</b> <b>{premium_type}</b>\n\n"
            f"<b>5-QADAM:</b> 📅 <i>Qachongacha muddati?</i>\n\n"
            f"Format: <code>YYYY-MM-DD</code> yoki <code>YYYY-MM-DD HH:MM:SS</code>\n"
            f"Masalan: <code>2027-08-07</code> yoki <code>2027-08-07 10:41:00</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

def _normalize_datetime_str(raw: str) -> str | None:
    """Sana vaqt formatini normalizatsiya qilish: YYYY-MM-DD -> YYYY-MM-DD 00:00:00, va YYYY-MM-DD HH:MM -> YYYY-MM-DD HH:MM:00"""
    import re
    s = raw.strip()
    m1 = re.match(r'^(\d{4}-\d{2}-\d{2})$', s)
    if m1:
        return f"{m1.group(1)} 00:00:00"
    m2 = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})$', s)
    if m2:
        return f"{m2.group(1)}:00"
    m3 = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}:\d{2})$', s)
    if m3:
        return m3.group(1)
    return None

@router.message(AdminStates.waiting_for_manual_prem_period_until, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_period_until(message: Message, state: FSMContext):
    normalized = _normalize_datetime_str(message.text)
    if not normalized:
        await message.answer(
            with_footer(
                '⚠️ <b>Sana formatida xatolik!</b>\n\n'
                'Iltimos, quyidagi formatlardan birini ishlating:\n'
                '• <code>2027-08-07</code> (faqat sana)\n'
                '• <code>2027-08-07 10:41</code> (sana + vaqt)\n'
                '• <code>2027-08-07 10:41:00</code> (to\'liq)'
            ),
            parse_mode='HTML'
        )
        return
    await state.update_data(mp_period_until=normalized)
    await state.set_state(AdminStates.waiting_for_manual_prem_expiration_date)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🔄 Oldingi bilan bir xil', callback_data='mp_exp_same'), InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await message.answer(
        with_footer(
            f"✅ <b>5-QADAM TUGALLANDI!</b>\n\n"
            f"📅 <i>Qachongacha muddati:</i> <code>{normalized}</code>\n\n"
            f"<b>6-QADAM:</b> ⏰ <i>Qachon tugaydi?</i>\n\n"
            f"Agar oldingi bilan bir xil bo'lsa, <b>🔄 Oldingi bilan bir xil</b> tugmasini bosing.\n"
            f"Yangi yozishingiz mumkin: Format <code>YYYY-MM-DD HH:MM:SS</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

@router.callback_query(F.data == 'mp_exp_same')
async def mp_exp_same_cb(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    period_until = data.get('mp_period_until', '')
    await state.update_data(mp_expiration_date=period_until)
    await state.set_state(AdminStates.waiting_for_manual_prem_purchase_date)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await callback.message.edit_text(
        with_footer(
            f"✅ <b>6-QADAM TUGALLANDI!</b>\n\n"
            f"⏰ <i>Qachon tugaydi:</i> <code>{period_until}</code>\n\n"
            f"<b>7-QADAM (OXIRGI):</b> 🛒 <i>Qachon sotib oldi?</i>\n\n"
            f"Format: <code>YYYY-MM-DD HH:MM:SS</code>\n"
            f"Masalan: <code>2026-08-07 10:41:00</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_manual_prem_expiration_date, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_expiration_date(message: Message, state: FSMContext):
    normalized = _normalize_datetime_str(message.text)
    if not normalized:
        await message.answer(
            with_footer(
                '⚠️ <b>Sana formatida xatolik!</b>\n\n'
                'Iltimos, quyidagi formatlardan birini ishlating:\n'
                '• <code>2027-08-07</code> (faqat sana)\n'
                '• <code>2027-08-07 10:41</code> (sana + vaqt)\n'
                '• <code>2027-08-07 10:41:00</code> (to\'liq)'
            ),
            parse_mode='HTML'
        )
        return
    await state.update_data(mp_expiration_date=normalized)
    await state.set_state(AdminStates.waiting_for_manual_prem_purchase_date)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Bekor qilish', callback_data='mp_cancel')]])
    await message.answer(
        with_footer(
            f"✅ <b>6-QADAM TUGALLANDI!</b>\n\n"
            f"⏰ <i>Qachon tugaydi:</i> <code>{normalized}</code>\n\n"
            f"<b>7-QADAM (OXIRGI):</b> 🛒 <i>Qachon sotib oldi?</i>\n\n"
            f"Format: <code>YYYY-MM-DD HH:MM:SS</code>\n"
            f"Masalan: <code>2026-08-07 10:41:00</code>"
        ),
        parse_mode='HTML',
        reply_markup=kb
    )

@router.message(AdminStates.waiting_for_manual_prem_purchase_date, F.text, ~F.text.in_(MENU_BUTTONS))
async def mp_process_purchase_date(message: Message, state: FSMContext):
    normalized = _normalize_datetime_str(message.text)
    if not normalized:
        await message.answer(
            with_footer(
                '⚠️ <b>Sana formatida xatolik!</b>\n\n'
                'Iltimos, quyidagi formatlardan birini ishlating:\n'
                '• <code>2026-08-07</code> (faqat sana)\n'
                '• <code>2026-08-07 10:41</code> (sana + vaqt)\n'
                '• <code>2026-08-07 10:41:00</code> (to\'liq)'
            ),
            parse_mode='HTML'
        )
        return

    data = await state.get_data()
    amount = data.get('mp_amount', 0)
    user_id = data.get('mp_user_id', 0)
    username = data.get('mp_username')
    payment_amount = data.get('mp_payment_amount', amount)
    premium_type = data.get('mp_premium_type', 'Premium')
    period_until = data.get('mp_period_until', normalized)
    expiration_date = data.get('mp_expiration_date', period_until)
    purchase_date = normalized

    plan_str_with_amount = f"{premium_type} ({payment_amount:,} UZS)"

    await db_req.set_user_premium_custom_dates(
        user_id=user_id,
        start_date=purchase_date,
        end_date=expiration_date,
        plan=premium_type
    )

    new_kassa_total = await db_req.add_payment_record(
        user_id=user_id,
        amount=payment_amount,
        plan=plan_str_with_amount,
        confirmed_by=message.from_user.id
    )

    user_disp = f"{username or ''} (ID: <code>{user_id}</code>)" if username else f"ID: <code>{user_id}</code>"
    time_short = purchase_date[:16] if len(purchase_date) >= 16 else purchase_date

    try:
        user_ntf = (
            f"🎉 <b>PREMIUM OBUNA MANNUAL TARZDA YOQILDI!</b>\n\n"
            f"👑 <b>Obuna turi:</b> {premium_type}\n"
            f"💰 <b>To'langan summa:</b> {payment_amount:,} UZS\n"
            f"⏰ <b>Muddati:</b> {expiration_date}\n\n"
            f"<i>Endi botimizdan kunlik cheklovlarsiz va barcha imtiyozlar bilan foydalanishingiz mumkin!</i> 🍿"
        )
        await message.bot.send_message(with_footer(user_id), user_ntf, parse_mode='HTML')
    except Exception:
        pass

    result_text = (
        f"✅ <b>MANNUAL PREMIUM MUVAFFAQIYATLI QO'SHILDI!</b> 👑\n\n"
        f"👤 <b>Foydalanuvchi:</b> {user_disp}\n"
        f"📋 <b>Plan:</b> {plan_str_with_amount}\n"
        f"🕒 <b>Vaqt:</b> <code>{time_short}</code>\n\n"
        f"📊 <b>Batafsil ma'lumotlar:</b>\n"
        f"• 💰 <b>Plan summasi:</b> <code>{amount:,} UZS</code>\n"
        f"• 💵 <b>To'langan summa:</b> <code>{payment_amount:,} UZS</code>\n"
        f"• 📋 <b>Premium turi:</b> <b>{premium_type}</b>\n"
        f"• 📅 <b>Muddat (qachongacha):</b> <code>{period_until}</code>\n"
        f"• ⏰ <b>Tugash sanasi:</b> <code>{expiration_date}</code>\n"
        f"• 🛒 <b>Sotib olingan sana:</b> <code>{purchase_date}</code>\n"
        f"• 💰 <b>Yangi kassa balansi:</b> <code>{new_kassa_total:,} UZS</code>"
    )

    await state.clear()
    await message.answer(with_footer(result_text), parse_mode='HTML')


@router.message(F.text == 'Premium Sozlamalar 👑')
async def show_premium_settings_panel(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id not in config.ADMINS and (not await db_req.has_permission(user_id, 'view_stats')):
        await message.answer(with_footer("❌ Bu amal uchun sizda ruxsat yo'q."))
        return
    p_1w = await db_req.get_premium_price_1w()
    p_1m = await db_req.get_premium_price_1m()
    p_3m = await db_req.get_premium_price_3m()
    p_6m = await db_req.get_premium_price_6m()
    p_1y = await db_req.get_premium_price_1y()
    txt = f"👑 <b>PREMIUM OBUNA SOZLAMALARI (5 TA PLAN):</b>\n\n1️⃣ <b>1 haftalik (7 kun):</b> <code>{p_1w:,} UZS</code>\n2️⃣ <b>1 oylik (30 kun):</b> <code>{p_1m:,} UZS</code>\n3️⃣ <b>3 oylik (90 kun):</b> <code>{p_3m:,} UZS</code>\n4️⃣ <b>6 oylik (180 kun):</b> <code>{p_6m:,} UZS</code>\n5️⃣ <b>1 yillik (365 kun):</b> <code>{p_1y:,} UZS</code>\n\n<i>Narxlarni o'zgartirish uchun quyidagi tugmalardan birini tanlang:</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'✏️ 1 haftalik ({p_1w:,} UZS)', callback_data='set_prem_price_1w_start'), InlineKeyboardButton(text=f'✏️ 1 oylik ({p_1m:,} UZS)', callback_data='set_prem_price_1m_start')], [InlineKeyboardButton(text=f'✏️ 3 oylik ({p_3m:,} UZS)', callback_data='set_prem_price_3m_start'), InlineKeyboardButton(text=f'✏️ 6 oylik ({p_6m:,} UZS)', callback_data='set_prem_price_6m_start')], [InlineKeyboardButton(text=f'✏️ 1 yillik ({p_1y:,} UZS)', callback_data='set_prem_price_1y_start')]])
    await message.answer(with_footer(txt), parse_mode='HTML', reply_markup=kb)

@router.callback_query(F.data == 'set_prem_price_1w_start')
async def set_prem_price_1w_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_prem_price_1w)
    p_1w = await db_req.get_premium_price_1w()
    await callback.message.edit_text(with_footer(f'✏️ <b>1 haftalik Premium uchun yangi narxni kiriting (UZS):</b>\n\nHozirgi narx: <code>{p_1w:,} UZS</code>\n<i>Masalan: 7000</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_prem_price_1w, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_prem_price_1w_input(message: Message, state: FSMContext):
    text = message.text.strip().replace(' ', '').replace(',', '')
    if not text.isdigit() or int(text) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 7000):'))
        return
    new_price = int(text)
    await state.clear()
    await db_req.set_premium_price_1w(new_price)
    await message.answer(with_footer(f"✅ <b>1 haftalik Premium narxi muvaffaqiyatli o'zgartirildi!</b>\n\n💵 <b>Yangi narx:</b> <code>{new_price:,} UZS</code>"), parse_mode='HTML')

@router.callback_query(F.data == 'set_prem_price_1m_start')
async def set_prem_price_1m_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_prem_price_1m)
    p_1m = await db_req.get_premium_price_1m()
    await callback.message.edit_text(with_footer(f'✏️ <b>1 oylik Premium uchun yangi narxni kiriting (UZS):</b>\n\nHozirgi narx: <code>{p_1m:,} UZS</code>\n<i>Masalan: 20000</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_prem_price_1m, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_prem_price_1m_input(message: Message, state: FSMContext):
    text = message.text.strip().replace(' ', '').replace(',', '')
    if not text.isdigit() or int(text) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 20000):'))
        return
    new_price = int(text)
    await state.clear()
    await db_req.set_premium_price_1m(new_price)
    await message.answer(with_footer(f"✅ <b>1 oylik Premium narxi muvaffaqiyatli o'zgartirildi!</b>\n\n💵 <b>Yangi narx:</b> <code>{new_price:,} UZS</code>"), parse_mode='HTML')

@router.callback_query(F.data == 'set_prem_price_3m_start')
async def set_prem_price_3m_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_prem_price_3m)
    p_3m = await db_req.get_premium_price_3m()
    await callback.message.edit_text(with_footer(f'✏️ <b>3 oylik Premium uchun yangi narxni kiriting (UZS):</b>\n\nHozirgi narx: <code>{p_3m:,} UZS</code>\n<i>Masalan: 50000</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_prem_price_3m, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_prem_price_3m_input(message: Message, state: FSMContext):
    text = message.text.strip().replace(' ', '').replace(',', '')
    if not text.isdigit() or int(text) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 50000):'))
        return
    new_price = int(text)
    await state.clear()
    await db_req.set_premium_price_3m(new_price)
    await message.answer(with_footer(f"✅ <b>3 oylik Premium narxi muvaffaqiyatli o'zgartirildi!</b>\n\n💵 <b>Yangi narx:</b> <code>{new_price:,} UZS</code>"), parse_mode='HTML')

@router.callback_query(F.data == 'set_prem_price_6m_start')
async def set_prem_price_6m_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_prem_price_6m)
    p_6m = await db_req.get_premium_price_6m()
    await callback.message.edit_text(with_footer(f'✏️ <b>6 oylik Premium uchun yangi narxni kiriting (UZS):</b>\n\nHozirgi narx: <code>{p_6m:,} UZS</code>\n<i>Masalan: 100000</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_prem_price_6m, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_prem_price_6m_input(message: Message, state: FSMContext):
    text = message.text.strip().replace(' ', '').replace(',', '')
    if not text.isdigit() or int(text) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 100000):'))
        return
    new_price = int(text)
    await state.clear()
    await db_req.set_premium_price_6m(new_price)
    await message.answer(with_footer(f"✅ <b>6 oylik Premium narxi muvaffaqiyatli o'zgartirildi!</b>\n\n💵 <b>Yangi narx:</b> <code>{new_price:,} UZS</code>"), parse_mode='HTML')

@router.callback_query(F.data == 'set_prem_price_1y_start')
async def set_prem_price_1y_start_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_prem_price_1y)
    p_1y = await db_req.get_premium_price_1y()
    await callback.message.edit_text(with_footer(f'✏️ <b>1 yillik Premium uchun yangi narxni kiriting (UZS):</b>\n\nHozirgi narx: <code>{p_1y:,} UZS</code>\n<i>Masalan: 180000</i>'), parse_mode='HTML')
    await callback.answer()

@router.message(AdminStates.waiting_for_prem_price_1y, F.text, ~F.text.in_(MENU_BUTTONS))
async def process_prem_price_1y_input(message: Message, state: FSMContext):
    text = message.text.strip().replace(' ', '').replace(',', '')
    if not text.isdigit() or int(text) <= 0:
        await message.answer(with_footer('⚠️ Iltimos, faqat musbat butun raqam yuboring (masalan: 180000):'))
        return
    new_price = int(text)
    await state.clear()
    await db_req.set_premium_price_1y(new_price)
    await message.answer(with_footer(f"✅ <b>1 yillik Premium narxi muvaffaqiyatli o'zgartirildi!</b>\n\n💵 <b>Yangi narx:</b> <code>{new_price:,} UZS</code>"), parse_mode='HTML')


# ─── ZAXIRA KANALI SOZLAMALARI (BACKUP CHANNEL) ──────────────────────────────
@router.message(Command("setbackupchannel"), Command("zaxirakanal"))
async def start_set_backup_channel(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMINS:
        await message.answer(with_footer("❌ Bu amal faqat Bosh Adminlar uchun ruxsat etilgan."))
        return
    await state.set_state(AdminStates.waiting_for_backup_channel)
    current_ch = await db_req.get_backup_channel_id()
    disp_ch = current_ch if current_ch else "Hali sozlanmagan ⚠️"
    await message.answer(
        with_footer(
            f"📢 <b>ZAXIRA (BACKUP) KANALI SOZLAMASI</b>\n\n"
            f"📌 <b>Hozirgi zaxira kanali ID:</b> <code>{disp_ch}</code>\n\n"
            f"⚙️ <b>Yangi zaxira kanalini biriktirish uchun:</b>\n"
            f"1. Botni zaxira kanalingizga <b>ADMINISTRATOR</b> qilib qo'shing.\n"
            f"2. Kanalingizdan istalgan bitta xabarni ushbu botga <b>FORWARD (uzating)</b> yoki kanal ID sini (masalan: <code>-1002237000000</code>) yuboring!"
        ),
        parse_mode="HTML"
    )

@router.message(AdminStates.waiting_for_backup_channel)
async def process_backup_channel_input(message: Message, state: FSMContext):
    if message.text in MENU_BUTTONS:
        await state.clear()
        return
        
    channel_id = None
    channel_title = "Zaxira kanali"
    
    if message.forward_from_chat:
        channel_id = str(message.forward_from_chat.id)
        if message.forward_from_chat.title:
            channel_title = message.forward_from_chat.title
    elif message.text:
        txt = message.text.strip()
        if txt.startswith("-100") or txt.lstrip("-").isdigit() or txt.startswith("@"):
            channel_id = txt

    if not channel_id:
        await message.answer(
            with_footer("⚠️ <b>Kanal aniqlanmadi!</b>\n\nIltimos, zaxira kanalingizdan istalgan xabarni botga FORWARD (uzating) qiling yoki <code>-100...</code> ID sini yuboring:"),
            parse_mode="HTML"
        )
        return

    try:
        test_msg = await message.bot.send_message(
            chat_id=channel_id,
            text=f"⚙️ <b>ZAXIRA KANALI TASDIQLANDI!</b>\n\nUshbu kanal `@uzkinobaza_bot` ning rasmiy Zaxira Bazasi sifatida biriktirildi. 🍿",
            parse_mode="HTML"
        )
        await db_req.set_backup_channel_id(channel_id)
        await state.clear()
        await message.answer(
            with_footer(
                f"✅ <b>ZAXIRA KANALI MUVAFFAQIYATLI BIRIKTIRILDI!</b> 🚀\n\n"
                f"📢 <b>Kanal:</b> {channel_title}\n"
                f"🆔 <b>Kanal ID:</b> <code>{channel_id}</code>\n\n"
                f"<i>Endi barcha yangi qo'shiladigan kinolar va avtomatik zaxira fayllari ushbu kanalga 100% yetkazib boriladi!</i>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            with_footer(
                f"❌ <b>Kanalga ulana olmadik!</b>\n\n"
                f"<b>Sababi:</b> Bot ushbu kanalga xabar yubora olmadi.\n"
                f"<b>Xato:</b> <code>{e}</code>\n\n"
                f"💡 <i>Iltimos, botni ushbu kanalga ADMIN (Administrator) qilib qo'shganingizga ishonch hosil qiling va qayta harakat qiling!</i>"
            ),
            parse_mode="HTML"
        )