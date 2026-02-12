import os
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# CoinMarketCap API
CMC_API_KEY = os.getenv('CMC_API_KEY')
CMC_BASE_URL = 'https://pro-api.coinmarketcap.com/v1/'

# Cấu hình khác
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 60))
PORT = int(os.getenv('PORT', 8080))

# Danh sách coin muốn theo dõi (mặc định)
DEFAULT_COINS = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']