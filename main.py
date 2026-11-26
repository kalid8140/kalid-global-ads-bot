import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
Message,
CallbackQuery,
InlineKeyboardMarkup,
InlineKeyboardButton
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

LANGUAGES = {
"om": "Afaan Oromoo",
"am": "አማርኛ",
"en": "English"
}

TEXTS = {
"om": {
"welcome": "🌍 Baga gara Kalid Global Ads dhuftan!",
"services": "Tajaajila beeksisa addunyaa.",
"order": "📢 Beeksisa haaraa",
"contact": "☎️ Admin qunnami"
},
"am": {
"welcome": "🌍 ወደ Kalid Global Ads እንኳን በደህና መጡ!",
"services": "ዓለም አቀፍ የማስታወቂያ አገልግሎት።",
"order": "📢 አዲስ ማስታወቂያ",
"contact": "☎️ Admin ያግኙ"
},
"en": {
"welcome": "🌍 Welcome to Kalid Global Ads!",
"services": "Worldwide advertising services.",
"order": "📢 New Advertisement",
"contact": "☎️ Contact Admin"
}
}

user_languages = {}

@dp.message(CommandStart())
async def start(message: Message):
keyboard = InlineKeyboardMarkup(inline_keyboard=[
[
InlineKeyboardButton(text="Afaan Oromoo", callback_data="lang_om"),
InlineKeyboardButton(text="አማርኛ", callback_data="lang_am")
],
[
InlineKeyboardButton(text="English", callback_data="lang_en")
]
])

await message.answer(
    "🌍 KALID GLOBAL ADS\n\nChoose your language / Afaan filadhu:",
    reply_markup=keyboard
)

@dp.callback_query(F.data.startswith("lang_"))
async def choose_language(callback: CallbackQuery):
lang = callback.data.split("_")[1]
user_languages[callback.from_user.id] = lang

t = TEXTS[lang]

keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=t["order"], callback_data="new_order")],
    [InlineKeyboardButton(text=t["contact"], callback_data="contact")]
])

await callback.message.edit_text(
    f'{t["welcome"]}\n\n{t["services"]}',
    reply_markup=keyboard
)
await callback.answer()

@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery):
await callback.message.answer(
"📢 Send your advertisement text, photo or video.\n\n"
"Please include the platform you want to advertise on."
)
await callback.answer()

@dp.message(F.text | F.photo | F.video)
async def receive_advertisement(message: Message):
if message.from_user.id == ADMIN_ID:
return

if message.from_user.id not in user_languages:
    await message.answer("Please use /start and select your language.")
    return

if not ADMIN_ID:
    await message.answer("Admin is not configured yet.")
    return

await bot.forward_message(
    chat_id=ADMIN_ID,
    from_chat_id=message.chat.id,
    message_id=message.message_id
)

await message.answer(
    "✅ Your advertisement request has been received. "
    "Our team will contact you about payment and publishing."
)

await bot.send_message(
    ADMIN_ID,
    f"📢 NEW AD REQUEST\n"
    f"Customer: {message.from_user.full_name}\n"
    f"User ID: {message.from_user.id}"
)

@dp.message(Command("admin"))
async def admin(message: Message):
if message.from_user.id != ADMIN_ID:
return

await message.answer(
    "👨‍💼 KALID GLOBAL ADS ADMIN PANEL\n\n"
    "New advertisement requests will appear here."
)

async def main():
if not TOKEN:
raise ValueError("BOT_TOKEN is missing!")

await dp.start_polling(bot)

if name == "main":
asyncio.run(main())
