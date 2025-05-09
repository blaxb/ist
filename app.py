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

# --- Tabs ---
tab1, tab2 = st.tabs(["📊 Manual Forecast", "🔍 Top 5 Setups"])

with tab1:
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

    rsi_min, rsi_max = st.slider("RSI range:", 0, 100, (0, 100))
    volume_min, volume_max = st.slider("Volume range:", 0, int(df["Volume"].max()), (0, int(df["Volume"].max())))
    macd_min, macd_max = st.slider("MACD range:", float(df["MACD"].min()), float(df["MACD"].max()), (float(df["MACD"].min()), float(df["MACD"].max())))
    signal_min, signal_max = st.slider("MACD Signal range:", float(df["MACD_signal"].min()), float(df["MACD_signal"].max()), (float(df["MACD_signal"].min()), float(df["MACD_signal"].max())))
    body_pct_min, body_pct_max = st.slider("Candle Body % Range (Price Action):", float(df["Body_pct"].min()), float(df["Body_pct"].max()), (float(df["Body_pct"].min()), float(df["Body_pct"].max())))

    if st.button("Get Historical Forecast"):
        returns_5 = []
        returns_15 = []
        returns_60 = []
        match_indices = []

        for date in df["Datetime"].dt.date.unique():
            if selected_day != "Any day" and datetime.strptime(str(date), "%Y-%m-%d").weekday() != weekday_map[selected_day]:
                continue

            day_df = df[df["Datetime"].dt.date == date].copy()
            if selected_time == "Any time":
                current_rows = day_df.index
            else:
                current_rows = day_df[day_df["Datetime"].dt.strftime("%H:%M") == selected_time].index

            for idx in current_rows:
                try:
                    rsi_now = df.loc[idx, "RSI"]
                    volume_now = df.loc[idx, "Volume"]
                    macd_now = df.loc[idx, "MACD"]
                    signal_now = df.loc[idx, "MACD_signal"]
                    body_pct_now = df.loc[idx, "Body_pct"]
                    price_now = df.loc[idx, "Close"]

                    if pd.isna(rsi_now) or not (rsi_min <= rsi_now <= rsi_max): continue
                    if not (volume_min <= volume_now <= volume_max): continue
                    if pd.isna(macd_now) or not (macd_min <= macd_now <= macd_max): continue
                    if pd.isna(signal_now) or not (signal_min <= signal_now <= signal_max): continue
                    if pd.isna(body_pct_now) or not (body_pct_min <= body_pct_now <= body_pct_max): continue

                    price_5 = df.iloc[idx + 1]["Close"]
                    price_15 = df.iloc[idx + 3]["Close"]
                    price_60 = df.iloc[idx + 12]["Close"]

                    returns_5.append(((price_5 - price_now) / price_now) * 100)
                    returns_15.append(((price_15 - price_now) / price_now) * 100)
                    returns_60.append(((price_60 - price_now) / price_now) * 100)
                    match_indices.append(idx)
                except IndexError:
                    continue

        st.write(f"✅ Matches found: {len(match_indices)}")

        if returns_5:
            st.success(f"📊 Average 5-min return: **{round(sum(returns_5)/len(returns_5), 3)}%**")
            st.success(f"📊 Average 15-min return: **{round(sum(returns_15)/len(returns_15), 3)}%**")
            st.success(f"📊 Average 60-min return: **{round(sum(returns_60)/len(returns_60), 3)}%**")
            win_trades = sum(1 for r in returns_5 if r > 0)
            st.subheader("📈 Strategy Tester Results (5-min horizon)")
            st.markdown(f"- **Trades tested:** {len(returns_5)}")
            st.markdown(f"- **Win rate:** {round((win_trades / len(returns_5)) * 100, 2)}%")
            st.markdown(f"- **Best trade:** {round(max(returns_5), 3)}%")
            st.markdown(f"- **Worst trade:** {round(min(returns_5), 3)}%")
            st.markdown(f"- **Total return if all trades were taken:** {round(sum(returns_5), 3)}%")
        else:
            st.warning("Not enough data for those filters.")
with tab2:
    # --- Best Setups Finder ---
    st.subheader("🔍 Top 5 Setups for This Stock")

    # Narrowed RSI buckets (10-point width)
    rsi_bins = [(0, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 100)]

    # Fixed-width 100k volume buckets
    volume_min = int(df["Volume"].min())
    volume_max = int(df["Volume"].max())
    volume_bins = [(i, i + 100_000) for i in range(volume_min, volume_max, 100_000)]

    macd_bins = pd.qcut(df["MACD"].dropna(), 4, duplicates='drop').unique().tolist()
    body_bins = pd.qcut(df["Body_pct"].dropna(), 4, duplicates='drop').unique().tolist()

    results = []

    for rsi_min, rsi_max in rsi_bins:
        for macd_range in macd_bins:
            for volume_range in volume_bins:
                for body_range in body_bins:
                    subset = df[
                        (df["RSI"] >= rsi_min) & (df["RSI"] <= rsi_max) &
                        (df["MACD"] >= macd_range.left) & (df["MACD"] <= macd_range.right) &
                        (df["Volume"] >= volume_range[0]) & (df["Volume"] <= volume_range[1]) &
                        (df["Body_pct"] >= body_range.left) & (df["Body_pct"] <= body_range.right)
                    ]
                    for idx in subset.index:
                        try:
                            price_now = df.loc[idx, "Close"]
                            price_5 = df.loc[idx + 1, "Close"]
                            ret_5 = ((price_5 - price_now) / price_now) * 100
                            results.append({
                                "RSI": f"{rsi_min}-{rsi_max}",
                                "MACD": f"{macd_range.left:.2f}-{macd_range.right:.2f}",
                                "Volume": f"{int(volume_range[0]):,}-{int(volume_range[1]):,}",
                                "Body%": f"{body_range.left:.2f}-{body_range.right:.2f}",
                                "Return": ret_5
                            })
                        except:
                            continue

    if results:
        df_results = pd.DataFrame(results)
        summary = df_results.groupby(["RSI", "MACD", "Volume", "Body%"]).agg(
            win_rate=("Return", lambda x: round((x > 0).sum() / len(x) * 100, 2)),
            avg_return=("Return", lambda x: round(x.mean(), 3)),
            trades=("Return", "count")
        ).reset_index()
        top_strategies = summary[summary["trades"] >= 10].sort_values(by="win_rate", ascending=False).head(5)
        for _, row in top_strategies.iterrows():
            st.markdown(f"RSI {row['RSI']}, MACD {row['MACD']}, Volume {row['Volume']}, Body {row['Body%']} → 📈 Win Rate: **{row['win_rate']}%** over {row['trades']} trades")
    else:
        st.warning("No strong setups found based on current data.")
