from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()  # Зчитує змінні з .env

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

auto_signal_enabled = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['Старт', 'Автосигнал'],
        ['Сигнал', 'Ціна'],
        ['Аналітика']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        'Привіт! Я бот для сигналів по крипті. Обери команду або кнопку:',
        reply_markup=reply_markup
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Тут буде логіка ціни (приклад).')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signal_enabled
    text = update.message.text.lower()

    if text == 'старт':
        await update.message.reply_text('Вітаю! Бот запущений і готовий до роботи.')
    elif text == 'автосигнал':
        auto_signal_enabled = not auto_signal_enabled
        if auto_signal_enabled:
            await update.message.reply_text('Автосигнал увімкнено.')
        else:
            await update.message.reply_text('Автосигнал вимкнено.')
    elif text == 'сигнал':
        await update.message.reply_text('Тут буде логіка сигналів.')
    elif text == 'ціна':
        await update.message.reply_text('Введи команду /price для отримання ціни.')
    elif text == 'аналітика':
        await update.message.reply_text('Аналітика в розробці.')
    else:
        await update.message.reply_text('Невідома команда. Використовуй кнопки.')

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('price', price))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    print("Бот запущений...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
