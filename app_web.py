import datetime
import pandas as pd
import plotly.graph_objects as graph_objects
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定 (設定為寬螢幕模式，並強制套用行動端側邊欄預設隱藏)
st.set_page_config(
    page_title="行動看盤系統", layout="wide", initial_sidebar_state="collapsed"
)

# 減少網頁頂部空白，讓手機畫面更緊湊
st.markdown(
    """
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem; padding-left: 0.5rem; padding-right: 0.5rem;}
        div[data-testid="stMetric"] { background-color: #1e222d; padding: 5px 10px; border-radius: 5px; }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. 數據下載與核心計算 (保持原本強大的上市櫃自動辨識)
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

    df_daily["MA37"] = df_daily["Close"].rolling(window=37).mean()
    df_daily["MA160"] = df_daily["Close"].rolling(window=160).mean()

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


# --- 手機版置頂控制面板 ---
with st.expander("🔍 點擊此處：切換股票 / 設定天數", expanded=False):
    stock_id = st.text_input("請輸入股票代號", value="2330")
    days_back = st.slider("讀取歷史天數", min_value=200, max_value=500, value=300)

# --- 網頁畫面渲染 ---
if stock_id:
    df, prices, full_ticker = load_data_and_calculate(stock_id, days_back)

    if df is not None:
        # 標題與股票名稱
        st.markdown(f"### 📊 {full_ticker} 關鍵技術指標")

        # 行動端優化：使用緊湊型欄位排列（自適應一排到三排）
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
        c1.metric(label="🔴 壓力", value=f"{prices['resistance']:.1f}")
        c2.metric(label="🍏 日關鍵", value=f"{prices['day']:.1f}")
        c3.metric(label="🔷 周關鍵", value=f"{prices['week']:.1f}")
        c4.metric(label="🔶 月關鍵", value=f"{prices['month']:.1f}")
        c5.metric(label="🟢 支撐", value=f"{prices['support']:.1f}")

        # 4. 互動式 K 線圖
        df_plot = df.tail(60).copy()
        df_plot["Date_Str"] = df_plot.index.strftime("%Y-%m-%d")

        fig = graph_objects.Figure()

        # K線
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

        # 均線
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

        # 關鍵技術價橫線
        x_range = df_plot["Date_Str"]
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["resistance"]] * len(x_range),
                mode="lines",
                name=f"壓力: {prices['resistance']:.1f}",
                line=dict(color="#E53935", width=1.5, dash="dash"),
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["day"]] * len(x_range),
                mode="lines",
                name=f"日關: {prices['day']:.1f}",
                line=dict(color="#4CAF50", width=1.2, dash="dash"),
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["week"]] * len(x_range),
                mode="lines",
                name=f"周關: {prices['week']:.1f}",
                line=dict(color="#2196F3", width=1.2, dash="dash"),
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["month"]] * len(x_range),
                mode="lines",
                name=f"月關: {prices['month']:.1f}",
                line=dict(color="#FF5722", width=1.2, dash="dash"),
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            graph_objects.Scatter(
                x=x_range,
                y=[prices["support"]] * len(x_range),
                mode="lines",
                name=f"支撐: {prices['support']:.1f}",
                line=dict(color="#2E7D32", width=1.5, dash="dash"),
                hoverinfo="skip",
            )
        )

        # 佈局優化（特別針對手機端優化圖例配置）
        fig.update_layout(
            height=500,  # 稍微縮減高度，適應手機單手操作
            xaxis_rangeslider_visible=False,
            xaxis=dict(type="category", tickangle=-45),
            template="plotly_dark",
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified",
            # 手機版圖例改放到圖表正下方，水平排列，避免擠壓到右側空間
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.4,
                xanchor="center",
                x=0.5,
                font=dict(size=10),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"❌ 無法獲獲股票 {stock_id} 的資料。")
