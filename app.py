import streamlit as st
import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from datetime import datetime, timedelta, time, date

# --- Ticker Selection ---
ticker_list = [
    "SPY", "QQQ", "DIA", "IWM", "VTI", "XLF", "XLK", "XLE", "XLY", "XLV",
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC",
    "BA", "JPM", "BAC", "WFC", "UNH", "V", "MA", "T", "DIS", "PEP",
    "KO", "COST", "WMT", "HD", "NKE", "CRM", "PYPL", "ADBE", "AVGO", "CSCO",
    "CVX", "XOM", "PFE", "MRK", "ABBV", "TMO", "AMGN", "JNJ", "VRTX", "LMT",
    "GE", "GM", "F", "UBER", "LYFT", "PLTR", "SNOW", "NET", "ROKU", "SQ",
    "SHOP", "BABA", "BIDU", "JD", "TSM", "ASML", "IBM", "ORCL", "QCOM", "TXN",
    "ETSY", "EBAY", "ZM", "DOCU", "RBLX", "TWLO", "PANW", "OKTA", "CRWD", "DDOG",
    "TLT", "HYG", "IEF", "SHY", "GLD", "SLV", "USO", "UNG", "UUP", "FXI"
]

ticker = st.selectbox("Select a stock or ETF:", sorted(ticker_list))

# --- Time Selector ---
times = []
start = datetime.combine(datetime.today(), time(9, 30))
end = datetime.combine(datetime.today(), time(16, 0))
while start <= end:
    times.append(start.time())
    start += timedelta(minutes=5)

time_options = ["Any time"] + [t.strftime("%H:%M") for t in times]
selected_time = st.selectbox("Choose a time of day:", time_options)

# --- Weekday Selector ---
selected_day = st.selectbox("Choose a weekday:", ["Any day", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
weekday_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}

# --- Download Data + Compute Indicators ---
st.write(f"\U0001F4E6 Downloading 5-minute {ticker} data from the past 30 days...")
df = yf.Ticker(ticker).history(period="30d", interval="5m").reset_index()
df = df[(df["Datetime"].dt.time >= time(9, 30)) & (df["Datetime"].dt.time <= time(16, 0))]
df["RSI"] = RSIIndicator(close=df["Close"], window=14).rsi()
macd = MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
df["MACD"] = macd.macd()
df["MACD_signal"] = macd.macd_signal()
df["Body"] = df["Close"] - df["Open"]
df["Body_pct"] = df["Body"] / df["Open"] * 100

# --- Best Setups Finder ---
st.subheader("🔍 Top 5 Setups for This Stock")

# Binning logic
rsi_bins = [(0, 30), (30, 50), (50, 70), (70, 100)]
macd_bins = pd.qcut(df["MACD"].dropna(), 4, duplicates='drop').unique().tolist()
volume_bins = pd.qcut(df["Volume"].dropna(), 4, duplicates='drop').unique().tolist()
body_bins = pd.qcut(df["Body_pct"].dropna(), 4, duplicates='drop').unique().tolist()

results = []

for weekday in range(5):
    for rsi_min, rsi_max in rsi_bins:
        for macd_range in macd_bins:
            for volume_range in volume_bins:
                for body_range in body_bins:
                    subset = df[(df["Datetime"].dt.weekday == weekday) &
                                (df["RSI"] >= rsi_min) & (df["RSI"] <= rsi_max) &
                                (df["MACD"] >= macd_range.left) & (df["MACD"] <= macd_range.right) &
                                (df["Volume"] >= volume_range.left) & (df["Volume"] <= volume_range.right) &
                                (df["Body_pct"] >= body_range.left) & (df["Body_pct"] <= body_range.right)]
                    for idx in subset.index:
                        try:
                            price_now = df.loc[idx, "Close"]
                            price_5 = df.loc[idx + 1, "Close"]
                            ret_5 = ((price_5 - price_now) / price_now) * 100
                            results.append({
                                "Day": list(weekday_map.keys())[weekday],
                                "RSI": f"{rsi_min}-{rsi_max}",
                                "MACD": f"{macd_range.left:.2f}-{macd_range.right:.2f}",
                                "Volume": f"{int(volume_range.left):,}-{int(volume_range.right):,}",
                                "Body%": f"{body_range.left:.2f}-{body_range.right:.2f}",
                                "Return": ret_5
                            })
                        except:
                            continue

if results:
    df_results = pd.DataFrame(results)
    summary = df_results.groupby(["Day", "RSI", "MACD", "Volume", "Body%"]).agg(
        win_rate=("Return", lambda x: round((x > 0).sum() / len(x) * 100, 2)),
        avg_return=("Return", lambda x: round(x.mean(), 3)),
        trades=("Return", "count")
    ).reset_index()
    top_strategies = summary[summary["trades"] >= 10].sort_values(by="win_rate", ascending=False).head(5)
    for i, row in top_strategies.iterrows():
        st.markdown(f"**{row['Day']}** — RSI {row['RSI']}, MACD {row['MACD']}, Volume {row['Volume']}, Body {row['Body%']} → 📈 Win Rate: **{row['win_rate']}%** over {row['trades']} trades")
else:
    st.warning("No strong setups found based on current data.")
