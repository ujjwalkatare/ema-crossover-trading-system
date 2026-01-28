import os
import sys
import requests
import pandas as pd
import time
import pytz
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from django.conf import settings
from django.db import connection
from .models import MonitoringSession, MonitoredStock, SignalEvent
from asgiref.sync import sync_to_async
from requests.utils import quote  # ✅ For safe ticker encoding
from pathlib import Path          # ✅ For safe filenames

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "8475210830:AAFE5ed13AYPh63qWG1-6YTMB81-mSqFSZw"
CHAT_ID = "1319951741"
EMA_PERIODS = [5, 20]
TIMEFRAME_OPTIONS = {
    "1 Minute":   {"api": "1m", "seconds": 60, "period": "1d"},
    "5 Minutes":  {"api": "5m", "seconds": 300, "period": "5d"},
    "15 Minutes": {"api": "15m", "seconds": 900, "period": "10d"},
    "30 Minutes": {"api": "30m", "seconds": 1800, "period": "20d"},
    "1 Hour":     {"api": "60m", "seconds": 3600, "period": "1mo"},
    "4 Hours":    {"api": "4h", "seconds": 14400, "period": "3mo"},
}
bot = Bot(token=TELEGRAM_TOKEN)
last_crossover_signals = {}

# --- DATA STRUCTURE ---
class StockData:
    def __init__(self, ticker, data, ema_data, trend, crossover, is_new_crossover, current_close, latest_ema5, latest_ema20):
        self.ticker, self.data, self.ema_data, self.trend, self.crossover = ticker, data, ema_data, trend, crossover
        self.is_new_crossover, self.current_close, self.latest_ema5, self.latest_ema20 = is_new_crossover, current_close, latest_ema5, latest_ema20

# --- HELPER & CALCULATION FUNCTIONS ---
def load_tickers_from_csv(file_path='stock_names.csv'):
    """Load stocks + indices + cryptos from CSV and normalize tickers."""
    try:
        df = pd.read_csv(file_path)
        symbols = []
        for s in df['SYMBOL'].dropna().astype(str):
            s = s.strip().upper()
            # ✅ Keep indices (^NSEI, ^NSEBANK, etc.) or symbols with suffix (.NS / .BO)
            # ✅ Keep cryptos (BTC-USD, ETH-USD, etc.)
            if s.startswith('^') or '.' in s or s.endswith('-USD'):
                symbols.append(s)
            else:
                # Default: assume NSE equity and append .NS
                symbols.append(f"{s}.NS")
        print(f"✅ Successfully loaded {len(symbols)} symbols from '{file_path}'.")
        return symbols
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
        print(f"❌ Failed to send Telegram message: {e}")
        return False

# --- DATABASE HELPERS ---
@sync_to_async
def get_active_session():
    connection.close()
    return MonitoringSession.objects.filter(is_active=True).order_by('-start_time').first()

@sync_to_async
def is_session_active(session_id):
    connection.close()
    return MonitoringSession.objects.filter(id=session_id, is_active=True).exists()

@sync_to_async
def update_stock_in_db(session, stock_result):
    MonitoredStock.objects.filter(session=session, ticker=stock_result.ticker).update(
        last_trend=stock_result.trend, last_price=stock_result.current_close
    )

@sync_to_async
def save_signal_event_in_db(session, stock, timeframe_label):
    SignalEvent.objects.create(
        session=session,
        ticker=stock.ticker,
        signal_type=stock.crossover,
        description=f"Crossover on {timeframe_label} chart"
    )

@sync_to_async
def deactivate_session_in_db(session):
    if session:
        session.is_active = False
        session.save()

# --- CORE LOGIC ---

def fetch_single_stock_data(ticker, timeframe_config):
    timeframe_api = timeframe_config["api"]
    timeframe_period = timeframe_config["period"]
    try:
        # ✅ Encode ticker safely (handles ^NSEI etc.)
        escaped_ticker = quote(ticker, safe='')
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{escaped_ticker}?range={timeframe_period}&interval={timeframe_api}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        response.raise_for_status()
        result = response.json()

        if not result.get('chart') or not result['chart'].get('result'): return None
        quotes = result['chart']['result'][0]
        timestamps, closes = quotes.get('timestamp', []), quotes['indicators']['quote'][0].get('close', [])
        
        if not timestamps or not closes or len(closes) < max(EMA_PERIODS): return None
        data = [{'close': cl} for cl in closes if cl is not None]
        if not data: return None

        ema_data = {p: calculate_ema(data, p) for p in EMA_PERIODS}
        if not ema_data[5] or not ema_data[20]: return None
        
        current_close = data[-1]['close']
        trend = determine_trend(ema_data[5], ema_data[20], current_close)
        crossover_result = detect_crossover(ema_data[5], ema_data[20])

        print(f"--- {datetime.now().strftime('%H:%M:%S')} - {ticker} ({timeframe_api}) --- TREND: {trend} | SIGNAL: {crossover_result['signal']}")

        # ✅ Save each symbol’s intraday data to CSV
        safe_name = ticker.replace("^", "").replace(".", "_").replace("/", "_")
        out_path = Path("index_data") / f"{safe_name}_intraday.csv"
        os.makedirs("index_data", exist_ok=True)
        pd.DataFrame(data).to_csv(out_path, index=False)

        return StockData(ticker, data, ema_data, trend, crossover_result['signal'],
                         crossover_result['is_new'], current_close,
                         ema_data[5][-1], ema_data[20][-1])
    except Exception as e:
        print(f"❌ Fetch Error for {ticker}: {e}")
        return None

# --- WORKER TASK ---
async def monitor_stock_task(config, session):
    ticker, timeframe_label = config['ticker'], config['timeframe']
    
    if timeframe_label not in TIMEFRAME_OPTIONS:
        print(f"❌ Invalid timeframe '{timeframe_label}' for {ticker}.")
        return
        
    timeframe_config = TIMEFRAME_OPTIONS[timeframe_label]
    fetch_interval = timeframe_config["seconds"]
    
    print(f"✅ Starting monitor for {ticker} ({timeframe_label}) -> every {fetch_interval}s.")
    
    while True:
        try:
            if not await is_session_active(session.id):
                print(f"🛑 Session ended for {ticker}.")
                break

            stock_result = fetch_single_stock_data(ticker, timeframe_config)
            
            if stock_result:
                await update_stock_in_db(session, stock_result)

                # --- 1. Crossover Alerts ---
                if stock_result.is_new_crossover:
                    last_signal_key = f"{stock_result.ticker}-{timeframe_config['api']}"
                    last_signal = last_crossover_signals.get(last_signal_key)
                    if not last_signal or last_signal['type'] != stock_result.crossover:
                        print(f"🚨 NEW CROSSOVER: {stock_result.ticker} ({timeframe_label}) -> {stock_result.crossover}")
                        alert_message = format_alert_message(stock_result, timeframe_label)
                        if await send_telegram_message(alert_message, is_alert=True):
                            last_crossover_signals[last_signal_key] = {'type': stock_result.crossover}
                            await save_signal_event_in_db(session, stock_result, timeframe_label)

                # --- 2. Regular Summary ---
                summary_message = format_summary_message(stock_result, timeframe_label)
                await send_telegram_message(summary_message, is_alert=False)

            await asyncio.sleep(fetch_interval)

        except Exception as e:
            print(f"❌ Error in monitor for {ticker}: {e}.")
            break

# --- MAIN LOOP ---
async def main_bot_loop(stock_configs):
    session = await get_active_session()
    if not session:
        print("❌ No active session in DB. Stopping bot.")
        return

    print(f"--- ✅ Starting Bot for Session ID: {session.id} ---")
    tasks = [asyncio.create_task(monitor_stock_task(config, session)) for config in stock_configs]
    await asyncio.gather(*tasks)
    print("--- 🛑 All tasks stopped. Deactivating session. ---")
    await deactivate_session_in_db(session)
