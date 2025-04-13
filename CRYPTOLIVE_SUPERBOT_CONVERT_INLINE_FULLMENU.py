
import os
import json
import requests
import telebot
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from deep_translator import GoogleTranslator

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(TOKEN)


# === Меню ===
main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("💱 Конвертация", "📊 Портфель")
main_menu.row("📰 Новости сейчас")
main_menu.row("🔔 Алерты", "💎 Premium")
main_menu.row("📈 Курс сейчас")

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Добро пожаловать в CRYPTOLIVE SUPERTBOT! Выберите действие:", reply_markup=main_menu)

@bot.message_handler(commands=["convert"])
def convert(message):
    bot.reply_to(message, "Введите в формате: BTC USDT 0.01")

@bot.message_handler(commands=["portfolio"])
def portfolio(message):
    bot.reply_to(message, "Ваш криптопортфель пока пуст.")

@bot.message_handler(commands=["alert"])

def send_price_update():
    prices = get_prices()
    if not prices: return

    usd_btc = "{:,}".format(prices['BTC']['usd']).replace(",", ".")
    rub_btc = "{:,}".format(prices['BTC']['rub']).replace(",", ".")
    usd_eth = "{:,}".format(prices['ETH']['usd']).replace(",", ".")
    rub_eth = "{:,}".format(prices['ETH']['rub']).replace(",", ".")
    usd_ton = "{:,}".format(prices['TON']['usd']).replace(",", ".")
    rub_ton = "{:,}".format(prices['TON']['rub']).replace(",", ".")
    usd_sol = "{:,}".format(prices['SOL']['usd']).replace(",", ".")
    rub_sol = "{:,}".format(prices['SOL']['rub']).replace(",", ".")

    message = "Курсы:\n"
    message += "BTC: $" + usd_btc + " / ₽" + rub_btc + "\n"
    message += "ETH: $" + usd_eth + " / ₽" + rub_eth + "\n"
    message += "TON: $" + usd_ton + " / ₽" + rub_ton + "\n"
    message += "SOL: $" + usd_sol + " / ₽" + rub_sol

    try:
        bot.send_message(CHAT_ID, message)
    except Exception as e:
        print(f"[ERROR send_price_update]: {e}")

def alert(message):
    bot.reply_to(message, "Алерты уже активны: BTC/ETH/SOL/TON")

@bot.message_handler(commands=["premium"])
def premium(message):
    bot.reply_to(message, "CRYPTOLIVE Premium скоро будет доступен по NFT и подписке.")

@bot.message_handler(commands=["alertslist"])
def alerts_list(message):
    if os.path.exists("alerts.json"):
        with open("alerts.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        lines = ["🔔 Активные алерты:"]
        for symbol, info in data.items():
            lines.append(f"{symbol} → каждые {info['step']} USD (последняя: ${info['last_price']}, {info['updated_at']})")
        bot.reply_to(message, "\n".join(lines))
    else:
        bot.reply_to(message, "Алерты ещё не активны.")

@bot.message_handler(commands=["news"])
def manual_news(message):
    send_combined_news()


from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

convert_state = {}

@bot.message_handler(commands=["convert"])
def start_convert_menu(message):
    user_id = message.chat.id
    convert_state[user_id] = {}
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("BTC", callback_data="from_BTC"),
        InlineKeyboardButton("ETH", callback_data="from_ETH")
    )
    markup.row(
        InlineKeyboardButton("TON", callback_data="from_TON"),
        InlineKeyboardButton("SOL", callback_data="from_SOL")
    )
    bot.send_message(user_id, "💱 Выбери валюту, из которой конвертировать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("from_"))
def handle_from_selection(call):
    user_id = call.message.chat.id
    from_coin = call.data.split("_")[1].lower()
    convert_state[user_id]["from"] = from_coin
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("0.01", callback_data="amount_0.01"),
        InlineKeyboardButton("0.1", callback_data="amount_0.1"),
        InlineKeyboardButton("0.5", callback_data="amount_0.5")
    )
    markup.row(
        InlineKeyboardButton("1", callback_data="amount_1"),
        InlineKeyboardButton("5", callback_data="amount_5"),
        InlineKeyboardButton("10", callback_data="amount_10")
    )
    bot.send_message(user_id, f"🔢 Сколько {from_coin.upper()} хочешь конвертировать?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("amount_"))
def handle_amount_selection(call):
    user_id = call.message.chat.id
    amount = float(call.data.split("_")[1])
    convert_state[user_id]["amount"] = amount
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("USD", callback_data="to_usd"),
        InlineKeyboardButton("RUB", callback_data="to_rub"),
        InlineKeyboardButton("USDT", callback_data="to_usdt")
    )
    bot.send_message(user_id, "💰 В какую валюту перевести?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("to_"))
def handle_to_selection(call):
    user_id = call.message.chat.id
    to_coin = call.data.split("_")[1].lower()
    from_coin = convert_state[user_id]["from"]
    amount = convert_state[user_id]["amount"]

    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={from_coin}&vs_currencies={to_coin}"
        response = requests.get(url, timeout=5).json()
        rate = response[from_coin][to_coin]
        result = round(amount * rate, 4)
        bot.send_message(user_id, f"{amount} {from_coin.upper()} = {result} {to_coin.upper()}")
    except Exception as e:
        print(f"[ERROR convert fullmenu]: {e}")
        bot.send_message(user_id, "⚠️ Не удалось получить курс.")

@bot.message_handler(func=lambda msg: True)
def handle_buttons(message):
    if message.text == "💱 Конвертация":
        convert(message)
    elif message.text == "📊 Портфель":
        portfolio(message)
    elif message.text == "🔔 Алерты":
        alerts_list(message)
    elif message.text == "💎 Premium":
        premium(message)
    elif message.text == "📈 Курс сейчас":
        send_price_update()
    elif message.text == "📰 Новости сейчас":
        send_combined_news()
        send_price_update()

# === Курсы ===

def get_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "bitcoin,ethereum,the-open-network,solana", "vs_currencies": "usd"}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return {
            "BTC": data.get("bitcoin", {}).get("usd", 0),
            "ETH": data.get("ethereum", {}).get("usd", 0),
            "TON": data.get("the-open-network", {}).get("usd", 0),
            "SOL": data.get("solana", {}).get("usd", 0)
        }
    except Exception as e:
        print("[ERROR get_prices]: {e}")
        return {}

def load_alerts():
    if os.path.exists("alerts.json"):
        with open("alerts.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_alerts(data):
    with open("alerts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_alerts():
    prices = get_prices()
    alerts = load_alerts()
    updated = False

    for symbol, step in alert_config.items():
        current = prices.get(symbol, 0)
        if current == 0:
            continue

        last_entry = alerts.get(symbol)
        if last_entry is None:
            alerts[symbol] = {
                "last_price": current,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "step": step
            }
            updated = True
            continue

        diff = abs(current - last_entry["last_price"])
        if diff >= step:
            direction = "вырос" if current > last_entry["last_price"] else "упал"
            msg = "{symbol} {direction} на {int(diff)} USD\nТекущий курс: ${current}"
            try:
                bot.send_message(CHAT_ID, msg)
            except Exception as e:
                print("[ERROR send_alert]: {e}")
            alerts[symbol]["last_price"] = current
            alerts[symbol]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            updated = True

    if updated:
        save_alerts(alerts)

# === Новости с переводом ===

def fetch_rss_titles(url, limit=2):
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.content, features="xml")
        items = soup.find_all("item")[:limit]
        news = []
        for item in items:
            title = item.title.text
            link = item.link.text
            news.append((title, link))
        return news
    except Exception as e:
        print("[ERROR fetch_rss]: {e}")
        return []


def translate_text(text):
    try:
        if hasattr(text, "text"):
            text = str(text.text)
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        print("[ERROR translate]: {e}")
        return str(text)


def get_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "bitcoin,ethereum,the-open-network,solana", "vs_currencies": "usd,rub"}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return {
            "BTC": {"usd": data.get("bitcoin", {}).get("usd", 0), "rub": data.get("bitcoin", {}).get("rub", 0)},
            "ETH": {"usd": data.get("ethereum", {}).get("usd", 0), "rub": data.get("ethereum", {}).get("rub", 0)},
            "TON": {"usd": data.get("the-open-network", {}).get("usd", 0), "rub": data.get("the-open-network", {}).get("rub", 0)},
            "SOL": {"usd": data.get("solana", {}).get("usd", 0), "rub": data.get("solana", {}).get("rub", 0)},
        }
    except Exception as e:
        print("[ERROR get_prices]: {e}")
        return {}


def send_combined_news():
    sources = {
        "Reddit r/Crypto": "https://www.reddit.com/r/CryptoCurrency/top/.rss?t=hour",
        "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "Cointelegraph": "https://cointelegraph.com/rss",
        "Decrypt": "https://decrypt.co/feed"
    }

    message_lines = ["🌐 Новости криптовалют (перевод):"]

    for name, url in sources.items():
        entries = fetch_rss_titles(url)
        if entries:
            message_lines.append("\n🔹 " + name + ":")
            for title, link in entries:
                translated = translate_text(title)
                message_lines.append("• " + translated + "\n" + link)

    full_message = "\n\n".join(message_lines)
    try:
        bot.send_message(CHAT_ID, full_message)
    except Exception as e:
        print(f"[ERROR send_combined_news]: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(send_price_update, 'interval', minutes=1)
scheduler.add_job(check_alerts, 'interval', minutes=1)
scheduler.add_job(send_combined_news, 'interval', minutes=30)
scheduler.start()

print("🔥 SUPERTBOT ULTIMATE запущен.")
bot.infinity_polling()