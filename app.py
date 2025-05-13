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
tab1, tab2, tab3 = st.tabs(["📊 Manual Forecast", "🧪 Strategy Tester", "🔍 Top 5 Setups"])

# --- Manual Forecast ---
with tab1:
    st.subheader("📊 Manual Forecast")
    times = []
    start = datetime.combine(datetime.today(), time(9, 30))
    end = datetime.combine(datetime.today(), time(16, 0))
    while start <= end:
        times.append(start.time())
        start += timedelta(minutes=5)

    time_options = ["Any time"] + [t.strftime("%H:%M") for t in times]
    selected_time = st.selectbox("Choose a time of day:", time_options, key="manual_time")

    selected_day = st.selectbox("Choose a weekday:", ["Any day", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], key="manual_day")
    weekday_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}

    rsi_min, rsi_max = st.slider("RSI range:", 0, 100, (0, 100))
    volume_min, volume_max = st.slider("Volume range:", 0, int(df["Volume"].max()), (0, int(df["Volume"].max())))
    macd_min, macd_max = st.slider("MACD range:", float(df["MACD"].min()), float(df["MACD"].max()), (float(df["MACD"].min()), float(df["MACD"].max())))
    signal_min, signal_max = st.slider("MACD Signal range:", float(df["MACD_signal"].min()), float(df["MACD_signal"].max()), (float(df["MACD_signal"].min()), float(df["MACD_signal"].max())))
    body_pct_min, body_pct_max = st.slider("Candle Body % Range (Price Action):", float(df["Body_pct"].min()), float(df["Body_pct"].max()), (float(df["Body_pct"].min()), float(df["Body_pct"].max())))

    manual_horizon = st.selectbox("Select forecast horizon:", ["5 minutes", "15 minutes", "60 minutes"], key="manual_horizon")
    shift_map = {"5 minutes": 1, "15 minutes": 3, "60 minutes": 12}
    shift_n = shift_map[manual_horizon]

    if st.button("Get Historical Forecast", key="manual_button"):
        matches = []

        for idx in range(len(df) - shift_n):
            timestamp = df.loc[idx, "Datetime"]
            if selected_time != "Any time" and timestamp.strftime("%H:%M") != selected_time:
                continue
            if selected_day != "Any day" and timestamp.weekday() != weekday_map[selected_day]:
                continue

            rsi_now = df.loc[idx, "RSI"]
            volume_now = df.loc[idx, "Volume"]
            macd_now = df.loc[idx, "MACD"]
            signal_now = df.loc[idx, "MACD_signal"]
            body_pct_now = df.loc[idx, "Body_pct"]

            if pd.isna(rsi_now) or not (rsi_min <= rsi_now <= rsi_max): continue
            if pd.isna(volume_now) or not (volume_min <= volume_now <= volume_max): continue
            if pd.isna(macd_now) or not (macd_min <= macd_now <= macd_max): continue
            if pd.isna(signal_now) or not (signal_min <= signal_now <= signal_max): continue
            if pd.isna(body_pct_now) or not (body_pct_min <= body_pct_now <= body_pct_max): continue

            close_now = df.loc[idx, "Close"]
            close_future = df.loc[idx + shift_n, "Close"] if idx + shift_n < len(df) else None

            if close_future:
                ret = round((close_future - close_now) / close_now * 100, 2)
                matches.append(ret)

        if matches:
            st.success(f"📊 Matches found: {len(matches)}")
            st.success(f"📈 Average return after {manual_horizon}: {round(sum(matches) / len(matches), 3)}%")
        else:
            st.warning("No matches found for those criteria.")


# --- Strategy Tester ---
with tab2:
    st.subheader("🧪 Strategy Tester")
    st.caption("Uses filters from Manual Forecast tab")
    horizon = st.selectbox("Select forecast horizon:", ["5 minutes", "15 minutes", "60 minutes"], key="forecast_horizon")

    if st.button("Run Strategy Tester"):
        horizon_map = {"5 minutes": 1, "15 minutes": 3, "60 minutes": 12}
        horizon_shift = horizon_map[horizon]

        returns = []
        match_indices = []

        for idx in range(len(df) - horizon_shift):
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

            price_future = df.loc[idx + horizon_shift, "Close"]
            returns.append(((price_future - price_now) / price_now) * 100)
            match_indices.append(idx)

        st.write(f"✅ Matches found: {len(match_indices)}")

        if returns:
            avg_return = round(sum(returns) / len(returns), 3)
            st.success(f"📊 Average return after {horizon}: **{avg_return}%**")
            win_trades = sum(1 for r in returns if r > 0)
            st.markdown(f"- **Win rate:** {round((win_trades / len(returns)) * 100, 2)}%")
            st.markdown(f"- **Best trade:** {round(max(returns), 3)}%")
            st.markdown(f"- **Worst trade:** {round(min(returns), 3)}%")
            st.markdown(f"- **Total return if all trades were taken:** {round(sum(returns), 3)}%")

            # --- Risk-Reward Analysis ---
            reward_list = returns
            risk_list = [abs(df.loc[idx, "Body_pct"]) for idx in match_indices]
            rr_list = [r / risk for r, risk in zip(reward_list, risk_list) if risk > 0]
            avg_rr = round(sum(rr_list) / len(rr_list), 2) if rr_list else 0

            gains = [r for r in reward_list if r > 0]
            losses = [abs(r) for r in reward_list if r < 0]
            profit_factor = round(sum(gains) / sum(losses), 2) if losses else float('inf')
            avg_win = round(sum(gains) / len(gains), 2) if gains else 0
            avg_loss = round(sum(losses) / len(losses), 2) if losses else 0
            win_rate = (len(gains) / len(reward_list)) if reward_list else 0
            expectancy = round((win_rate * avg_win) - ((1 - win_rate) * avg_loss), 2)

            st.subheader("📈 Risk-Reward Stats")
            st.markdown(f"- **Avg Reward-to-Risk Ratio:** {avg_rr}")
            st.markdown(f"- **Profit Factor:** {profit_factor}")
            st.markdown(f"- **Expectancy per trade:** {expectancy}%")
        else:
            st.warning("Not enough data for those filters.")


# --- Top Setups ---
with tab3:
    st.subheader("🔍 Top Setups for This Stock")

    setup_horizon = st.selectbox("Choose time horizon for return calculation:", ["5 minutes", "15 minutes", "60 minutes"], key="top5_horizon")
    shift_map = {"5 minutes": 1, "15 minutes": 3, "60 minutes": 12}
    shift_n = shift_map[setup_horizon]

    volume_min = int(df["Volume"].min())
    volume_max = int(df["Volume"].max())
    volume_bins = range(volume_min, volume_max + 200_000, 200_000)

    df["RSI_bin"] = pd.cut(df["RSI"], bins=range(0, 105, 5))
    df["MACD_bin"] = pd.qcut(df["MACD"].dropna(), 4, duplicates='drop')
    df["Volume_bin"] = pd.cut(df["Volume"], bins=volume_bins)
    df["Body_bin"] = pd.qcut(df["Body_pct"].dropna(), 4, duplicates='drop')

    df = df.dropna(subset=["RSI_bin", "MACD_bin", "Volume_bin", "Body_bin"])
    df["future_close"] = df["Close"].shift(-shift_n)
    df["ret_horizon"] = ((df["future_close"] - df["Close"]) / df["Close"]) * 100

    agg_df = (
        df.groupby(["RSI_bin", "MACD_bin", "Volume_bin", "Body_bin"])
        .agg(
            trades=("ret_horizon", "count"),
            avg_return=("ret_horizon", "mean"),
            win_rate=("ret_horizon", lambda x: (x > 0).mean() * 100)
        )
        .reset_index()
    )

    top_strategies = agg_df[
        (agg_df["trades"] >= 10) & (agg_df["avg_return"] >= 0.25)
    ].sort_values("win_rate", ascending=False).head(5)

    if not top_strategies.empty:
        for _, row in top_strategies.iterrows():
            st.markdown(
                f"RSI {row['RSI_bin']}, MACD {row['MACD_bin'].left:.2f}-{row['MACD_bin'].right:.2f}, "
                f"Volume {int(row['Volume_bin'].left):,}-{int(row['Volume_bin'].right):,}, "
                f"Body {row['Body_bin'].left:.2f}-{row['Body_bin'].right:.2f} "
                f"→ 📈 Win Rate: **{row['win_rate']:.2f}%** | Avg Return: **{row['avg_return']:.3f}%** over {row['trades']} trades"
            )
    else:
        st.warning("No strong setups found with ≥ 0.250% return and ≥ 10 trades.")

st.markdown("---")
st.header("📬 Get Notified When a Setup Hits")

with st.form("notify_form"):
    email = st.text_input("Your email")
    ticker_choice = st.selectbox("Which ticker?", ["ALL"] + sorted(ticker_list))
    
    rsi_range = st.slider("RSI range:", 0, 100, (20, 40))
    macd_range = st.slider("MACD range:", -5.0, 5.0, (-1.0, 1.0))
    body_pct_range = st.slider("Candle Body % range:", 0.0, 10.0, (0.5, 3.0))

    submitted = st.form_submit_button("Notify Me")

    if submitted:
        new_row = {
            "email": email,
            "ticker": ticker_choice,
            "rsi_min": rsi_range[0],
            "rsi_max": rsi_range[1],
            "macd_min": macd_range[0],
            "macd_max": macd_range[1],
            "body_pct_min": body_pct_range[0],
            "body_pct_max": body_pct_range[1]
        }

        try:
            df_users = pd.read_csv("users.csv")
            df_users = pd.concat([df_users, pd.DataFrame([new_row])], ignore_index=True)
        except FileNotFoundError:
            df_users = pd.DataFrame([new_row])

        df_users.to_csv("users.csv", index=False)
        st.success("✅ You're set! We'll notify you when your setup hits.")

