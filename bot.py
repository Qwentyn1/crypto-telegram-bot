import os
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from binance.client import Client
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "SOLUSDT", "DOGEUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT"
]

CHOOSING_ACTION, CHOOSING_COIN = range(2)

auto_signal_enabled = False

def get_main_menu():
    keyboard = [['Ціна', 'Сигнал'], ['Аналітика', 'Автосигнал Вкл/Викл']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Вибери команду:",
        reply_markup=get_main_menu()
    )
    return CHOOSING_ACTION

async def choose_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    global auto_signal_enabled

    if text in ['ціна', 'сигнал', 'аналітика']:
        context.user_data['action'] = text
        coins_buttons = [[coin[:-4]] for coin in COINS]
        coins_buttons.append(['Всі монети'])
        reply_markup = ReplyKeyboardMarkup(coins_buttons, resize_keyboard=True)
        await update.message.reply_text(
            f"Обери монету для {text}:",
            reply_markup=reply_markup
        )
        return CHOOSING_COIN
    elif text == 'автосигнал вкл/викл':
        auto_signal_enabled = not auto_signal_enabled
        state = "увімкнено" if auto_signal_enabled else "вимкнено"
        await update.message.reply_text(f"Автосигнал {state}.", reply_markup=get_main_menu())
        return CHOOSING_ACTION
    else:
        await update.message.reply_text(
            "Невідома команда, будь ласка, обери зі списку.",
            reply_markup=get_main_menu()
        )
        return CHOOSING_ACTION

async def handle_coin_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin_choice = update.message.text.upper()
    action = context.user_data.get('action')

    if coin_choice == 'ВСІ МОНЕТИ':
        coins_to_check = COINS
    else:
        coin_full = coin_choice + "USDT"
        if coin_full not in COINS:
            await update.message.reply_text(
                "Невідома монета, будь ласка, обери зі списку.",
                reply_markup=get_main_menu()
            )
            return CHOOSING_COIN
        coins_to_check = [coin_full]

    if action == 'ціна':
        await show_price(update, coins_to_check)
    elif action == 'сигнал':
        await show_signal(update, coins_to_check)
    elif action == 'аналітика':
        await show_analytics(update, coins_to_check)
    else:
        await update.message.reply_text(
            "Сталася помилка. Спробуйте знову.",
            reply_markup=get_main_menu()
        )
    # Після відповіді повертаємось в головне меню
    await update.message.reply_text("Оберіть команду:", reply_markup=get_main_menu())
    return CHOOSING_ACTION

async def show_price(update: Update, coins):
    texts = []
    for coin in coins:
        try:
            ticker = client.get_symbol_ticker(symbol=coin)
            price = ticker['price']
            texts.append(f"{coin[:-4]}: {price} USD")
        except Exception:
            texts.append(f"{coin[:-4]}: помилка отримання ціни")
    await update.message.reply_text("\n".join(texts), reply_markup=ReplyKeyboardRemove())

async def show_signal(update: Update, coins):
    texts = []
    for coin in coins:
        try:
            klines = client.get_klines(symbol=coin, interval=Client.KLINE_INTERVAL_1HOUR, limit=2)
            if len(klines) < 2:
                texts.append(f"{coin[:-4]}: недостатньо даних для сигналу")
                continue
            prev_close = float(klines[-2][4])
            last_close = float(klines[-1][4])
            if last_close > prev_close:
                signal = "📈 Рекомендовано КУПИТИ"
            elif last_close < prev_close:
                signal = "📉 Рекомендовано ПРОДАТИ"
            else:
                signal = "➖ Без змін"
            texts.append(f"{coin[:-4]}: {signal} (ост. ціна: {last_close} USD)")
        except Exception:
            texts.append(f"{coin[:-4]}: помилка отримання сигналу")
    await update.message.reply_text("\n".join(texts), reply_markup=ReplyKeyboardRemove())

async def show_analytics(update: Update, coins):
    texts = []
    for coin in coins:
        try:
            ticker_24h = client.get_ticker_24hr(symbol=coin)
            price_change = float(ticker_24h.get('priceChangePercent', 0))
            high_price = float(ticker_24h.get('highPrice', 0))
            low_price = float(ticker_24h.get('lowPrice', 0))
            texts.append(
                f"{coin[:-4]}:\n"
                f"Зміна за 24г: {price_change:.2f}%\n"
                f"Макс. ціна: {high_price} USD\n"
                f"Мін. ціна: {low_price} USD"
            )
        except Exception:
            texts.append(f"{coin[:-4]}: помилка отримання аналітики")
    await update.message.reply_text("\n\n".join(texts), reply_markup=ReplyKeyboardRemove())

async def auto_signal_task(application):
    global auto_signal_enabled
    while True:
        if auto_signal_enabled:
            try:
                texts = []
                for coin in COINS:
                    klines = client.get_klines(symbol=coin, interval=Client.KLINE_INTERVAL_15MINUTE, limit=2)
                    if len(klines) < 2:
                        continue
                    prev_close = float(klines[-2][4])
                    last_close = float(klines[-1][4])
                    if last_close > prev_close:
                        signal = "📈 Рекомендовано КУПИТИ"
                    elif last_close < prev_close:
                        signal = "📉 Рекомендовано ПРОДАТИ"
                    else:
                        signal = None
                    if signal:
                        texts.append(f"{coin[:-4]}: {signal} (ост. ціна: {last_close} USD)")

                if texts:
                    msg = "[Автосигнал {}]\n\n".format(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")) + "\n".join(texts)
                    for chat_id in application.chat_data.keys():
                        await application.bot.send_message(chat_id=chat_id, text=msg)

            except Exception as e:
                print(f"Помилка автосигналу: {e}")

        await asyncio.sleep(900)  # 15 хвилин

async def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_coin)],
            CHOOSING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_coin_choice)],
        },
        fallbacks=[],
        allow_reentry=True
    )
    application.add_handler(conv_handler)

    # Запуск автосигналу як фонове завдання
    application.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_signal_task(application)), interval=900, first=10)

    print("Бот запущений...")
    await application.run_polling()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()  # Щоб уникнути RuntimeError в Windows
    import asyncio
    asyncio.run(main())
