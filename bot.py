from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

TELEGRAM_BOT_TOKEN = '8110685774:AAGtRE2qYsid1MIA3SD0K_8itCLe1QEMHuo'
BINANCE_API_KEY = 'VpqwF6TywazIQKwwFBqNb3K8AOblqp9DGT6kQAuTHiAjRiJ7o9R0iqHoIlqVUNM3'
BINANCE_API_SECRET = 'V9ZRbX44Dr66UkEWwqJNG9afuhDknpAGeatnekaNbhwIyj1KIouFZGayyImfxves'

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
    # Тут можна додати реальну логіку отримання ціни через API Binance
    await update.message.reply_text('Тут буде логіка ціни (приклад).')

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Логіка видачі сигналу (поки заглушка)
    await update.message.reply_text('Тут буде логіка сигналів.')

async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Логіка аналітики (поки заглушка)
    await update.message.reply_text('Аналітика в розробці.')

async def auto_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signal_enabled
    auto_signal_enabled = not auto_signal_enabled
    if auto_signal_enabled:
        await update.message.reply_text('Автосигнал увімкнено.')
    else:
        await update.message.reply_text('Автосигнал вимкнено.')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if text == 'старт':
        await start(update, context)
    elif text == 'автосигнал':
        await auto_signal(update, context)
    elif text == 'сигнал':
        await signal(update, context)
    elif text == 'ціна':
        await price(update, context)
    elif text == 'аналітика':
        await analytics(update, context)
    else:
        await update.message.reply_text('Невідома команда. Використовуй кнопки нижче.')

async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('price', price))
    app.add_handler(CommandHandler('signal', signal))
    app.add_handler(CommandHandler('analytics', analytics))
    app.add_handler(CommandHandler('autosignal', auto_signal))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    print("Бот запущений...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
