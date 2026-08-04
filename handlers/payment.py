import asyncio
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import requests as db_req
import config

router = Router()

class PaymentStates(StatesGroup):
    waiting_for_payment_proof = State()
    waiting_for_manual_verification = State()


# ─── PREMIUM OBUNA TO'LOV TIZIMI ───────────────────────────────────────────────
async def show_payment_options(callback: types.CallbackQuery, plan: str, amount: int, months: int):
    """To'lov variantlarini ko'rsatish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Click", callback_data=f"pay_click_{plan}_{amount}_{months}"),
            InlineKeyboardButton(text="💳 Payme", callback_data=f"pay_payme_{plan}_{amount}_{months}")
        ],
        [
            InlineKeyboardButton(text="📞 Manual (Admin)", callback_data=f"pay_manual_{plan}_{amount}_{months}")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back")
        ]
    ])

    try:
        await callback.message.edit_text(
            f"💎 <b>Premium obuna - {plan.upper()}</b>\n\n"
            f"💰 <b>Narx:</b> {amount:,} UZS\n"
            f"⏰ <b>Davomiyligi:</b> {months} oy\n\n"
            f"📋 <b>To'lov usulini tanlang:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        pass  # Message not modified error handling


async def show_manual_payment(callback: types.CallbackQuery):
    """Manual to'lov ma'lumotlarini ko'rsatish"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="premium_back")
        ]
    ])

    payment_info = (
        "💳 <b>Manual to'lov ma'lumotlari:</b>\n\n"
        "📞 <b>Admin bilan bog'laning:</b> @admin\n\n"
        "📋 <b>To'lov ma'lumotlari:</b>\n"
        "• Click: 998901234567\n"
        "• Payme: 998901234567\n"
        "• Uzum: 998901234567\n\n"
        "⚠️ <b>Eslatma:</b> To'lov qilib, chekni adminga yuboring!"
    )

    await callback.message.edit_text(payment_info, parse_mode="HTML", reply_markup=keyboard)


# ─── CLICK TO'LOV TIZIMI ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_click_"))
async def click_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Click to'lovini boshlash"""
    parts = callback.data.split("_")
    plan = parts[2]
    amount = int(parts[3])
    months = int(parts[4])

    if not config.CLICK_SERVICE_ID or not config.CLICK_MERCHANT_ID:
        await callback.answer("Click to'lovi sozlanmagan!", show_alert=True)
        return

    # Click to'lov havolasini yaratish
    click_url = f"https://my.click.uz/services/pay?service_id={config.CLICK_SERVICE_ID}&merchant_id={config.CLICK_MERCHANT_ID}&amount={amount}&transaction_param={callback.from_user.id}_{plan}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 To'lov qilish", url=click_url)
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="premium_back")
        ]
    ])

    try:
        await callback.message.edit_text(
            f"💳 <b>Click to'lovi</b>\n\n"
            f"💰 <b>Narx:</b> {amount:,} UZS\n"
            f"⏰ <b>Davomiyligi:</b> {months} oy\n\n"
            f"👇 <b>To'lov qilish uchun:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        pass  # Message not modified error handling
    await callback.answer()


# ─── PAYME TO'LOV TIZIMI ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_payme_"))
async def payme_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Payme to'lovini boshlash"""
    parts = callback.data.split("_")
    plan = parts[2]
    amount = int(parts[3])
    months = int(parts[4])

    if not config.PAYME_MERCHANT_ID:
        await callback.answer("Payme to'lovi sozlanmagan!", show_alert=True)
        return

    # Payme to'lov havolasini yaratish
    payme_url = f"https://payme.uz/{config.PAYME_MERCHANT_ID}?amount={amount}&params={callback.from_user.id}_{plan}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 To'lov qilish", url=payme_url)
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="premium_back")
        ]
    ])

    try:
        await callback.message.edit_text(
            f"💳 <b>Payme to'lovi</b>\n\n"
            f"💰 <b>Narx:</b> {amount:,} UZS\n"
            f"⏰ <b>Davomiyligi:</b> {months} oy\n\n"
            f"👇 <b>To'lov qilish uchun:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        pass
    await callback.answer()


# ─── MANUAL TO'LOV (ADMIN VERIFICATION) ───────────────────────────────────────
@router.callback_query(F.data.startswith("pay_manual_"))
async def manual_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Manual to'lovni boshlash"""
    parts = callback.data.split("_")
    plan = parts[2]
    amount = int(parts[3])
    months = int(parts[4])

    await state.update_data(plan=plan, amount=amount, months=months)
    await state.set_state(PaymentStates.waiting_for_payment_proof)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="premium_back")
        ]
    ])

    try:
        await callback.message.edit_text(
            f"📞 <b>Manual to'lov</b>\n\n"
            f"💰 <b>Narx:</b> {amount:,} UZS\n"
            f"⏰ <b>Davomiyligi:</b> {months} oy\n\n"
            f"📋 <b>To'lov ma'lumotlari:</b>\n"
            f"• Click: 998901234567\n"
            f"• Payme: 998901234567\n"
            f"• Uzum: 998901234567\n\n"
            f"📸 <b>Chekni yuboring:</b>\n"
            f"To'lov qilib, chekni shu yerga yuboring!",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        pass
    await callback.answer()


# ─── ORQAGA TUGMASI ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "premium_back")
async def premium_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Premium menyusiga qaytish"""
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ 1 oylik - 10,000 UZS", callback_data="premium_monthly"),
            InlineKeyboardButton(text="2️⃣ 3 oylik - 25,000 UZS", callback_data="premium_quarterly")
        ],
        [
            InlineKeyboardButton(text="📞 Manual to'lov", callback_data="premium_manual")
        ]
    ])

    try:
        await callback.message.edit_text(
            "💎 <b>Premium obuna:</b>\n\n"
            "📋 <b>Obuna rejalari:</b>\n\n"
            "1️⃣ <b>1 oylik - 10,000 UZS</b>\n"
            "2️⃣ <b>3 oylik - 25,000 UZS</b> (5,000 UZS tejang!)\n\n"
            "🎁 <b>Premium imtiyozlari:</b>\n"
            "• Kunlik limit yo'q\n"
            "• Cheklovsiz kino ko'rish\n"
            "• Prioritet qo'llab-quvvatlash\n\n"
            "👇 <b>Plan tanlang:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        pass  # Message not modified error handling
    await callback.answer()


# ─── PLAN TANLASH ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "premium_monthly")
async def premium_monthly_callback(callback: types.CallbackQuery, state: FSMContext):
    """1 oylik premium plan tanlash"""
    await show_payment_options(callback, "monthly", 10000, 1)
    await callback.answer()


@router.callback_query(F.data == "premium_quarterly")
async def premium_quarterly_callback(callback: types.CallbackQuery, state: FSMContext):
    """3 oylik premium plan tanlash"""
    await show_payment_options(callback, "quarterly", 25000, 3)
    await callback.answer()


@router.callback_query(F.data == "premium_manual")
async def premium_manual_callback(callback: types.CallbackQuery, state: FSMContext):
    """Manual to'lov tanlash"""
    await show_manual_payment(callback)
    await callback.answer()


# ─── PAYME TO'LOV TIZIMI ───────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("pay_payme_"))
async def payme_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Payme to'lovini boshlash"""
    parts = callback.data.split("_")
    plan = parts[2]
    amount = int(parts[3])
    months = int(parts[4])

    if not config.PAYME_MERCHANT_ID:
        await callback.answer("Payme to'lovi sozlanmagan!", show_alert=True)
        return

    # Payme to'lov havolasini yaratish
    payme_url = f"https://payme.uz/{config.PAYME_MERCHANT_ID}?amount={amount}&params={callback.from_user.id}_{plan}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 To'lov qilish", url=payme_url)
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium_back"),
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="premium_back")
        ]
    ])

    try:
        await callback.message.edit_text(
            f"💳 <b>Payme to'lovi</b>\n\n"
            f"💰 <b>Narx:</b> {amount:,} UZS\n"
            f"⏰ <b>Davomiyligi:</b> {months} oy\n\n"
            f"👇 <b>To'lov qilish uchun:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception:
        pass
    await callback.answer()


# ─── MANUAL TO'LOV (ADMIN VERIFICATION) ───────────────────────────────────────
@router.callback_query(F.data.startswith("pay_manual_"))
async def manual_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Manual to'lovni boshlash"""
    parts = callback.data.split("_")
    plan = parts[2]
    amount = int(parts[3])
    months = int(parts[4])

    await state.update_data(plan=plan, amount=amount, months=months)
    await state.set_state(PaymentStates.waiting_for_payment_proof)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"premium_{plan}")
        ]
    ])

    await callback.message.edit_text(
        f"📞 <b>Manual to'lov</b>\n\n"
        f"💰 <b>Narx:</b> {amount:,} UZS\n"
        f"⏰ <b>Davomiyligi:</b> {months} oy\n\n"
        f"📋 <b>To'lov ma'lumotlari:</b>\n"
        f"• Click: 998901234567\n"
        f"• Payme: 998901234567\n"
        f"• Uzum: 998901234567\n\n"
        f"📸 <b>Chekni yuboring:</b>\n"
        f"To'lov qilib, chekni shu yerga yuboring!",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.message(PaymentStates.waiting_for_payment_proof, F.photo)
async def handle_payment_proof(message: types.Message, state: FSMContext):
    """To'lov chekini qabul qilish"""
    user_id = message.from_user.id
    data = await state.get_data()
    plan = data.get("plan")
    amount = data.get("amount")
    months = data.get("months")

    # Chekni bosh adminga yuborish
    if config.ADMINS:
        admin_chat_id = config.ADMINS[0]  # Bosh admin
    else:
        await message.answer("❌ Admin topilmadi!")
        await state.clear()
        return

    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_payment_{user_id}_{months}_{amount}_{plan}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_payment_{user_id}")
            ]
        ])

        await message.bot.send_photo(
            admin_chat_id,
            photo=message.photo[-1].file_id,
            caption=f"📊 <b>To'lov so'rovi:</b>\n\n"
                    f"👤 <b>User ID:</b> {user_id}\n"
                    f"💰 <b>Narx:</b> {amount:,} UZS\n"
                    f"⏰ <b>Plan:</b> {plan} ({months} oy)\n\n"
                    f"✅ <b>Tasdiqlash:</b> Tugmani bosing\n"
                    f"❌ <b>Rad etish:</b> Tugmani bosing",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        return

    await state.clear()
    await message.answer(
        "✅ <b>Chek qabul qilindi!</b>\n\n"
        "Admin to'lovni tekshiradi va premium obunani yoqadi.\n"
        "Natija tez orada ma'lum bo'ladi.",
        parse_mode="HTML"
    )


# ─── ADMIN TO'LOV TASDIQLASH ───────────────────────────────────────────────────
@router.callback_query(F.data.startswith("approve_payment_"))
async def approve_payment_callback(callback: types.CallbackQuery):
    """Admin to'lovni tasdiqlash (callback)"""
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    try:
        parts = callback.data.split("_")
        user_id = int(parts[2])
        months = int(parts[3])
        amount = int(parts[4])
        plan = parts[5]

        # Premium obunani qo'shish
        await db_req.add_premium_subscription(user_id, "admin_approved", months)

        # Userga xabar yuborish
        try:
            await callback.bot.send_message(
                user_id,
                "🎉 <b>Premium obuna yoqildi!</b>\n\n"
                f"✅ Siz {months} oylik premium obunaga ega bo'ldingiz.\n"
                "Endi cheklovsiz kino ko'rishingiz mumkin!",
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Xabarni yangilash (tugmalarni olib tashlash)
        await callback.message.edit_caption(
            caption=f"📊 <b>To'lov so'rovi:</b>\n\n"
                    f"👤 <b>User ID:</b> {user_id}\n"
                    f"💰 <b>Narx:</b> {amount:,} UZS\n"
                    f"⏰ <b>Plan:</b> {plan} ({months} oy)\n\n"
                    f"✅ <b>TASDIQLANDI!</b>",
            parse_mode="HTML",
            reply_markup=None
        )
        await callback.answer(f"✅ {user_id} uchun {months} oylik premium obuna yoqildi!")
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)


@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment_callback(callback: types.CallbackQuery):
    """Admin to'lovni rad etish (callback)"""
    if callback.from_user.id not in config.ADMINS:
        await callback.answer("❌ Siz admin emassiz!", show_alert=True)
        return

    try:
        user_id = int(callback.data.split("_")[2])

        # Userga xabar yuborish
        try:
            await callback.bot.send_message(
                user_id,
                "❌ <b>To'lov rad etildi!</b>\n\n"
                "Iltimos, to'lovni qayta tekshiring yoki admin bilan bog'laning.",
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Xabarni yangilash (tugmalarni olib tashlash)
        await callback.message.edit_caption(
            caption=f"📊 <b>To'lov so'rovi:</b>\n\n"
                    f"👤 <b>User ID:</b> {user_id}\n\n"
                    f"❌ <b>RAD ETILDI!</b>",
            parse_mode="HTML",
            reply_markup=None
        )
        await callback.answer(f"❌ {user_id} to'lovi rad etildi!")
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)


# ─── ADMIN TO'LOV TASDIQLASH (COMMAND) ───────────────────────────────────────
@router.message(F.text.startswith("/approve_premium"))
async def approve_premium(message: types.Message):
    """Admin to'lovni tasdiqlash (command)"""
    if message.from_user.id not in config.ADMINS:
        await message.answer("❌ Siz admin emassiz!")
        return

    try:
        parts = message.text.split()
        user_id = int(parts[1])
        months = int(parts[2])

        # Premium obunani qo'shish
        await db_req.add_premium_subscription(user_id, "admin_approved", months)

        # Userga xabar yuborish
        try:
            await message.bot.send_message(
                user_id,
                "🎉 <b>Premium obuna yoqildi!</b>\n\n"
                f"✅ Siz {months} oylik premium obunaga ega bo'ldingiz.\n"
                "Endi cheklovsiz kino ko'rishingiz mumkin!",
                parse_mode="HTML"
            )
        except Exception:
            pass

        await message.answer(f"✅ {user_id} uchun {months} oylik premium obuna yoqildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")


@router.message(F.text.startswith("/reject_premium"))
async def reject_premium(message: types.Message):
    """Admin to'lovni rad etish (command)"""
    if message.from_user.id not in config.ADMINS:
        await message.answer("❌ Siz admin emassiz!")
        return

    try:
        user_id = int(message.text.split()[1])

        # Userga xabar yuborish
        try:
            await message.bot.send_message(
                user_id,
                "❌ <b>To'lov rad etildi!</b>\n\n"
                "Iltimos, to'lovni qayta tekshiring yoki admin bilan bog'laning.",
                parse_mode="HTML"
            )
        except Exception:
            pass

        await message.answer(f"❌ {user_id} to'lovi rad etildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
