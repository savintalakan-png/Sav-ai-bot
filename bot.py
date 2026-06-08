import os
import io
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
        [
            InlineKeyboardButton("💬 Чат с ИИ", callback_data='chat'),
            InlineKeyboardButton("🎨 Генерация картинок", callback_data='image')
        ],
        [
            InlineKeyboardButton("📊 Крипто-анализ", callback_data='crypto'),
            InlineKeyboardButton("👤 Мой аккаунт", callback_data='account')
        ]
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
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я ваш ИИ-помощник SAV AI.\n\n"
        f"{premium_text}\n"
        f"{remaining_text}\n\n"
        f"Выберите действие в меню ниже 👇",
        reply_markup=get_main_menu()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_menu()
    )

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.set_premium(user.id, days=30)
    await update.message.reply_text(
        "⭐ Premium активирован на 30 дней!\n"
        "Теперь у вас безлимитный доступ ко всем функциям."
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    data = query.data
    
    if data == 'chat':
        user_states[user.id] = 'chat'
        remaining = db.get_remaining_messages(user.id)
        await query.edit_message_text(
            f"💬 **Режим чата с ИИ**\n\n"
            f"Осталось сообщений сегодня: {remaining if remaining != float('inf') else '∞'}\n\n"
            f"Напишите мне что-нибудь, и я отвечу!\n"
            f"Для выхода нажми кнопку в меню",
            parse_mode='Markdown'
        )
    
    elif data == 'image':
        user_states[user.id] = 'image'
        await query.edit_message_text(
            "🎨 **Генерация изображений**\n\n"
            "Опиши картинку, которую хочешь создать.\n"
            "Например: закат над морем, неоновый город, кот-астронавт",
            parse_mode='Markdown'
        )    
    elif data == 'crypto':
        await query.edit_message_text("📊 Загружаю данные о криптовалютах...")
        
        result, error = get_crypto_prices()
        
        if error:
            await query.edit_message_text(f"❌ Ошибка: {error}")
        else:
            await query.edit_message_text(result, parse_mode='Markdown')
    
    elif data == 'account':
        is_premium = db.is_premium(user.id)
        remaining = db.get_remaining_messages(user.id)
        
        status = "⭐ Premium" if is_premium else "🆓 Бесплатный"
        
        await query.edit_message_text(
            f"👤 **Ваш аккаунт**\n\n"
            f"ID: {user.id}\n"
            f"Имя: {user.first_name}\n"
            f"Статус: {status}\n"
            f"Осталось сообщений: {remaining if remaining != float('inf') else '∞'}",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    message_text = update.message.text
    
    state = user_states.get(user_id)
    
    if not state:
        await update.message.reply_text(
            "Выберите действие в меню:",
            reply_markup=get_main_menu()
        )
        return
    
    if not db.can_send_message(user_id):
        await update.message.reply_text(
            "❌ Вы исчерпали лимит сообщений на сегодня.\n"
            "Приходите завтра или активируйте Premium командой /premium"
        )
        return
    
    if state == 'chat':
        await update.message.reply_text(" Думаю...")
                response, error = chat_with_groq(message_text)
        provider = "Groq (Llama-3.3-70b)"
        
        if error or not response:
            response, error = chat_with_gemini(message_text)
            provider = "Gemini"
        
        if error:
            await update.message.reply_text(f"❌ Ошибка ИИ: {error}")
        else:
            db.save_message(user_id, message_text, response, provider)
            db.increment_usage(user_id)
            
            remaining = db.get_remaining_messages(user_id)
            remaining_text = remaining if remaining != float('inf') else '∞'
            
            await update.message.reply_text(
                f"{response}\n\n"
                f"🟢 {provider} · Осталось: {remaining_text}"
            )
    
    elif state == 'image':
        await update.message.reply_text("🎨 Генерирую изображение... подожди немного ⏳")
        
        image_data, error = generate_image(message_text)
        
        if error:
            await update.message.reply_text("❌ Не удалось сгенерировать изображение. Попробуй другой запрос или повтори позже.")
        else:
            db.increment_usage(user_id)
            
            photo = io.BytesIO(image_data)
            photo.name = 'generated.jpg'
            
            remaining = db.get_remaining_messages(user_id)
            remaining_text = remaining if remaining != float('inf') else '∞'
            
            await update.message.reply_photo(
                photo=photo,
                caption=f"🎨 {message_text}\n\nОсталось сообщений: {remaining_text}"
            )
    
    else:
        await update.message.reply_text(
            "Выберите действие в меню:",
            reply_markup=get_main_menu()
        )

def main():
    if not BOT_TOKEN:        logger.error("BOT_TOKEN не найден!")
        return
    
    logger.info("Бот запускается...")
    
    # Запускаем Flask в отдельном потоке (для Render)
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("premium", premium))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
