import os
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Загружаем токены
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
BS_API_KEY = os.getenv("BS_API_KEY")

HEADERS = {"Authorization": f"Bearer {BS_API_KEY}"}

# Кланы: название -> тег
CLUBS = {
    "Котолог": "#2Q22RGG09",
    "Котолог up": "#2CJGPULJJ"
}

# Глобальная переменная для кэша состава клубов
CLUB_PLAYERS_CACHE = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"club:{tag}")]
        for name, tag in CLUBS.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Выбери клуб:",
        reply_markup=reply_markup
    )

# Получение состава клуба через API
def fetch_club_players(club_tag):
    url = f"https://api.brawlstars.com/v1/clubs/{club_tag.replace('#','%23')}/members"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        raise Exception("Не удалось получить состав клуба")
    players = r.json().get("items", [])
    # Сортируем по кубкам
    players.sort(key=lambda x: x["trophies"], reverse=True)
    return players

# Обработка нажатий кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Если пользователь выбрал клуб
    if data.startswith("club:"):
        club_tag = data.split(":", 1)[1]

        # Если кэш пустой, загружаем состав
        if club_tag not in CLUB_PLAYERS_CACHE:
            try:
                CLUB_PLAYERS_CACHE[club_tag] = fetch_club_players(club_tag)
            except:
                await query.edit_message_text("❌ Не удалось получить состав клуба")
                return

        players = CLUB_PLAYERS_CACHE[club_tag]

        # Создаем кнопки игроков: ник + кубки, 2 кнопки в ряд
        keyboard = []
        row = []
        for i, player in enumerate(players, 1):
            button = InlineKeyboardButton(f"{player['name']} ({player['trophies']} 🏆)", callback_data=f"player:{player['tag']}")
            row.append(button)
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Выбран клуб. Выберите игрока:", reply_markup=reply_markup)

    # Если пользователь выбрал игрока
    elif data.startswith("player:"):
        tag = data.split(":", 1)[1].replace("#","%23")
        url = f"https://api.brawlstars.com/v1/players/{tag}"
        try:
            r = requests.get(url, headers=HEADERS)
            if r.status_code != 200:
                raise Exception()
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
            await query.edit_message_text("❌ Игрок не найден или ошибка API")

# Основная функция
def main():
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Бот запущен 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()