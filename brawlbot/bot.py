import os
import requests
import asyncio
from dotenv import load_dotenv
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# Загружаем токены
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
BS_API_KEY = os.getenv("BS_API_KEY")

HEADERS = {"Authorization": f"Bearer {BS_API_KEY}"}

CLUBS = {
    "Котолог": "#2Q22RGG09",
    "Котолог up": "#2CJGPULJJ"
}

CLUB_PLAYERS_CACHE = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"club:{tag}")]
        for name, tag in CLUBS.items()
    ]
    await update.message.reply_text(
        "Привет! Выбери клуб:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# API клубов
def fetch_club_players(club_tag):
    url = f"https://api.brawlstars.com/v1/clubs/{club_tag.replace('#','%23')}/members"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    players = r.json().get("items", [])
    players.sort(key=lambda x: x["trophies"], reverse=True)
    return players

# Кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("club:"):
        club_tag = data.split(":", 1)[1]

        if club_tag not in CLUB_PLAYERS_CACHE:
            try:
                CLUB_PLAYERS_CACHE[club_tag] = fetch_club_players(club_tag)
            except Exception as e:
                await query.edit_message_text("❌ Ошибка загрузки клуба")
                return

        players = CLUB_PLAYERS_CACHE[club_tag]

        keyboard, row = [], []
        for i, p in enumerate(players, 1):
            row.append(
                InlineKeyboardButton(
                    f"{p['name']} ({p['trophies']} 🏆)",
                    callback_data=f"player:{p['tag']}"
                )
            )
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        await query.edit_message_text(
            "Выбери игрока:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("player:"):
        tag = data.split(":", 1)[1].replace("#", "%23")
        url = f"https://api.brawlstars.com/v1/players/{tag}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            p = r.json()
            text = (
                f"🎮 {p['name']}\n"
                f"🏆 Кубки: {p['trophies']}\n"
                f"👑 Макс: {p['highestTrophies']}\n"
                f"🔥 Уровень: {p['expLevel']}\n"
                f"🤺 Победы 3v3: {p['3vs3Victories']}"
            )
            await query.edit_message_text(text)
        except:
            await query.edit_message_text("❌ Ошибка API")

# ---- HTTP для Leapcell ----
async def healthcheck(request):
    return web.Response(text="OK")

async def start_web():
    app = web.Application()
    app.router.add_get("/", healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner,
        "0.0.0.0",
        int(os.environ.get("PORT", 8000))
    )
    await site.start()

async def main():
    await start_web()

    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    print("Бот запущен 🚀")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())