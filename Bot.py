import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from database import db
from ai_services import chat_with_groq, chat_with_gemini, generate_image, get_crypto_prices

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
user_states = {}

app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💬 Чат с ИИ", callback_data='chat'),
         InlineKeyboardButton("🎨 Генерация картинок", callback_data='image')],
        [InlineKeyboardButton("📊 Крипто-анализ", callback_data='crypto'),
         InlineKeyboardButton("👤 Мой аккаунт", callback_data='account')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    is_premium = db.is_premium(user.id)
    remaining = db.get_remaining_messages(user.id)
    premium_text = "⭐ Premium: безлимитный доступ" if is_premium else "🆓 Бесплатный план: 10 сообщений в день"
    remaining_text = f"Осталось сообщений сегодня: {remaining if remaining != float('inf') else '∞'}"
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\nЯ ваш ИИ-помощник SAV AI.\n\n{premium_text}\n{remaining_text}\n\nВыберите действие в меню ниже 👇",
        reply_markup=get_main_menu()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply
