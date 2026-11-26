import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
Message,
CallbackQuery,
InlineKeyboardMarkup,
InlineKeyboardButton
)

==============================

SETTINGS

==============================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

if not TOKEN:
raise ValueError("BOT_TOKEN is missing!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_languages = {}

==============================

LANGUAGES

==============================

TEXTS = {
"om": {
"welcome": "🌍 Baga gara Kalid Global Ads dhuftan!",
"services": "Tajaajila beeksisa addunyaa.",
"order": "📢 Beeksisa haaraa",
"contact": "☎️ Admin qunnami",
"received": "✅ Gaaffiin beeksisa kee nu gaheera. Admin si qunnama.",
"choose": "Afaan kee filadhu:"
},
"am": {
"welcome": "🌍 ወደ Kalid Global Ads እንኳን በደህና መጡ!",
"services": "ዓለም አቀፍ የማስታወቂያ አገልግሎት።",
"order": "📢 አዲስ ማስታወቂያ",
"contact": "☎️ Admin ያግኙ",
"received": "✅ የማስታወቂያ ጥያቄዎ ደርሶናል። Admin ያነጋግርዎታል።",
"choose": "ቋንቋዎን ይምረጡ:"
},
"en": {
"welcome": "🌍 Welcome to Kalid Global Ads!",
"services": "Worldwide advertising services.",
"order": "📢 New Advertisement",
"contact": "☎️ Contact Admin",
"received": "✅ Your advertisement request has been received. Our team will contact you.",
"choose": "Choose your language:"
}
}

==============================

START COMMAND

==============================

@dp.message(CommandStart())
async def start(message: Message):

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Afaan Oromoo",
                callback_data="lang_om"
            ),
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
    "Please select your language.\n"
    "Afaan kee filadhu.",
    reply_markup=keyboard
)

==============================

LANGUAGE SELECTION

==============================

@dp.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery):

lang = callback.data.split("_")[1]

user_languages[callback.from_user.id] = lang

t = TEXTS[lang]

keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t["order"],
                callback_data="new_order"
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

await callback.message.edit_text(
    f'{t["welcome"]}\n\n{t["services"]}',
    reply_markup=keyboard
)

await callback.answer()

==============================

NEW ADVERTISEMENT

==============================

@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery):

lang = user_languages.get(callback.from_user.id, "en")

await callback.message.answer(
    "📢 Please send your advertisement text, photo or video.\n\n"
    "Include the platform you want to advertise on:\n\n"
    "Facebook\n"
    "Instagram\n"
    "TikTok\n"
    "YouTube\n"
    "Telegram\n"
    "Google Ads"
)

await callback.answer()

==============================

RECEIVE ADVERTISEMENT

==============================

@dp.message(F.text | F.photo | F.video)
async def receive_advertisement(message: Message):

user_id = message.from_user.id

if user_id == ADMIN_ID:
    return

lang = user_languages.get(user_id)

if not lang:
    await message.answer(
        "Please use /start and select your language."
    )
    return

if ADMIN_ID == 0:
    await message.answer(
        "Admin is not configured. Please contact support."
    )
    return

try:
    await bot.send_message(
        ADMIN_ID,
        f"📢 NEW ADVERTISEMENT REQUEST\n\n"
        f"Customer: {message.from_user.full_name}\n"
        f"Username: @{message.from_user.username}\n"
        f"User ID: {user_id}"
    )

    await bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

    await message.answer(TEXTS[lang]["received"])

except Exception as error:
    logging.exception("Advertisement forwarding failed")
    await message.answer(
        "Sorry, your request could not be forwarded. Please try again."
    )

==============================

CONTACT ADMIN

==============================

@dp.callback_query(F.data == "contact")
async def contact_admin(callback: CallbackQuery):

lang = user_languages.get(callback.from_user.id, "en")

if ADMIN_ID:
    admin_text = {
        "om": "Adminiin gaaffii kee erguuf, asitti beeksisa kee ergi.",
        "am": "ለAdmin መልዕክት ለመላክ እዚህ ያግኙን።",
        "en": "Send your message here and our admin team will help you."
    }

    await callback.message.answer(admin_text[lang])

else:
    await callback.message.answer(
        "Admin contact is not configured yet."
    )

await callback.answer()

==============================

ADMIN PANEL

==============================

@dp.message(Command("admin"))
async def admin_panel(message: Message):

if message.from_user.id != ADMIN_ID:
    await message.answer("⛔ Access denied.")
    return

await message.answer(
    "👨‍💼 KALID GLOBAL ADS ADMIN PANEL\n\n"
    "✅ Bot is running.\n"
    "📢 Advertisement requests will appear here.\n"
    "🌍 Languages: Oromoo, Amharic, English."
)

==============================

MAIN

==============================

async def main():

logging.info("Kalid Global Ads Bot is starting...")

await dp.start_polling(bot)

if name == "main":
asyncio.run(main())