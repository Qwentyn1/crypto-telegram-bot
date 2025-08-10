import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from binance.client import Client
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# --- Глобальні змінні ---
auto_signal_enabled = False
auto_signal_task = None
WATCHED_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']  # монети які слідкуємо

# --- Conversation states ---
CHOOSE_PRICE, CHOOSE_SIGNAL, CHOOSE_ANALYTICS = range(3)

# --- Клавіатури ---
main_keyboard = [
    ['Старт', 'Автосигнал'],
    ['Ціна', 'Сигнал'],
    ['Аналітика']
]
main_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

def get_symbols_keyboard():
    keys = [[sym] for sym in WATCHED_SYMBOLS]
    keys.append(['Всі монети'])
    return ReplyKeyboardMarkup(keys, resize_keyboard=True, one_time_keyboard=True)

# --- Обробники ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Я крипто-бот.\nОбери команду або кнопку нижче:",
        reply_markup=main_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signal_enabled, auto_signal_task

    text = update.message.text.lower()

    if text == 'старт':
        await update.message.reply_text("Бот запущений і готовий до роботи!", reply_markup=main_markup)

    elif text == 'автосигнал':
        auto_signal_enabled = not auto_signal_enabled
        if auto_signal_enabled:
            # Запускаємо таск автосигналу, якщо він не запущений
            if auto_signal_task is None or auto_signal_task.done():
                auto_signal_task = asyncio.create_task(run_auto_signal(update, context))
            await update.message.reply_text("Автосигнал увімкнено.", reply_markup=main_markup)
        else:
            await update.message.reply_text("Автосигнал вимкнено.", reply_markup=main_markup)

    elif text == 'ціна':
        await update.message.reply_text(
            "Обери монету для отримання ціни:",
            reply_markup=get_symbols_keyboard()
        )
        return CHOOSE_PRICE

    elif text == 'сигнал':
        await update.message.reply_text(
            "Обери монету для отримання сигналу:",
            reply_markup=get_symbols_keyboard()
        )
        return CHOOSE_SIGNAL

    elif text == 'аналітика':
        await update.message.reply_text(
            "Обери монету для аналітики:",
            reply_markup=get_symbols_keyboard()
        )
        return CHOOSE_ANALYTICS

    else:
        await update.message.reply_text("Невідома команда. Використовуй кнопки.", reply_markup=main_markup)
    return ConversationHandler.END

# --- Логіка для команд з вибором монети ---

async def get_price(symbol):
    try:
        if symbol == 'Всі монети':
            prices = client.get_all_tickers()
            res = '\n'.join([f"{p['symbol']}: {p['price']}" for p in prices if p['symbol'] in WATCHED_SYMBOLS])
            return res or "Дані не знайдені."
        else:
            price = client.get_symbol_ticker(symbol=symbol)
            return f"{symbol} ціна: {price['price']}"
    except Exception as e:
        return f"Помилка отримання ціни: {str(e)}"

async def get_signal(symbol):
    # Проста логіка: якщо ціна змінилась більше ніж на 1% за останні 24 год
    try:
        if symbol == 'Всі монети':
            msgs = []
            for sym in WATCHED_SYMBOLS:
                change = client.get_ticker_24hr(symbol=sym)
                price_change_percent = float(change['priceChangePercent'])
                if abs(price_change_percent) >= 1:
                    msgs.append(f"{sym}: зміна за 24г: {price_change_percent:.2f}%")
            return '\n'.join(msgs) if msgs else "Сигналів немає."
        else:
            change = client.get_ticker_24hr(symbol=symbol)
            price_change_percent = float(change['priceChangePercent'])
            if abs(price_change_percent) >= 1:
                return f"{symbol}: зміна за 24г: {price_change_percent:.2f}% - є сигнал!"
            else:
                return f"{symbol}: немає значних змін."
    except Exception as e:
        return f"Помилка отримання сигналів: {str(e)}"

async def get_analytics(symbol):
    # Приклад аналітики: поточна ціна + зміна за 1 год
    try:
        if symbol == 'Всі монети':
            msgs = []
            for sym in WATCHED_SYMBOLS:
                ticker = client.get_ticker_24hr(symbol=sym)
                price = client.get_symbol_ticker(symbol=sym)['price']
                change_1h = await get_1h_change(sym)
                msgs.append(f"{sym} ціна: {price}, зміна за 1 год: {change_1h:.2f}%")
            return '\n'.join(msgs)
        else:
            price = client.get_symbol_ticker(symbol=symbol)['price']
            change_1h = await get_1h_change(symbol)
            return f"{symbol} ціна: {price}, зміна за 1 год: {change_1h:.2f}%"
    except Exception as e:
        return f"Помилка аналітики: {str(e)}"

async def get_1h_change(symbol):
    # Використаємо Klines (свічки) для обчислення зміни за останню годину
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=2)
        if len(klines) < 2:
            return 0.0
        open_price = float(klines[0][1])
        close_price = float(klines[1][4])
        change = ((close_price - open_price) / open_price) * 100
        return change
    except:
        return 0.0

# Обробники вибору монети

async def price_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip()
    if symbol not in WATCHED_SYMBOLS and symbol != 'Всі монети':
        await update.message.reply_text("Монету не знайдено, спробуй ще.", reply_markup=get_symbols_keyboard())
        return CHOOSE_PRICE

    res = await get_price(symbol)
    await update.message.reply_text(res, reply_markup=main_markup)
    return ConversationHandler.END

async def signal_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip()
    if symbol not in WATCHED_SYMBOLS and symbol != 'Всі монети':
        await update.message.reply_text("Монету не знайдено, спробуй ще.", reply_markup=get_symbols_keyboard())
        return CHOOSE_SIGNAL

    res = await get_signal(symbol)
    await update.message.reply_text(res, reply_markup=main_markup)
    return ConversationHandler.END

async def analytics_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbol = update.message.text.strip()
    if symbol not in WATCHED_SYMBOLS and symbol != 'Всі монети':
        await update.message.reply_text("Монету не знайдено, спробуй ще.", reply_markup=get_symbols_keyboard())
        return CHOOSE_ANALYTICS

    res = await get_analytics(symbol)
    await update.message.reply_text(res, reply_markup=main_markup)
    return ConversationHandler.END

# --- Автосигнал (фонова задача) ---

async def run_auto_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_signal_enabled

    chat_id = update.effective_chat.id
    while auto_signal_enabled:
        try:
            msg = await get_signal('Всі монети')
            if msg != "Сигналів немає.":
                now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
                await context.bot.send_message(chat_id=chat_id, text=f"[Автосигнал {now}]\n{msg}")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"Помилка автосигналу: {str(e)}")

        await asyncio.sleep(60*5)  # перевіряємо кожні 5 хвилин

# --- Головна функція ---

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано.", reply_markup=main_markup)
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)],
        states={
            CHOOSE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_choice)],
            CHOOSE_SIGNAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, signal_choice)],
            CHOOSE_ANALYTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, analytics_choice)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("Бот запущений...")
    app.run_polling()

if __name__ == '__main__':
    main()
