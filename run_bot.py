
from dotenv import load_dotenv
import os
import telebot

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print(f"[DEBUG] TOKEN: {TOKEN}")
print(f"[DEBUG] CHAT_ID: {CHAT_ID}")

bot = telebot.TeleBot(TOKEN)
bot.send_message(CHAT_ID, "✅ Тестовое сообщение: бот работает!")
