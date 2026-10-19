import ccxt
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8726580360:AAG7RCtO2xKvkzIjb--YNGnkuMj-qohnfWw"
TELEGRAM_CHAT_ID   = "1314669361"

# Gerçek Binance API Bilgilerin
API_KEY    = "yfjc6DFN5Sa0jqjIElpZgUEEq1O0lXNJo7nVgjKHdGGm9LcZW4zxm0OJ9iUs5rsv"
SECRET_KEY = "ZgZSFfuU7YAjtvj6r02oo4bPDsIC1BJwM87jy43r1djlk6NkVOc6iSbNQjXwd3IJ"

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'},
    'timeout': 15000
})

# Sandbox kapalı, doğrudan gerçek hesap (Mainnet)
exchange.set_sandbox_mode(False)

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'AVAX/USDT', 'DOGE/USDT']
TIMEFRAME = '15m'
TRADE_BUDGET_USDT = 15.0 # İşlem başına 15 USDT

last_update_id = 0

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Telegram Hatası]: {e}")

def get_user_portfolio():
    try:
        balance = exchange.fetch_balance()
        free_assets = balance.get('free', {})
        locked_assets = balance.get('locked', {})
        
        portfolio_text = "📦 <b>Anlık Gerçek Spot Cüzdanınız:</b>\n\n"
        has_asset = False

        for asset, amount in free_assets.items():
            if amount > 0.00001:  # Sıfıra yakın küçük kalıntıları elemek için
                has_asset = True
                locked = locked_assets.get(asset, 0.0)
                portfolio_text += f"🔹 <b>{asset}:</b> {amount:.4f} (Kullanılabilir)"
                if locked > 0:
                    portfolio_text += f" | {locked:.4f} (Kilitli)"
                portfolio_text += "\n"
        
        if not has_asset:
            portfolio_text += "Cüzdanınızda şu an sıfırdan büyük varlık bulunmuyor."
        return portfolio_text
    except Exception as e:
        print(f"[Cüzdan Hatası]: {e}")
        return "⚠️ Cüzdan bilgisi alınamadı. (API izinlerini veya bakiyeyi kontrol et)"

def check_telegram_commands():
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=1"
    try:
        response = requests.get(url, timeout=5).json()
        if response.get("ok") and response.get("result"):
            for result in response["result"]:
                last_update_id = result["update_id"]
                message = result.get("message", {})
                text = message.get("text", "").strip().lower()
                chat_id = str(message.get("chat", {}).get("id", ""))

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Telegram Komutu Alındı: '{text}'")

                if chat_id == TELEGRAM_CHAT_ID:
                    if "/bakiye" in text:
                        try:
                            balance = exchange.fetch_balance()
                            usdt_balance = balance['free'].get('USDT', 0.0)
                            send_telegram_message(f"💰 <b>Canlı USDT Bakiyeniz:</b> {usdt_balance:.2f} USDT")
                        except Exception as e:
                            send_telegram_message(f"⚠️ Bakiye alınamadı: {e}")
                    elif "/cuzdan" in text or "/cüzdan" in text:
                        portfolio = get_user_portfolio()
                        send_telegram_message(portfolio)
                    elif "/durum" in text:
                        send_telegram_message("🤖 <b>Bot Durumu:</b> Gerçek Canlı Mod & WARP Tüneli Aktif 🚀")
    except Exception as e:
        print(f"[Komut Dinleme Hatası]: {e}")

def execute_buy(symbol, close_price):
    try:
        balance = exchange.fetch_balance()
        free_usdt = balance['free'].get('USDT', 0.0)

        if free_usdt < TRADE_BUDGET_USDT:
            msg = f"⚠️ [{symbol}] ALIM YAPILAMADI! Yetersiz USDT: {free_usdt:.2f}"
            print(msg)
            send_telegram_message(msg)
            return False

        amount = TRADE_BUDGET_USDT / close_price
        order = exchange.create_market_buy_order(symbol, amount)
        
        msg = f"🟢 <b>CANLI ALIM YAPILDI!</b>\n\n🔹 <b>Coin:</b> {symbol}\n💵 <b>Tutar:</b> {TRADE_BUDGET_USDT} USDT\n💰 <b>Fiyat:</b> {close_price}\n🆔 <b>Emir ID:</b> {order['id']}"
        print(msg)
        send_telegram_message(msg)
        return True
    except Exception as e:
        msg = f"❌ <b>ALIM HATASI ({symbol}):</b> {str(e)}"
        print(msg)
        send_telegram_message(msg)
        return False

def analyze_market(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        curr = df.iloc[-2]
        close_price = curr['close']

        print(f"-> {symbol} | Fiyat: {close_price} | Piyasa Taranıyor...")
        return f"{symbol} tarandı."
    except Exception as e:
        err_msg = f"[{symbol} Hatası]: {e}"
        print(err_msg)
        return err_msg

if __name__ == '__main__':
    print("🚀 BİNANCE GERÇEK HESAP BOTU BAŞLATILDI (WARP AKTİF)...")
    send_telegram_message("🚀 <b>GERÇEK HESAP BOTU AKTİF!</b> /cuzdan veya /bakiye yazarak anlık cüzdanını kontrol edebilirsin.")

    last_checked_minute = -1

    while True:
        check_telegram_commands()
        now = datetime.now()
        current_minute = now.minute

        if current_minute in [0, 15, 30, 45] and current_minute != last_checked_minute:
            print(f"\n[{now.strftime('%H:%M:%S')}] Yeni 15m mum. Piyasalar taranıyor...")
            for symbol in SYMBOLS:
                analyze_market(symbol)
                time.sleep(1)
            last_checked_minute = current_minute

        if current_minute not in [0, 15, 30, 45]:
            last_checked_minute = -1

        time.sleep(3)