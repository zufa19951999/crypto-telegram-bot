import logging
from datetime import datetime
from flask import Flask
import time
from multiprocessing import Process

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CHECK_INTERVAL_MINUTES, PORT, DEFAULT_COINS
from utils_bybit import BybitWebSocket, format_price, format_percentage, format_number

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

bybit_ws = BybitWebSocket()
bybit_ws.start(DEFAULT_COINS)

flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Telegram Crypto Bot is running! (Bybit WebSocket)", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Crypto Bot is running! Use /xiaofa BTC", parse_mode=ParseMode.MARKDOWN)

async def xiaofa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Example: /xiaofa BTC")
        return
    symbol = context.args[0].upper()
    coin_data = bybit_ws.get_price(symbol)
    if coin_data:
        await update.message.reply_text(f"💰 {symbol}: ${coin_data['price']:,.2f}")
    else:
        await update.message.reply_text(f"❌ Cannot find {symbol}")

def run_bot():
    try:
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler('start', start_command))
        app.add_handler(CommandHandler('xiaofa', xiaofa_command))
        logger.info("🤖 Bot started successfully!")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        time.sleep(5)
        run_bot()

if __name__ == '__main__':
    Process(target=run_flask, daemon=True).start()
    logger.info("✅ Flask started")
    run_bot()
