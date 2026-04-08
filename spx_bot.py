import time
import requests
import yfinance as yf
from datetime import datetime

TELEGRAM_TOKEN = “8633605004:AAGOO5mlpBMDmV9reDkFvjuZQZWcxHpdmvI”
CHAT_ID = “971145292”

ACCOUNT_SIZE = 10000
RISK_PER_TRADE = 0.02
MAX_DAILY_LOSS = 0.05
CHECK_INTERVAL = 60

def send_telegram(message):
url = f”https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage”
try:
r = requests.post(url, json={“chat_id”: CHAT_ID, “text”: message, “parse_mode”: “HTML”}, timeout=10)
return r.status_code == 200
except Exception as e:
print(f”Send error: {e}”)
return False

def get_prices():
try:
ticker = yf.Ticker(”^GSPC”)
df = ticker.history(period=“1d”, interval=“1m”)
if df.empty:
ticker = yf.Ticker(“ES=F”)
df = ticker.history(period=“1d”, interval=“1m”)
if df.empty:
return None, None
closes = list(df[“Close”].round(2))
return closes, closes[-1]
except Exception as e:
print(f”Price error: {e}”)
return None, None

def calc_rsi(prices, period=14):
if len(prices) < period + 1:
return 50.0
gains, losses = [], []
for i in range(1, len(prices)):
d = prices[i] - prices[i-1]
gains.append(max(0, d))
losses.append(max(0, -d))
ag = sum(gains[-period:]) / period
al = sum(losses[-period:]) / period
if al == 0:
return 100.0
return round(100 - 100 / (1 + ag / al), 1)

def calc_ema(prices, period):
if len(prices) < period:
return prices[-1]
k = 2 / (period + 1)
val = prices[0]
for p in prices:
val = p * k + val * (1 - k)
return round(val, 2)

def calc_atr(prices, period=14):
if len(prices) < 2:
return 10.0
ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
return round(sum(ranges[-period:]) / min(period, len(ranges)), 2)

def analyze(prices):
if len(prices) < 26:
return None
price = prices[-1]
rsi = calc_rsi(prices)
ema9 = calc_ema(prices[-9:], 9)
ema21 = calc_ema(prices[-21:], 21)
ema12 = calc_ema(prices[-12:], 12)
ema26 = calc_ema(prices, 26)
macd = round(ema12 - ema26, 2)
atr = calc_atr(prices)
buy = [rsi > 50 and rsi < 68, ema9 > ema21, macd > 0, price > ema21]
sell = [rsi < 50 and rsi > 32, ema9 < ema21, macd < 0, price < ema21]
bs = sum(buy)
ss = sum(sell)
sl_p = round(atr * 0.8, 2)
tp1_p = round(atr * 1.2, 2)
tp2_p = round(atr * 2.0, 2)
contracts = max(1, int((ACCOUNT_SIZE * RISK_PER_TRADE) / (sl_p * 50)))
if bs >= 3:
return {“type”: “BUY”, “entry”: price, “sl”: round(price - sl_p, 2), “tp1”: round(price + tp1_p, 2), “tp2”: round(price + tp2_p, 2), “rsi”: rsi, “macd”: macd, “score”: bs, “contracts”: contracts, “risk”: round(sl_p * 50 * contracts), “reward”: round(tp1_p * 50 * contracts), “rr”: round(tp1_p / sl_p, 1)}
elif ss >= 3:
return {“type”: “SELL”, “entry”: price, “sl”: round(price + sl_p, 2), “tp1”: round(price - tp1_p, 2), “tp2”: round(price - tp2_p, 2), “rsi”: rsi, “macd”: macd, “score”: ss, “contracts”: contracts, “risk”: round(sl_p * 50 * contracts), “reward”: round(tp1_p * 50 * contracts), “rr”: round(tp1_p / sl_p, 1)}
return None

def fmt_signal(s):
now = datetime.now().strftime(”%H:%M:%S”)
arrow = “BUY” if s[“type”] == “BUY” else “SELL”
return f”{arrow} SPX 0DTE\nTime: {now}\n\nEntry: {s[‘entry’]}\nTarget 1: {s[‘tp1’]}\nTarget 2: {s[‘tp2’]}\nStop Loss: {s[‘sl’]}\n\nRSI: {s[‘rsi’]} | MACD: {s[‘macd’]}\nStrength: {s[‘score’]}/4\n\nContracts: {s[‘contracts’]}\nRisk: ${s[‘risk’]} | Reward: ${s[‘reward’]}\nR:R = 1:{s[‘rr’]}\n\nFor educational purposes only”

def main():
print(“Bot started…”)
send_telegram(“SPX Bot is running! Checking every 60 seconds.”)
last_signal = None
checks = 0
errors = 0
while True:
try:
prices, price = get_prices()
if prices is None or len(prices) < 26:
errors += 1
if errors >= 5:
send_telegram(“Warning: Cannot fetch prices.”)
errors = 0
time.sleep(CHECK_INTERVAL)
continue
errors = 0
checks += 1
rsi = calc_rsi(prices)
print(f”[{datetime.now().strftime(’%H:%M:%S’)}] SPX={price} RSI={rsi} check#{checks}”)
signal = analyze(prices)
if signal:
if last_signal != signal[“type”]:
if send_telegram(fmt_signal(signal)):
print(f”Signal sent: {signal[‘type’]}”)
last_signal = signal[“type”]
else:
last_signal = None
if checks % 10 == 0:
send_telegram(f”SPX Update\nPrice: {price}\nRSI: {rsi}\nNo signal. Check #{checks}”)
time.sleep(CHECK_INTERVAL)
except KeyboardInterrupt:
send_telegram(“Bot stopped.”)
break
except Exception as e:
print(f”Error: {e}”)
time.sleep(30)

if **name** == “**main**”:
main()