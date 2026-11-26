import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# SETTINGS

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or "0")

CBE_NAME = os.getenv("CBE_ACCOUNT_NAME", "Admin irraa gaafadhu")
CBE_NUMBER = os.getenv("CBE_ACCOUNT_NUMBER", "Admin irraa gaafadhu")

TELEBIRR_NAME = os.getenv("TELEBIRR_ACCOUNT_NAME", "Admin irraa gaafadhu")
TELEBIRR_NUMBER = os.getenv("TELEBIRR_ACCOUNT_NUMBER", "Admin irraa gaafadhu")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing in Render Environment!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_languages = {}


# LANGUAGES

TEXTS = {
    "om": {
        "welcome": "🌍 Baga gara Kalid Global Ads dhuftan!",
        "services": "Tajaajila beeksisa addunyaa.",
        "order": "📢 Beeksisa haaraa",
        "contact": "☎️ Admin qunnami",
        "payment": "💳 Kaffaltii",
        "received": "✅ Gaaffiin kee nu gaheera. Admin si qunnama.",
        "choose": "Platformii beeksisaaf filadhu:"
    },
    "am": {
        "welcome": "🌍 ወደ Kalid Global Ads እንኳን በደህና መጡ!",
        "services": "ዓለም አቀፍ የማስታወቂያ አገልግሎት።",
        "order": "📢 አዲስ ማስታወቂያ",
        "contact": "☎️ Admin ያግኙ",
        "payment": "💳 ክፍያ",
        "received": "✅ ጥያቄዎ ደርሶናል።",
        "choose": "የማስታወቂያ መድረክ ይምረጡ:"
    },
    "en": {
        "welcome": "🌍 Welcome to Kalid Global Ads!",
        "services": "Worldwide advertising services.",
        "order": "📢 New Advertisement",
        "contact": "☎️ Contact Admin",
        "payment": "💳 Payment",
        "received": "✅ Your request has been received.",
        "choose": "Choose your advertising platform:"
    }
}


# USER STATES

class OrderForm(StatesGroup):
    platform = State()
    content = State()


class ContactForm(StatesGroup):
    message = State()


class PaymentForm(StatesGroup):
    receipt = State()


# MAIN MENU

def main_menu(lang):
    t = TEXTS[lang]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t["order"],
                    callback_data="new_order"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t["payment"],
                    callback_data="payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text=t["contact"],
                    callback_data="contact"
                )
            ]
        ]
    )


# START

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Afaan Oromoo",
                    callback_data="lang_om"
                )
            ],
            [
                InlineKeyboardButton(
                    text="አማርኛ",
                    callback_data="lang_am"
                )
            ],
            [
                InlineKeyboardButton(
                    text="English",
                    callback_data="lang_en"
                )
            ]
        ]
    )

    await message.answer(
        "🌍 KALID GLOBAL ADS\n\n"
        "Welcome!\n"
        "Please select your language:",
        reply_markup=keyboard
    )


# LANGUAGE SELECTION

@dp.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    lang = callback.data.split("_")[1]
    user_languages[callback.from_user.id] = lang

    t = TEXTS[lang]

    await callback.message.edit_text(
        f'{t["welcome"]}\n\n{t["services"]}',
        reply_markup=main_menu(lang)
    )

    await callback.answer()


# NEW ADVERTISEMENT

@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery, state: FSMContext):
    lang = user_languages.get(callback.from_user.id, "en")

    await state.set_state(OrderForm.platform)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Facebook", callback_data="platform:Facebook")],
            [InlineKeyboardButton(text="Instagram", callback_data="platform:Instagram")],
            [InlineKeyboardButton(text="TikTok", callback_data="platform:TikTok")],
            [InlineKeyboardButton(text="YouTube", callback_data="platform:YouTube")],
            [InlineKeyboardButton(text="Telegram", callback_data="platform:Telegram")],
            [InlineKeyboardButton(text="Google Ads", callback_data="platform:Google Ads")]
        ]
    )

    await callback.message.answer(
        TEXTS[lang]["choose"],
        reply_markup=keyboard
    )

    await callback.answer()


# PLATFORM SELECTION

@dp.callback_query(OrderForm.platform, F.data.startswith("platform:"))
async def select_platform(callback: CallbackQuery, state: FSMContext):
    platform = callback.data.split(":", 1)[1]

    await state.update_data(platform=platform)
    await state.set_state(OrderForm.content)

    await callback.message.answer(
        f"✅ Selected: {platform}\n\n"
        "Now send your advertisement.\n"
        "You can send text, photo or video."
    )

    await callback.answer()


# RECEIVE ADVERTISEMENT

@dp.message(OrderForm.content, F.text | F.photo | F.video)
async def receive_advertisement(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return

    if ADMIN_ID == 0:
        await message.answer("Admin is not configured. Please try later.")
        return

    data = await state.get_data()
    platform = data.get("platform", "Not selected")
    username = message.from_user.username or "No username"

    try:
        await bot.send_message(
            ADMIN_ID,
            "📢 NEW ADVERTISEMENT REQUEST\n\n"
            f"Customer: {message.from_user.full_name}\n"
            f"Username: @{username}\n"
            f"User ID: {message.from_user.id}\n"
            f"Platform: {platform}"
        )

        await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        lang = user_languages.get(message.from_user.id, "en")

        await message.answer(
            TEXTS[lang]["received"]
        )

        await state.clear()

    except Exception:
        logger.exception("Advertisement forwarding failed")
        await message.answer(
            "Sorry! Something went wrong. Please try again."
        )


# PAYMENT MENU

@dp.callback_query(F.data == "payment")
async def payment_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏦 CBE Bank Transfer",
                    callback_data="pay_cbe"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱 Telebirr",
                    callback_data="pay_telebirr"
                )
            ]
        ]
    )

    await callback.message.answer(
        "💳 KALID GLOBAL ADS PAYMENT\n\n"
        "Choose your payment method:",
        reply_markup=keyboard
    )

    await callback.answer()


# CBE PAYMENT

@dp.callback_query(F.data == "pay_cbe")
async def pay_cbe(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_method="CBE Bank")

    await callback.message.answer(
        "🏦 CBE BANK TRANSFER\n\n"
        f"Account Name: {CBE_NAME}\n"
        f"Account Number: {CBE_NUMBER}\n\n"
        "Please confirm the payment details with Admin "
        "before transferring money.\n\n"
        "After payment, send your payment receipt or screenshot here."
    )

    await state.set_state(PaymentForm.receipt)
    await callback.answer()


# TELEBIRR PAYMENT

@dp.callback_query(F.data == "pay_telebirr")
async def pay_telebirr(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_method="Telebirr")

    await callback.message.answer(
        "📱 TELEBIRR PAYMENT\n\n"
        f"Account Name: {TELEBIRR_NAME}\n"
        f"Telebirr Number: {TELEBIRR_NUMBER}\n\n"
        "Please confirm the payment details with Admin "
        "before transferring money.\n\n"
        "After payment, send your payment receipt or screenshot here."
    )

    await state.set_state(PaymentForm.receipt)
    await callback.answer()


# RECEIVE PAYMENT RECEIPT

@dp.message(PaymentForm.receipt, F.photo | F.document | F.text)
async def receive_payment_receipt(message: Message, state: FSMContext):
    if ADMIN_ID == 0:
        await message.answer("Admin is not configured.")
        return

    data = await state.get_data()
    method = data.get("payment_method", "Unknown")

    username = message.from_user.username or "No username"

    try:
        await bot.send_message(
            ADMIN_ID,
            "💳 NEW PAYMENT RECEIPT\n\n"
            f"Customer: {message.from_user.full_name}\n"
            f"Username: @{username}\n"
            f"User ID: {message.from_user.id}\n"
            f"Payment Method: {method}\n\n"
            "⚠️ Please verify the payment before approving it."
        )

        await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        await message.answer(
            "✅ Your payment receipt has been sent to our Admin team.\n\n"
            "Your payment will be checked manually. "
            "Your advertisement will start after confirmation."
        )

        await state.clear()

    except Exception:
        logger.exception("Payment receipt forwarding failed")
        await message.answer(
            "Sorry! We could not send your receipt. Please try again."
        )


# CONTACT ADMIN

@dp.callback_query(F.data == "contact")
async def contact_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ContactForm.message)

    await callback.message.answer(
        "☎️ Please write your message to our Admin team."
    )

    await callback.answer()


# RECEIVE CUSTOMER MESSAGE

@dp.message(ContactForm.message)
async def receive_contact(message: Message, state: FSMContext):
    if ADMIN_ID == 0:
        await message.answer("Admin is not configured yet.")
        return

    try:
        await bot.send_message(
            ADMIN_ID,
            "📩 NEW CUSTOMER MESSAGE\n\n"
            f"Name: {message.from_user.full_name}\n"
            f"User ID: {message.from_user.id}"
        )

        await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        await message.answer(
            "✅ Your message has been sent to our team."
        )

        await state.clear()

    except Exception:
        logger.exception("Contact forwarding failed")
        await message.answer(
            "Message could not be sent. Please try again."
        )


# ADMIN PANEL

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Access denied.")
        return

    await message.answer(
        "👨‍💼 KALID GLOBAL ADS ADMIN PANEL\n\n"
        "✅ Bot is running.\n"
        "📢 Advertisement requests are forwarded here.\n"
        "💳 Payment receipts are forwarded here.\n"
        "🌍 Languages: Oromoo, Amharic, English."
    )


# MAIN FUNCTION

async def main():
    logger.info("Kalid Global Ads Bot is starting...")

    await dp.start_polling(
        bot,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    asyncio.run(main())