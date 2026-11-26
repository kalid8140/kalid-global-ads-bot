import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)

if not TOKEN:
raise ValueError("BOT_TOKEN is missing!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_languages = {}

TEXTS = {
"om": {
"welcome": "🌍 Baga gara Kalid Global Ads dhuftan!",
"services": "Tajaajila beeksisa addunyaa.",
"order": "📢 Beeksisa haaraa",
"contact": "☎️ Admin qunnami",
"received": "✅ Gaaffiin kee nu gaheera. Admin si qunnama."
},
"am": {
"welcome": "🌍 ወደ Kalid Global Ads እንኳን በደህና መጡ!",
"services": "ዓለም አቀፍ የማስታወቂያ አገልግሎት።",
"order": "📢 አዲስ ማስታወቂያ",
"contact": "☎️ Admin ያግኙ",
"received": "✅ ጥያቄዎ ደርሶናል። Admin ያነጋግርዎታል።"
},
"en": {
"welcome": "🌍 Welcome to Kalid Global Ads!",
"services": "Worldwide advertising services.",
"order": "📢 New Advertisement",
"contact": "☎️ Contact Admin",
"received": "✅ Your request has been received. Our team will contact you."
}
}

@dp.message(CommandStart())
async def start(message: Message):
keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
])

await message.answer(
    "🌍 KALID GLOBAL ADS\n\nChoose your language:",
    reply_markup=keyboard
)

@dp.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery):
lang = callback.data.split("_")[1]
user_languages[callback.from_user.id] = lang

t = TEXTS[lang]

keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
])

await callback.message.edit_text(
    f'{t["welcome"]}\n\n{t["services"]}',
    reply_markup=keyboard
)
await callback.answer()

@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery):
lang = user_languages.get(callback.from_user.id, "en")

await callback.message.answer(
    "📢 Please send your advertisement text, photo or video.\n\n"
    "Platforms:\n"
    "Facebook\n"
    "Instagram\n"
    "TikTok\n"
    "YouTube\n"
    "Telegram\n"
    "Google Ads"
)
await callback.answer()

@dp.message(F.text | F.photo | F.video)
async def receive_advertisement(message: Message):
user_id = message.from_user.id

if user_id == ADMIN_ID:
    return

lang = user_languages.get(user_id)

if not lang:
    await message.answer("Please use /start first.")
    return

if not ADMIN_ID:
    await message.answer("Admin is not configured.")
    return

try:
    await bot.send_message(
        ADMIN_ID,
        f"NEW ADVERTISEMENT REQUEST\n\n"
        f"Name: {message.from_user.full_name}\n"
        f"Username: @{message.from_user.username}\n"
        f"User ID: {user_id}"
    )

    await bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

    await message.answer(TEXTS[lang]["received"])

except Exception:
    logging.exception("Forwarding error")
    await message.answer("Please try again later.")

@dp.callback_query(F.data == "contact")
async def contact_admin(callback: CallbackQuery):
await callback.message.answer(
"Please send your message here. Our team will help you."
)
await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: Message):
if message.from_user.id != ADMIN_ID:
await message.answer("Access denied.")
return

await message.answer(
    "KALID GLOBAL ADS ADMIN PANEL\n\n"
    "Bot is running successfully!"
)

async def main():
logging.info("Kalid Global Ads Bot is starting...")
await dp.start_polling(bot)

if name == "main":
asyncio.run(main())