“””
SPX 0DTE Signal Bot — أسعار حقيقية عبر yfinance
يرسل إشارات تداول على Telegram
للأغراض التعليمية فقط — ليست نصيحة مالية
“””

import time
import requests
import yfinance as yf
from datetime import datetime

# ===== إعدادات =====

TELEGRAM_TOKEN = “8633605004:AAGOO5mlpBMDmV9reDkFvjuZQZWcxHpdmvI”
CHAT_ID = “971145292”

ACCOUNT_SIZE   = 10000   # حجم حسابك بالدولار — عدّله
RISK_PER_TRADE = 0.02    # 2% مخاطرة لكل صفقة
MAX_DAILY_LOSS = 0.05    # وقف عند 5% خسارة يومية
CHECK_INTERVAL = 60      # فحص كل 60 ثانية

# ===== تيليقرام =====

def send_telegram(message):
url = f”https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage”
try:
r = requests.post(url, json={
“chat_id”: CHAT_ID,
“text”: message,
“parse_mode”: “HTML”
}, timeout=10)
return r.status_code == 200
except Exception as e:
print(f”خطأ إرسال: {e}”)
return False

# ===== جلب الأسعار الحقيقية =====

def get_real_prices():
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
print(f”خطأ في جلب الأسعار: {e}”)
return None, None

# ===== المؤشرات =====

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

def calc_macd(prices):
e12 = calc_ema(prices[-12:], 12)
e26 = calc_ema(prices, 26)
return round(e12 - e26, 2)

# ===== محرك الإشارات =====

def analyze(prices):
if len(prices) < 26:
return None

```
price = prices[-1]
rsi   = calc_rsi(prices)
ema9  = calc_ema(prices[-9:], 9)
ema21 = calc_ema(prices[-21:], 21)
macd  = calc_macd(prices)
atr   = calc_atr(prices)

buy_cond  = [rsi > 50 and rsi < 68, ema9 > ema21, macd > 0, price > ema21]
sell_cond = [rsi < 50 and rsi > 32, ema9 < ema21, macd < 0, price < ema21]

buy_score  = sum(buy_cond)
sell_score = sum(sell_cond)

sl_pts  = round(atr * 0.8, 2)
tp1_pts = round(atr * 1.2, 2)
tp2_pts = round(atr * 2.0, 2)
contracts = max(1, int((ACCOUNT_SIZE * RISK_PER_TRADE) / (sl_pts * 50)))

if buy_score >= 3:
    return {
        "type": "BUY", "entry": price,
        "sl": round(price - sl_pts, 2),
        "tp1": round(price + tp1_pts, 2),
        "tp2": round(price + tp2_pts, 2),
        "rsi": rsi, "macd": macd,
        "ema": f"EMA9={ema9} > EMA21={ema21} ✅",
        "score": buy_score, "contracts": contracts,
        "risk_usd": round(sl_pts * 50 * contracts),
        "reward_usd": round(tp1_pts * 50 * contracts),
        "rr": round(tp1_pts / sl_pts, 1)
    }
elif sell_score >= 3:
    return {
        "type": "SELL", "entry": price,
        "sl": round(price + sl_pts, 2),
        "tp1": round(price - tp1_pts, 2),
        "tp2": round(price - tp2_pts, 2),
        "rsi": rsi, "macd": macd,
        "ema": f"EMA9={ema9} < EMA21={ema21} ❌",
        "score": sell_score, "contracts": contracts,
        "risk_usd": round(sl_pts * 50 * contracts),
        "reward_usd": round(tp1_pts * 50 * contracts),
        "rr": round(tp1_pts / sl_pts, 1)
    }
return None
```

# ===== تنسيق الرسائل =====

def fmt_signal(s):
now = datetime.now().strftime(”%H:%M:%S”)
label = “🟢📈 شراء” if s[“type”] == “BUY” else “🔴📉 بيع”
return f”””{label} — <b>SPX 0DTE</b>
🕐 {now}

💰 <b>دخول:</b> {s[‘entry’]}
🎯 <b>هدف ١:</b> {s[‘tp1’]}
🎯 <b>هدف ٢:</b> {s[‘tp2’]}
🛑 <b>وقف الخسارة:</b> {s[‘sl’]}

📊 RSI: {s[‘rsi’]} | MACD: {s[‘macd’]}
📉 {s[‘ema’]}
⚡ قوة الإشارة: {s[‘score’]}/4

💼 عقود مقترحة: {s[‘contracts’]}
📉 مخاطرة: <b>${s[‘risk_usd’]}</b>
📈 هدف ربح: <b>${s[‘reward_usd’]}</b>
⚖️ R:R = 1:{s[‘rr’]}

⚠️ <i>للتعليم فقط — القرار لك</i>”””

def fmt_update(price, rsi, checks):
now = datetime.now().strftime(”%H:%M:%S”)
return f””“⏳ <b>تحديث SPX</b> — {now}
💲 السعر: <b>{price}</b>
📊 RSI: {rsi}
🔄 فحص #{checks} — لا توجد إشارة”””

# ===== الحلقة الرئيسية =====

def main():
print(“🚀 البوت يعمل — أسعار حقيقية…”)
send_telegram(“✅ <b>بوت SPX يعمل!</b>\n📡 أسعار حقيقية من yfinance\n⏱ فحص كل دقيقة”)

```
daily_loss  = 0
last_signal = None
checks      = 0
errors      = 0

while True:
    try:
        if daily_loss >= ACCOUNT_SIZE * MAX_DAILY_LOSS:
            send_telegram(f"🚨 <b>توقف التداول</b>\nخسارة اليوم: ${daily_loss:.0f}\nالحساب محمي ✅")
            break

        prices, price = get_real_prices()

        if prices is None or len(prices) < 26:
            errors += 1
            print(f"⚠️ بيانات غير كافية ({errors})")
            if errors >= 5:
                send_telegram("⚠️ مشكلة في جلب الأسعار — تأكد من الاتصال")
                errors = 0
            time.sleep(CHECK_INTERVAL)
            continue

        errors = 0
        checks += 1
        rsi = calc_rsi(prices)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SPX={price} RSI={rsi} فحص#{checks}")

        signal = analyze(prices)

        if signal:
            if last_signal != signal["type"]:
                if send_telegram(fmt_signal(signal)):
                    print(f"✅ {signal['type']} أُرسلت")
                    last_signal = signal["type"]
        else:
            last_signal = None
            if checks % 10 == 0:
                send_telegram(fmt_update(price, rsi, checks))

        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        send_telegram("⛔ البوت أُوقف يدوياً")
        print("توقف")
        break
    except Exception as e:
        print(f"خطأ: {e}")
        time.sleep(30)
```

if **name** == “**main**”:
main()
