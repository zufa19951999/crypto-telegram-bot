import json
import time
from datetime import datetime
from threading import Thread, Lock
from websocket import WebSocketApp
import requests

class BybitWebSocket:
    def __init__(self):
        self.prices = {}
        self.symbols = []
        self.ws = None
        self.running = False
        self.lock = Lock()
        self.reconnect_count = 0
        self.max_reconnect = 5
        self.base_url = "wss://stream.bybit.com/v5/public/spot"
        
    def start(self, symbols=['BTC', 'ETH', 'BNB', 'SOL', 'XRP']):
        """Khởi động WebSocket Bybit"""
        self.symbols = [f"{s.upper()}USDT" for s in symbols]
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if 'topic' in data and 'tickers' in data['topic']:
                    if 'data' in data:
                        ticker = data['data']
                        symbol = ticker['symbol'].replace('USDT', '')
                        with self.lock:
                            self.prices[symbol] = {
                                'symbol': symbol,
                                'price': float(ticker['lastPrice']),
                                'price_change_24h': float(ticker.get('price24hPcnt', 0)) * 100,
                                'high_24h': float(ticker.get('highPrice24h', 0)),
                                'low_24h': float(ticker.get('lowPrice24h', 0)),
                                'volume_24h': float(ticker.get('volume24h', 0)),
                                'bid': float(ticker.get('bid1Price', 0)),
                                'ask': float(ticker.get('ask1Price', 0)),
                                'time': datetime.now()
                            }
            except Exception as e:
                print(f"Error: {e}")
        
        def on_error(ws, error):
            print(f"❌ Bybit error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print("🔌 Bybit closed")
            self.running = False
            
        def on_open(ws):
            print("✅ Bybit connected!")
            self.running = True
            for symbol in self.symbols:
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [f"tickers.{symbol}"]
                }
                ws.send(json.dumps(subscribe_msg))
                time.sleep(0.1)
        
        def run_ws():
            self.ws = WebSocketApp(
                self.base_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            self.ws.run_forever()
        
        thread = Thread(target=run_ws)
        thread.daemon = True
        thread.start()
        time.sleep(2)
    
    def get_price(self, symbol):
        """Lấy giá realtime"""
        symbol = symbol.upper()
        with self.lock:
            if symbol in self.prices:
                return self.prices[symbol].copy()
        return self.get_price_rest(symbol)
    
    def get_price_rest(self, symbol):
        """Fallback REST API"""
        try:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol.upper()}USDT"
            response = requests.get(url, timeout=3)
            data = response.json()
            if data['retCode'] == 0 and data['result']['list']:
                ticker = data['result']['list'][0]
                return {
                    'symbol': symbol.upper(),
                    'price': float(ticker['lastPrice']),
                    'price_change_24h': float(ticker['price24hPcnt']) * 100,
                    'high_24h': float(ticker['highPrice24h']),
                    'low_24h': float(ticker['lowPrice24h']),
                    'volume_24h': float(ticker['volume24h']),
                    'time': datetime.now()
                }
        except:
            pass
        return None
    
    def get_multiple_prices(self, symbols):
        """Lấy giá nhiều coin"""
        results = {}
        for symbol in symbols:
            price_data = self.get_price(symbol)
            if price_data:
                results[symbol] = price_data
        return results

# ==================== FORMAT FUNCTIONS ====================

def format_price(price):
    if price is None: return "N/A"
    try:
        price = float(price)
        if price < 0.01: return f"${price:.8f}"
        elif price < 1: return f"${price:.4f}"
        elif price < 1000: return f"${price:.2f}"
        else: return f"${price:,.0f}"
    except: return "N/A"

def format_percentage(value):
    if value is None: return "N/A"
    try:
        value = float(value)
        if value > 0: return f"📈 +{value:.2f}%"
        elif value < 0: return f"📉 {value:.2f}%"
        else: return f"➡️ {value:.2f}%"
    except: return "N/A"

def format_number(num):
    if num is None: return "N/A"
    try:
        num = float(num)
        if num >= 1e12: return f"${num/1e12:.2f}T"
        elif num >= 1e9: return f"${num/1e9:.2f}B"
        elif num >= 1e6: return f"${num/1e6:.2f}M"
        elif num >= 1e3: return f"${num/1e3:.2f}K"
        else: return f"${num:.2f}"
    except: return "N/A"