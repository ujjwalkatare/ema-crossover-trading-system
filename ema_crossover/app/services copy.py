import os
import sys
import requests
import pandas as pd
import time
import copy
import pytz
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from django.conf import settings

# --- CONFIGURATION (Move secrets to settings.py or environment variables later) ---
TELEGRAM_TOKEN = "8475210830:AAFE5ed13AYPh63qWG1-6YTMB81-mSqFSZw" # Better to load from settings
CHAT_ID = "1319951741" # Better to load from settings
EMA_PERIODS = [5, 20]

TIMEFRAME_OPTIONS = {
    "1 Minute":   {"api": "1m", "seconds": 60, "period": "1d"},
    "5 Minutes":  {"api": "5m", "seconds": 300, "period": "5d"},
    "15 Minutes": {"api": "15m", "seconds": 900, "period": "10d"},
    "30 Minutes": {"api": "30m", "seconds": 1800, "period": "20d"},
    "1 Hour":     {"api": "60m", "seconds": 3600, "period": "1mo"},
    "4 Hour":     {"api": "4h", "seconds": 14400, "period": "3mo"},
}

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)
last_crossover_signals = {} # Note: This will reset if the script restarts. For persistence, use a database or cache.

# --- DATA STRUCTURE ---
class StockData:
    def __init__(self, ticker, data, ema_data, trend, crossover, is_new_crossover, current_close, latest_ema5, latest_ema20):
        self.ticker, self.data, self.ema_data, self.trend, self.crossover = ticker, data, ema_data, trend, crossover
        self.is_new_crossover, self.current_close, self.latest_ema5, self.latest_ema20 = is_new_crossover, current_close, latest_ema5, latest_ema20

# --- HELPER & CALCULATION FUNCTIONS ---

# Replace your old function with this updated version
def load_tickers_from_csv(file_path='stock_names.csv'):
    """Loads all available stock tickers from the CSV file."""
    try:
        # --- THIS IS THE FIX ---
        # Build the full, absolute path to the CSV file inside your 'app' folder
        full_path = os.path.join(settings.BASE_DIR, 'app', file_path)
        # --- END OF FIX ---
        
        df = pd.read_csv(full_path) # Use the new full_path variable
        tickers = [f"{symbol.strip().upper()}.NS" for symbol in df['SYMBOL'].dropna().tolist()]
        print(f"✅ Successfully loaded {len(tickers)} stock symbols from '{full_path}'.")
        return tickers
    except Exception as e:
        print(f"❌ ERROR loading tickers: {e}")
        return []

def calculate_ema(data, period):
    if not data or len(data) < period: return []
    closes = [d['close'] for d in data]
    k = 2 / (period + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(closes[i] * k + ema[i-1] * (1 - k))
    return ema

def determine_trend(ema5, ema20, current_close):
    latest_ema5, latest_ema20 = (ema5[-1] if ema5 else 0), (ema20[-1] if ema20 else 0)
    if latest_ema5 > latest_ema20 and current_close > latest_ema5: return "STRONG BULLISH 📈"
    elif latest_ema5 > latest_ema20: return "BULLISH 📈"
    elif latest_ema5 < latest_ema20 and current_close < latest_ema5: return "STRONG BEARISH 📉"
    elif latest_ema5 < latest_ema20: return "BEARISH 📉"
    else: return "NEUTRAL ↔️"

def detect_crossover(ema5, ema20):
    if len(ema5) < 2 or len(ema20) < 2: return {"signal": "NO CROSSOVER", "is_new": False}
    current_ema5, current_ema20 = ema5[-1], ema20[-1]
    prev_ema5, prev_ema20 = ema5[-2], ema20[-2]
    if prev_ema5 <= prev_ema20 and current_ema5 > current_ema20: return {"signal": "BULLISH CROSSOVER 🔼", "is_new": True}
    if prev_ema5 >= prev_ema20 and current_ema5 < current_ema20: return {"signal": "BEARISH CROSSOVER 🔽", "is_new": True}
    return {"signal": "NO CROSSOVER", "is_new": False}


# --- MESSAGE FORMATTING & SENDING ---

def format_summary_message(stock, timeframe_label):
    current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")
    timeframe_title = timeframe_label.replace(" ", "")
    message = f"📊 <b>{stock.ticker} - {timeframe_title} Summary</b>\n\n"
    message += f"🕐 <b>Time:</b> {current_time}\n"
    message += f"📈 <b>Trend:</b> {stock.trend}\n"
    message += f"🔔 <b>Signal:</b> {stock.crossover}\n\n"
    message += "<b>KEY LEVELS:</b>\n"
    message += f"💰 <b>Current Price:</b> {stock.current_close:.2f}\n"
    message += f"📉 <b>EMA5:</b> {stock.latest_ema5:.2f}\n"
    message += f"📊 <b>EMA20:</b> {stock.latest_ema20:.2f}\n"
    message += f"🔍 <b>EMA Spread (5-20):</b> {(stock.latest_ema5 - stock.latest_ema20):.2f}\n"
    return message

def format_alert_message(stock, timeframe_label):
    current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%H:%M:%S")
    message = f"🚨 <b>{stock.ticker} - {timeframe_label} ALERT!</b> 🚨\n\n"
    message += f"🕐 <b>Time:</b> {current_time}\n"
    message += f"🔔 <b>Signal:</b> {stock.crossover}\n\n"
    message += "<b>CURRENT LEVELS:</b>\n"
    message += f"💰 <b>Price:</b> {stock.current_close:.2f}\n"
    message += f"📉 <b>EMA5:</b> {stock.latest_ema5:.2f}\n"
    message += f"📊 <b>EMA20:</b> {stock.latest_ema20:.2f}\n"
    message += "📈 <b>Potential Uptrend Starting!</b>\n" if "BULLISH" in stock.crossover else "📉 <b>Potential Downtrend Starting!</b>\n"
    return message

async def send_telegram_message(message, is_alert=False):
    try:
        await bot.send_message(
            chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML,
            disable_notification=not is_alert
        )
        print(f"✅ {'ALERT' if is_alert else 'Summary'} sent to Telegram.")
        return True
    except Exception as e:
        print(f"❌ Failed to send message to Telegram: {e}")
        return False

# --- CORE DATA FETCHING & PROCESSING ---

def fetch_stock_data(tickers, timeframe_config):
    results = []
    timeframe_api = timeframe_config["api"]
    timeframe_period = timeframe_config["period"]
    timeframe_label = [k for k, v in TIMEFRAME_OPTIONS.items() if v['api'] == timeframe_api][0]

    for ticker in tickers:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={timeframe_period}&interval={timeframe_api}"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            response.raise_for_status()
            result = response.json()

            if not result.get('chart') or not result['chart'].get('result'): continue
            quotes = result['chart']['result'][0]
            timestamps = quotes.get('timestamp', [])
            closes = quotes['indicators']['quote'][0].get('close', [])
            
            if not timestamps or not closes or len(closes) < max(EMA_PERIODS):
                print(f"Not enough data for {ticker} at {timeframe_label}. Skipping.")
                continue

            data = [{'close': cl} for cl in closes if cl is not None]
            if not data: continue

            ema_data = {p: calculate_ema(data, p) for p in EMA_PERIODS}
            if not ema_data[5] or not ema_data[20]: continue
            
            current_close = data[-1]['close']
            trend = determine_trend(ema_data[5], ema_data[20], current_close)
            crossover_result = detect_crossover(ema_data[5], ema_data[20])

            print(f"--- {datetime.now().strftime('%H:%M:%S')} - {ticker} ({timeframe_label}) ---")
            print(f"TREND: {trend} | SIGNAL: {crossover_result['signal']}")

            results.append(StockData(
                ticker, data, ema_data, trend, crossover_result['signal'],
                crossover_result['is_new'], current_close, ema_data[5][-1], ema_data[20][-1]
            ))
        except Exception as e:
            print(f"Fetch Error for {ticker}: {e}")
    return results

async def check_for_alerts(stock_data_list, timeframe_config):
    timeframe_label = [k for k, v in TIMEFRAME_OPTIONS.items() if v['api'] == timeframe_config['api']][0]
    for stock in stock_data_list:
        if stock.is_new_crossover:
            last_signal_key = f"{stock.ticker}-{timeframe_config['api']}"
            last_signal = last_crossover_signals.get(last_signal_key)
            
            # Check if it's a new, different signal
            is_new_alert = (last_signal is None or last_signal['type'] != stock.crossover)
            
            if is_new_alert:
                print(f"🚨 NEW CROSSOVER DETECTED for {stock.ticker} on {timeframe_label}: {stock.crossover}")
                alert_message = format_alert_message(stock, timeframe_label)
                if await send_telegram_message(alert_message, True):
                    last_crossover_signals[last_signal_key] = {'type': stock.crossover}

async def send_summary_updates(stock_data_list, timeframe_config):
    timeframe_label = [k for k, v in TIMEFRAME_OPTIONS.items() if v['api'] == timeframe_config['api']][0]
    for stock in stock_data_list:
        summary_message = format_summary_message(stock, timeframe_label)
        await send_telegram_message(summary_message, False)


# --- MAIN BACKGROUND LOOP ---
async def main_bot_loop(tickers, timeframe_label):
    """The main loop that will run continuously in the background."""
    if not tickers:
        print("No tickers provided. Exiting bot loop.")
        return

    print(f"--- Starting Bot ---")
    print(f"Monitoring Tickers: {tickers}")
    print(f"Timeframe: {timeframe_label}")
    
    timeframe_config = TIMEFRAME_OPTIONS[timeframe_label]
    fetch_interval = timeframe_config["seconds"]
    summary_interval = fetch_interval # Send summary every cycle
    last_summary_time = 0

    while True:
        try:
            current_time = time.time()
            stock_data = fetch_stock_data(tickers, timeframe_config)
            
            if stock_data:
                await check_for_alerts(stock_data, timeframe_config)
                
                if current_time - last_summary_time >= summary_interval:
                    await send_summary_updates(stock_data, timeframe_config)
                    last_summary_time = current_time

            print(f"\nWaiting for {fetch_interval} seconds until next check...")
            await asyncio.sleep(fetch_interval)

        except KeyboardInterrupt:
            print("Bot loop stopped by user.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            await asyncio.sleep(fetch_interval) # Wait before retrying