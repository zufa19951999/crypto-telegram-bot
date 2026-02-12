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

# ==================== CẤU HÌNH ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Khởi tạo WebSocket Bybit
bybit_ws = BybitWebSocket()
bybit_ws.start(DEFAULT_COINS)

# ==================== FLASK APP ====================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Telegram Crypto Bot is running! (Bybit WebSocket)", 200

def run_flask():
    """Chạy Flask server riêng"""
    flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

# ==================== TELEGRAM BOT HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
🚀 *Crypto Price Bot - Bybit WebSocket*

Bot này lấy giá REAL-TIME từ Bybit!

*Các lệnh có sẵn:*
/xiaofa [coin] - Lấy giá realtime (VD: /xiaofa BTC)
/prices - Lấy giá tất cả coin theo dõi
/market - Xem tổng quan thị trường
/help - Xem hướng dẫn
/add [coin] - Thêm coin theo dõi
/remove [coin] - Xóa coin theo dõi
/list - Xem danh sách coin

*Ví dụ:* /xiaofa ETH
    """
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

async def xiaofa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập tên coin.\nVí dụ: /xiaofa BTC")
        return
    
    symbol = context.args[0].upper()
    await update.message.reply_text(f"🔍 Đang lấy giá *{symbol}* từ Bybit...", parse_mode=ParseMode.MARKDOWN)
    
    coin_data = bybit_ws.get_price(symbol)
    
    if coin_data:
        message = f"""
💰 *{coin_data['symbol']} / USDT*

💵 *Giá:* ${coin_data['price']:,.2f}
📊 *24h:* {format_percentage(coin_data.get('price_change_24h', 0))}

📈 *Cao 24h:* ${coin_data.get('high_24h', 0):,.2f}
📉 *Thấp 24h:* ${coin_data.get('low_24h', 0):,.2f}
💱 *KL 24h:* {format_number(coin_data.get('volume_24h', 0))}

⚡ *Bybit WebSocket*
🕐 {datetime.now().strftime('%H:%M:%S')}
        """
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ Không tìm thấy coin *{symbol}*", parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 *Hướng dẫn sử dụng:*

1️⃣ *Kiểm tra giá:*
   /xiaofa BTC
   /xiaofa ETH
   /xiaofa SOL

2️⃣ *Xem nhiều coin:*
   /prices

3️⃣ *Thêm/xóa coin:*
   /add DOGE
   /remove DOGE

4️⃣ *Danh sách theo dõi:*
   /list

5️⃣ *Thị trường:*
   /market

⚡ *Nguồn:* Bybit WebSocket Realtime
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watchlist = context.user_data.get('watchlist', DEFAULT_COINS.copy()) if context.user_data else DEFAULT_COINS.copy()
    await update.message.reply_text("🔄 Đang lấy giá từ Bybit...")
    
    coins_data = bybit_ws.get_multiple_prices(watchlist)
    
    if coins_data:
        message = "📊 *Bảng giá Bybit Realtime*\n\n"
        for symbol, data in coins_data.items():
            message += f"*{symbol}*: ${data['price']:,.2f}\n"
            if 'price_change_24h' in data:
                change = data['price_change_24h']
                message += f"  {'📈 +' if change > 0 else '📉 '}{change:.2f}%\n"
            message += "\n"
        message += f"🕐 {datetime.now().strftime('%H:%M:%S')}"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Không thể lấy giá")

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌍 Đang lấy dữ liệu thị trường...")
    
    btc_data = bybit_ws.get_price('BTC')
    eth_data = bybit_ws.get_price('ETH')
    
    if btc_data and eth_data:
        message = f"""
🌍 *Tổng quan thị trường Bybit*

🥇 *BTC:* ${btc_data['price']:,.2f}
🥈 *ETH:* ${eth_data['price']:,.2f}

⚡ *WebSocket:* {'✅ Online' if bybit_ws.running else '❌ Offline'}
🕐 {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}
        """
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Không thể lấy dữ liệu")

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Ví dụ: /add DOGE")
        return
    
    symbol = context.args[0].upper()
    
    if 'watchlist' not in context.user_data:
        context.user_data['watchlist'] = DEFAULT_COINS.copy()
    
    if symbol in context.user_data['watchlist']:
        await update.message.reply_text(f"ℹ️ *{symbol}* đã có trong danh sách", parse_mode=ParseMode.MARKDOWN)
    else:
        test_price = bybit_ws.get_price(symbol)
        if test_price:
            context.user_data['watchlist'].append(symbol)
            await update.message.reply_text(f"✅ Đã thêm *{symbol}*", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"❌ Không tìm thấy *{symbol}*", parse_mode=ParseMode.MARKDOWN)

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Ví dụ: /remove DOGE")
        return
    
    symbol = context.args[0].upper()
    
    if 'watchlist' not in context.user_data:
        context.user_data['watchlist'] = DEFAULT_COINS.copy()
    
    if symbol in context.user_data['watchlist']:
        context.user_data['watchlist'].remove(symbol)
        await update.message.reply_text(f"✅ Đã xóa *{symbol}*", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ Không tìm thấy *{symbol}*", parse_mode=ParseMode.MARKDOWN)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watchlist = context.user_data.get('watchlist', DEFAULT_COINS.copy()) if context.user_data else DEFAULT_COINS.copy()
    
    if watchlist:
        message = "📋 *Danh sách theo dõi:*\n\n"
        for i, coin in enumerate(watchlist, 1):
            price_data = bybit_ws.get_price(coin)
            if price_data:
                status = f"✅ ${price_data['price']:,.2f}"
            else:
                status = "⏳ Đang cập nhật..."
            message += f"{i}. {coin}: {status}\n"
        message += f"\n⚡ Bybit: {'✅ Online' if bybit_ws.running else '❌ Offline'}"
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("📋 Danh sách trống")

async def periodic_price_update(context: ContextTypes.DEFAULT_TYPE):
    """Cập nhật giá định kỳ"""
    logger.info("📊 Đang gửi cập nhật giá...")
    coins_data = bybit_ws.get_multiple_prices(DEFAULT_COINS)
    
    if coins_data:
        message = "🔄 *Cập nhật giá Bybit*\n\n"
        for symbol, data in coins_data.items():
            message += f"*{symbol}*: ${data['price']:,.2f}\n"
            if 'price_change_24h' in data:
                change = data['price_change_24h']
                message += f"  {'📈 +' if change > 0 else '📉 '}{change:.2f}%\n"
            message += "\n"
        message += f"🕐 {datetime.now().strftime('%H:%M %d/%m/%Y')}"
        
        try:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Lỗi gửi tin nhắn: {e}")

# ==================== TELEGRAM BOT ====================
def run_bot():
    """Chạy Telegram bot với python-telegram-bot v20+"""
    try:
        # Tạo application - KHÔNG DÙNG UPDATER
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler('start', start_command))
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('xiaofa', xiaofa_command))
        application.add_handler(CommandHandler('prices', prices_command))
        application.add_handler(CommandHandler('market', market_command))
        application.add_handler(CommandHandler('add', add_command))
        application.add_handler(CommandHandler('remove', remove_command))
        application.add_handler(CommandHandler('list', list_command))
        
        # Job queue
        job_queue = application.job_queue
        if job_queue:
            job_queue.run_repeating(
                periodic_price_update,
                interval=CHECK_INTERVAL_MINUTES * 60,
                first=10
            )
        
        logger.info("🤖 Bot Telegram đã khởi động thành công!")
        
        # Chạy bot - blocking
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Lỗi khởi động bot: {e}")
        time.sleep(5)
        run_bot()

# ==================== MAIN ====================
if __name__ == '__main__':
    # Chạy Flask trong process riêng
    flask_process = Process(target=run_flask, daemon=True)
    flask_process.start()
    logger.info("✅ Flask server đã khởi động")
    
    # Chạy bot trong process chính
    run_bot()
