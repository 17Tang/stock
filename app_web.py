import datetime
import pandas as pd
import plotly.graph_objects as graph_objects
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定
st.set_page_config(page_title="專業股票關鍵價看盤系統", layout="wide")
st.title("📈 關鍵支撐價")

# 2. 側邊欄設定
st.sidebar.header("⚙️ 控制面板")
stock_id = st.sidebar.text_input(
    "請輸入股票代號", value="2330", help="台股如 ^TWII 或 ^TWOII，美股如 AAPL"
)
days_back = st.sidebar.slider(
    "讀取歷史天數", min_value=200, max_value=500, value=300
)


# 3. 數據下載與核心計算
@st.cache_data(ttl=600)
def load_data_and_calculate(stock_id, days_back):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days_back)

    if len(stock_id) >= 4 and stock_id.isdigit():
        ticker_id = f"{stock_id}.TW"
        df_daily = yf.download(ticker_id, start=start_date, end=end_date)
        if df_daily.empty:
            ticker_id = f"{stock_id}.TWO"
            df_daily = yf.download(ticker_id, start=start_date, end=end_date)
    else:
        ticker_id = stock_id.upper()
        df_daily = yf.download(ticker_id, start=start_date, end=end_date)

    if df_daily.empty:
        return None, None, stock_id

    if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)

    # --- 計算均線 (MA) ---
    df_daily["MA37"] = df_daily["Close"].rolling(window=37).mean()
    df_daily["MA160"] = df_daily["Close"].rolling(window=160).mean()

    # --- 核心數據計算 ---
    latest_day = df_daily.iloc[-1]
    high = float(latest_day["High"])
    low = float(latest_day["Low"])

    day_key_price = (high + low) / 2

    df_weekly = df_daily.resample("W-FRI").agg(
        {"High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    week_key_price = float((df_weekly.iloc[-1]["High"] + df_weekly.iloc[-1]["Low"]) / 2)

    df_monthly = df_daily.resample("ME").agg(
        {"High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    month_key_price = float(
        (df_monthly.iloc[-1]["High"] + df_monthly.iloc[-1]["Low"]) / 2
    )

    day_resistance = high + (high - low) * 0.382
    day_support = low - (high - low) * 0.382

    prices = {
        "day": day_key_price,
        "week": week_key_price,
        "month": month_key_price,
        "resistance": day_resistance,
        "support": day_support,
    }
    return df_daily, prices, ticker_id


# --- 網頁畫面渲染 ---
if stock_id:
    df, prices, full_ticker = load_data_and_calculate(stock_id, days_back)

    if df is not None:
        st.subheader(f"📊 {full_ticker} 關鍵技術指標")
        col_res, col_sup = st.columns(2)
        col_res.metric(
            label="🔴 日線壓力價", value=f"{prices['resistance']:.2f}"
        )
        col_sup.metric(label="🟢 日線支撐價", value=f"{prices['support']:.2f}")

        col1, col2, col3 = st.columns(3)
        col1.metric(label="🍏 日關鍵價", value=f"{prices['day']:.2f}")
        col2.metric(label="🔷 周關鍵價", value=f"{prices['week']:.2f}")
        col3.metric(label="🔶 月關鍵價", value=f"{prices['month']:.2f}")

        st.markdown("---")
        st.subheader("🎬 K 線與綜合指標圖")

        # 擷取最後 60 根 K 線顯示
        df_plot = df.tail(60).copy()
        df_plot["Date_Str"] = df_plot.index.strftime("%Y-%m-%d")

        fig = graph_objects.Figure()

        # 1. 繪製 K 線 (蠟燭圖)
        fig.add_trace(
            graph_objects.Candlestick(
                x=df_plot["Date_Str"],
                open=df_plot["Open"],
                high=df_plot["High"],
                low=df_plot["Low"],
                close=df_plot["Close"],
                name="K線",
                increasing_line_color="#ef5350",
                decreasing_line_color="#26a69a",
            )
        )

        # 2. 均線系列 (實線)
        fig.add_trace(
            graph_objects.Scatter(
                x=df_plot["Date_Str"],
                y=df_plot["MA37"],
                mode="lines",
                name="37日均線",
                line=dict(color="#FFD700", width=1.5),
            )
        )

        fig.add_trace(
            graph_objects.Scatter(
                x=df_plot["Date_Str"],
                y=df_plot["MA160"],
                mode="lines",
                name="160日均線",
                line=dict(color="#E040FB", width=2.5),
            )
        )

        # 3. 關鍵技術線系列 (將橫線轉為帶有「數字名稱」的軌跡，會自動排列在均線圖例下方)
        # 為了畫出橫跨整個圖表的水平線，我們建立一個包含相同數值的陣列
        x_range = df_plot["Date_Str"]

        # 🔴 日線壓力價
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["resistance"]] * len(x_range),
                mode="lines",
                name=f"日線壓力: {prices['resistance']:.2f}",
                line=dict(color="#E53935", width=1.5, dash="dash"),
                hoverinfo="skip",  # 避免干擾K線滑鼠提示
            )
        )

        # 🍏 日關鍵價
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["day"]] * len(x_range),
                mode="lines",
                name=f"日關鍵價: {prices['day']:.2f}",
                line=dict(color="#4CAF50", width=1.2, dash="dash"),
                hoverinfo="skip",
            )
        )

        # 🔷 周關鍵價
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["week"]] * len(x_range),
                mode="lines",
                name=f"周關鍵價: {prices['week']:.2f}",
                line=dict(color="#2196F3", width=1.2, dash="dash"),
                hoverinfo="skip",
            )
        )

        # 🔶 月關鍵價
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["month"]] * len(x_range),
                mode="lines",
                name=f"月關鍵價: {prices['month']:.2f}",
                line=dict(color="#FF5722", width=1.2, dash="dash"),
                hoverinfo="skip",
            )
        )

        # 🟢 日線支撐價
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["support"]] * len(x_range),
                mode="lines",
                name=f"日線支撐: {prices['support']:.2f}",
                line=dict(color="#2E7D32", width=1.5, dash="dash"),
                hoverinfo="skip",
            )
        )

        # 網頁圖表佈局優化
        fig.update_layout(
            height=650,
            xaxis_rangeslider_visible=False,
            xaxis=dict(type="category"),  # 保持無假日空格
            template="plotly_dark",
            margin=dict(l=20, r=20, t=30, b=20),
            hovermode="x unified",
            # 優化圖例顯示位置，讓其緊貼右側
            legend=dict(
                yanchor="top", y=0.99, xanchor="left", x=1.01, font=dict(size=12)
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"❌ 無法獲取股票 {stock_id} 的資料。")