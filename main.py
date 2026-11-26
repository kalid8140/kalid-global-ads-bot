import asyncio
import os
import logging
import tempfile
import uuid
from urllib.parse import urlencode

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# ================= SETTINGS =================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0").strip() or "0")

CBE_NAME = os.getenv("CBE_ACCOUNT_NAME", "Admin irraa gaafadhu")
CBE_NUMBER = os.getenv("CBE_ACCOUNT_NUMBER", "Admin irraa gaafadhu")
TELEBIRR_NAME = os.getenv("TELEBIRR_ACCOUNT_NAME", "Admin irraa gaafadhu")
TELEBIRR_NUMBER = os.getenv("TELEBIRR_ACCOUNT_NUMBER", "Admin irraa gaafadhu")

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.getenv("YOUTUBE_REFRESH_TOKEN", "").strip()

BASE_URL = "https://kalid-global-ads-bot.onrender.com"
REDIRECT_URI = f"{BASE_URL}/oauth2callback"

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload"
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing in Render Environment!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_languages = {}
pending_youtube_uploads = {}
oauth_state = None


# ================= YOUTUBE PRICES =================

YOUTUBE_PRICES = {
    "shorts": {
        "24h": 400,
        "3d": 800,
        "7d": 1000,
        "15d": 1800,
        "30d": 3200
    },
    "normal": {
        "24h": 600,
        "3d": 1200,
        "7d": 1800,
        "15d": 3000,
        "30d": 5500
    }
}

DURATION_NAMES = {
    "24h": "24 Hours",
    "3d": "3 Days",
    "7d": "7 Days",
    "15d": "15 Days",
    "30d": "30 Days"
}


# ================= LANGUAGES =================

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


# ================= STATES =================

class OrderForm(StatesGroup):
    platform = State()
    youtube_format = State()
    youtube_duration = State()
    content = State()


class ContactForm(StatesGroup):
    message = State()


class PaymentForm(StatesGroup):
    receipt = State()


# ================= KEYBOARDS =================

def main_menu(lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["order"], callback_data="new_order")],
        [InlineKeyboardButton(text=t["payment"], callback_data="payment")],
        [InlineKeyboardButton(text=t["contact"], callback_data="contact")]
    ])


# ================= YOUTUBE AUTH =================

def make_oauth_flow(state=None):
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        raise RuntimeError("YouTube OAuth Client ID/Secret missing.")

    client_config = {
        "web": {
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=YOUTUBE_SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI
    return flow


def get_youtube_service():
    if not YOUTUBE_REFRESH_TOKEN:
        raise RuntimeError(
            "YouTube is not connected. Add YOUTUBE_REFRESH_TOKEN in Render."
        )

    credentials = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=YOUTUBE_SCOPES
    )

    return build(
        "youtube",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )


def upload_video_sync(file_path, title, description):
    youtube = get_youtube_service()

    request_body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": "22",
            "tags": ["Kalid Global Ads", "JokeShift"]
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        file_path,
        mimetype="video/*",
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = request.execute()
    return response.get("id")


# ================= START =================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Afaan Oromoo", callback_data="lang_om")],
        [InlineKeyboardButton(text="አማርኛ", callback_data="lang_am")],
        [InlineKeyboardButton(text="English", callback_data="lang_en")]
    ])

    await message.answer(
        "🌍 KALID GLOBAL ADS\n\n"
        "Welcome!\n"
        "Please select your language:",
        reply_markup=keyboard
    )


# ================= LANGUAGE =================

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


# ================= NEW ORDER =================

@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery, state: FSMContext):
    lang = user_languages.get(callback.from_user.id, "en")
    await state.clear()
    await state.set_state(OrderForm.platform)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Facebook", callback_data="platform:Facebook")],
        [InlineKeyboardButton(text="Instagram", callback_data="platform:Instagram")],
        [InlineKeyboardButton(text="TikTok", callback_data="platform:TikTok")],
        [InlineKeyboardButton(text="YouTube", callback_data="platform:YouTube")],
        [InlineKeyboardButton(text="Telegram", callback_data="platform:Telegram")],
        [InlineKeyboardButton(text="Google Ads", callback_data="platform:Google Ads")]
    ])

    await callback.message.answer(
        TEXTS[lang]["choose"],
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(OrderForm.platform, F.data.startswith("platform:"))
async def select_platform(callback: CallbackQuery, state: FSMContext):
    platform = callback.data.split(":", 1)[1]
    await state.update_data(platform=platform)

    if platform == "YouTube":
        await state.set_state(OrderForm.youtube_format)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="▶️ YouTube Shorts",
                callback_data="ytformat:shorts"
            )],
            [InlineKeyboardButton(
                text="🎬 Normal YouTube Video",
                callback_data="ytformat:normal"
            )]
        ])

        await callback.message.answer(
            "🔥 YOUTUBE ADVERTISING\n\nChoose your advertising type:",
            reply_markup=keyboard
        )
    else:
        await state.set_state(OrderForm.content)
        await callback.message.answer(
            f"✅ Selected: {platform}\n\n"
            "Now send your advertisement as text, photo or video."
        )

    await callback.answer()


# ================= YOUTUBE FORMAT =================

@dp.callback_query(OrderForm.youtube_format, F.data.startswith("ytformat:"))
async def select_youtube_format(callback: CallbackQuery, state: FSMContext):
    video_format = callback.data.split(":")[1]
    await state.update_data(youtube_format=video_format)
    await state.set_state(OrderForm.youtube_duration)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="24 Hours", callback_data="ytduration:24h")],
        [InlineKeyboardButton(text="3 Days", callback_data="ytduration:3d")],
        [InlineKeyboardButton(text="7 Days", callback_data="ytduration:7d")],
        [InlineKeyboardButton(text="15 Days", callback_data="ytduration:15d")],
        [InlineKeyboardButton(text="30 Days", callback_data="ytduration:30d")]
    ])

    await callback.message.answer(
        "📅 Choose advertising duration:",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(OrderForm.youtube_duration, F.data.startswith("ytduration:"))
async def select_youtube_duration(callback: CallbackQuery, state: FSMContext):
    duration = callback.data.split(":")[1]
    data = await state.get_data()
    video_format = data.get("youtube_format", "shorts")

    price = YOUTUBE_PRICES[video_format][duration]

    await state.update_data(duration=duration, price=price)
    await state.set_state(OrderForm.content)

    format_name = (
        "YouTube Shorts" if video_format == "shorts"
        else "Normal YouTube Video"
    )

    await callback.message.answer(
        "✅ YOUTUBE ADVERTISEMENT ORDER\n\n"
        f"📺 Type: {format_name}\n"
        f"📅 Duration: {DURATION_NAMES[duration]}\n"
        f"💰 Price: {price} ETB\n\n"
        "Send your video here. Admin will review it and confirm payment."
    )
    await callback.answer()


# ================= RECEIVE ADVERTISEMENT =================

@dp.message(OrderForm.content, F.text | F.photo | F.video | F.document)
async def receive_advertisement(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        return

    if ADMIN_ID == 0:
        await message.answer("Admin is not configured. Please try later.")
        return

    data = await state.get_data()
    platform = data.get("platform", "Not selected")
    username = message.from_user.username or "No username"

    order_id = uuid.uuid4().hex[:10]
    details = (
        "📢 NEW ADVERTISEMENT REQUEST\n\n"
        f"Order ID: {order_id}\n"
        f"Customer: {message.from_user.full_name}\n"
        f"Username: @{username}\n"
        f"User ID: {message.from_user.id}\n"
        f"Platform: {platform}\n"
    )

    video_file_id = None
    video_title = message.caption or f"JokeShift - {order_id}"

    if message.video:
        video_file_id = message.video.file_id
    elif message.document and (message.document.mime_type or "").startswith("video/"):
        video_file_id = message.document.file_id

    if platform == "YouTube":
        video_format = data.get("youtube_format", "shorts")
        duration = data.get("duration", "Not selected")
        price = data.get("price", 0)

        format_name = (
            "YouTube Shorts" if video_format == "shorts"
            else "Normal YouTube Video"
        )

        details += (
            f"Video Type: {format_name}\n"
            f"Duration: {DURATION_NAMES.get(duration, duration)}\n"
            f"Price: {price} ETB\n"
            "Channel: JokeShift (@Soulturn7)\n"
        )

        if video_file_id:
            pending_youtube_uploads[order_id] = {
                "file_id": video_file_id,
                "customer_id": message.from_user.id,
                "title": video_title,
                "format": video_format,
                "duration": duration
            }

    try:
        if platform == "YouTube" and video_file_id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="▶️ Upload to YouTube",
                    callback_data=f"ytupload:{order_id}"
                )]
            ])
            await bot.send_message(
                ADMIN_ID,
                details + "\n⚠️ Check payment before uploading.",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(ADMIN_ID, details)

        await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        lang = user_languages.get(message.from_user.id, "en")
        await message.answer(
            TEXTS[lang]["received"]
            + "\n\nAdmin will review your advertisement and contact you."
        )
        await state.clear()

    except Exception:
        logger.exception("Advertisement forwarding failed")
        await message.answer("Sorry! Something went wrong. Please try again.")


# ================= ADMIN YOUTUBE UPLOAD =================

@dp.callback_query(F.data.startswith("ytupload:"))
async def admin_youtube_upload(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Admin only.", show_alert=True)
        return

    order_id = callback.data.split(":", 1)[1]
    order = pending_youtube_uploads.get(order_id)

    if not order:
        await callback.answer(
            "Order not found. It may have expired after a restart.",
            show_alert=True
        )
        return

    if not YOUTUBE_REFRESH_TOKEN:
        await callback.answer(
            "YouTube is not connected yet. Complete OAuth first.",
            show_alert=True
        )
        return

    await callback.answer("Uploading video. Please wait...")

    temp_path = None
    try:
        telegram_file = await bot.get_file(order["file_id"])

        with tempfile.NamedTemporaryFile(
            suffix=".mp4",
            delete=False
        ) as temp_file:
            temp_path = temp_file.name

        await bot.download_file(
            telegram_file.file_path,
            destination=temp_path
        )

        title = order["title"]
        if order["format"] == "shorts" and "#Shorts" not in title:
            title = f"{title} #Shorts"

        description = (
            "Promoted through Kalid Global Ads.\n"
            "YouTube channel: JokeShift (@Soulturn7)\n"
            f"Advertising duration: {DURATION_NAMES[order['duration']]}"
        )

        video_id = await asyncio.to_thread(
            upload_video_sync,
            temp_path,
            title,
            description
        )

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        await bot.send_message(
            ADMIN_ID,
            "✅ VIDEO UPLOADED SUCCESSFULLY!\n\n"
            f"Order ID: {order_id}\n"
            f"YouTube link: {video_url}"
        )

        await bot.send_message(
            order["customer_id"],
            "✅ Your video has been uploaded to YouTube!\n\n"
            f"{video_url}"
        )

        pending_youtube_uploads.pop(order_id, None)

    except Exception as error:
        logger.exception("YouTube upload failed")
        await bot.send_message(
            ADMIN_ID,
            f"❌ YouTube upload failed.\n\nError: {str(error)[:1000]}"
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


# ================= PAYMENT MENU =================

@dp.callback_query(F.data == "payment")
async def payment_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 CBE Bank Transfer", callback_data="pay_cbe")],
        [InlineKeyboardButton(text="📱 Telebirr", callback_data="pay_telebirr")]
    ])

    await callback.message.answer(
        "💳 KALID GLOBAL ADS PAYMENT\n\nChoose your payment method:",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data == "pay_cbe")
async def pay_cbe(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_method="CBE Bank")

    await callback.message.answer(
        "🏦 CBE BANK TRANSFER\n\n"
        f"Account Name: {CBE_NAME}\n"
        f"Account Number: {CBE_NUMBER}\n\n"
        "Confirm payment details with Admin before transferring.\n"
        "After payment, send your receipt or screenshot here."
    )
    await state.set_state(PaymentForm.receipt)
    await callback.answer()


@dp.callback_query(F.data == "pay_telebirr")
async def pay_telebirr(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment_method="Telebirr")

    await callback.message.answer(
        "📱 TELEBIRR PAYMENT\n\n"
        f"Account Name: {TELEBIRR_NAME}\n"
        f"Telebirr Number: {TELEBIRR_NUMBER}\n\n"
        "Confirm payment details with Admin before transferring.\n"
        "After payment, send your receipt or screenshot here."
    )
    await state.set_state(PaymentForm.receipt)
    await callback.answer()


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
            "⚠️ Verify the payment before approving it."
        )

        await bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        await message.answer(
            "✅ Your payment receipt has been sent to Admin.\n"
            "Your payment will be checked manually."
        )
        await state.clear()

    except Exception:
        logger.exception("Payment receipt forwarding failed")
        await message.answer("Sorry! We could not send your receipt.")


# ================= CONTACT ADMIN =================

@dp.callback_query(F.data == "contact")
async def contact_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ContactForm.message)
    await callback.message.answer("☎️ Please write your message to Admin.")
    await callback.answer()


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

        await message.answer("✅ Your message has been sent to our team.")
        await state.clear()

    except Exception:
        logger.exception("Contact forwarding failed")
        await message.answer("Message could not be sent. Please try again.")


# ================= ADMIN PANEL =================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Access denied.")
        return

    youtube_status = (
        "✅ Connected" if YOUTUBE_REFRESH_TOKEN
        else "❌ Not connected"
    )

    await message.answer(
        "👨‍💼 KALID GLOBAL ADS ADMIN PANEL\n\n"
        "✅ Bot is running.\n"
        "📢 Advertisement requests are forwarded here.\n"
        "💳 Payment receipts are forwarded here.\n"
        f"▶️ YouTube: {youtube_status}\n"
        "🌍 Languages: Oromoo, Amharic, English."
    )


# ================= CONNECT YOUTUBE =================

@dp.message(Command("youtube_connect"))
async def youtube_connect(message: Message):
    global oauth_state

    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Admin only.")
        return

    try:
        flow = make_oauth_flow()
        auth_url, oauth_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )

        await message.answer(
            "🔐 CONNECT JOKESHIFT TO KALID GLOBAL ADS\n\n"
            "1. Open the Google authorization link below.\n"
            "2. Sign in with the Google account that owns JokeShift.\n"
            "3. Allow YouTube upload permission.\n"
            "4. Google will return you to the connection page.\n\n"
            f"👉 {auth_url}\n\n"
            "⚠️ Do not share this link with anyone."
        )

    except Exception as error:
        logger.exception("OAuth start failed")
        await message.answer(
            f"Could not start YouTube connection: {str(error)[:500]}"
        )


# ================= OAUTH CALLBACK =================

async def oauth_callback(request):
    global oauth_state

    returned_state = request.query.get("state")
    code = request.query.get("code")
    error = request.query.get("error")

    if error:
        return web.Response(
            text="Google authorization was cancelled or denied.",
            content_type="text/plain"
        )

    if not code or not oauth_state or returned_state != oauth_state:
        return web.Response(
            text="Invalid or expired authorization request.",
            status=400
        )

    try:
        flow = make_oauth_flow(state=oauth_state)
        flow.fetch_token(code=code)

        credentials = flow.credentials
        refresh_token = credentials.refresh_token

        oauth_state = None

        if not refresh_token:
            await bot.send_message(
                ADMIN_ID,
                "⚠️ Google did not return a refresh token.\n"
                "Please revoke this app's access in your Google Account "
                "and run /youtube_connect again."
            )
            return web.Response(
                text="Authorization received, but no refresh token was returned. "
                     "Please contact the bot admin.",
                content_type="text/plain"
            )

        await bot.send_message(
            ADMIN_ID,
            "✅ GOOGLE AUTHORIZATION SUCCESSFUL!\n\n"
            "Your YouTube refresh token is ready.\n\n"
            "For security, add it privately to Render as an environment "
            "variable named YOUTUBE_REFRESH_TOKEN.\n\n"
            "Do not send this token to anyone."
        )

        # Send the token only to the configured Telegram admin.
        await bot.send_message(
            ADMIN_ID,
            "🔐 YOUR YOUTUBE_REFRESH_TOKEN:\n\n"
            f"<code>{refresh_token}</code>\n\n"
            "Copy it into Render Environment. Do not share it.",
            parse_mode="HTML"
        )

        return web.Response(
            text="Google authorization successful. Return to Telegram "
                 "and follow the admin instructions.",
            content_type="text/plain"
        )

    except Exception:
        logger.exception("OAuth callback failed")
        return web.Response(
            text="YouTube authorization failed. Please contact the bot admin.",
            status=500
        )


async def health_check(request):
    return web.Response(text="Kalid Global Ads is running.")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/oauth2callback", oauth_callback)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info("OAuth web server running on port %s", port)
    return runner


# ================= MAIN =================

async def main():
    logger.info("Kalid Global Ads Bot is starting...")

    runner = await start_web_server()

    try:
        await dp.start_polling(
            bot,
            drop_pending_updates=True
        )
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())