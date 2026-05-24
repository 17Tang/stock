import datetime
import pandas as pd
import plotly.graph_objects as graph_objects
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定 (預設隱藏側邊欄)
st.set_page_config(
    page_title="行動看盤系統", layout="wide", initial_sidebar_state="collapsed"
)

# ⚡ 終極防護修正：將 padding-top 拉大到 3.5rem，徹底推開手機瀏覽器網址列與系統黑條
st.markdown(
    """
    <style>
        .block-container {padding-top: 3.5rem; padding-bottom: 0rem; padding-left: 0.4rem; padding-right: 0.4rem;}
        h3 { margin-top: 0rem; margin-bottom: 0.5rem; }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. 數據下載與核心計算 (固定 365 天)
@st.cache_data(ttl=60)  # 1分鐘快取，兼顧效率與即時現價
def load_data_and_calculate(stock_id):
    days_back = 365
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

    # 計算 37 MA 與 160 MA
    df_daily["MA37"] = df_daily["Close"].rolling(window=37).mean()
    df_daily["MA160"] = df_daily["Close"].rolling(window=160).mean()

    # 核心數據計算
    latest_day = df_daily.iloc[-1]
    high = float(latest_day["High"])
    low = float(latest_day["Low"])
    current_price = float(latest_day["Close"])  # 最新現價

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
        "current": current_price,
        "day": day_key_price,
        "week": week_key_price,
        "month": month_key_price,
        "resistance": day_resistance,
        "support": day_support,
    }
    return df_daily, prices, ticker_id


# --- 頂部直覺輸入區 ---
stock_id = st.text_input("🔍 輸入股票代號", value="2330").strip()

if stock_id:
    df, prices, full_ticker = load_data_and_calculate(stock_id)

    if df is not None:
        # 標題
        st.markdown(f"### 📊 {full_ticker}")

        # ⚡ 顏色優化：將股票現價的標題與數字顏色完全統一為 #ffb74d (亮橘色)，方塊也換成橘色 🟧
        html_table = f"""
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 10px;">
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center;">
                <span style="color: #ef5350; font-size: 11px; font-weight: bold;">🟥 日線壓力</span><br>
                <span style="color: #ffffff; font-size: 16px; font-weight: bold;">{prices['resistance']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border: 1px solid #ffb74d;">
                <span style="color: #ffb74d; font-size: 11px; font-weight: bold;">🟧 股票現價</span><br>
                <span style="color: #ffb74d; font-size: 16px; font-weight: bold;">{prices['current']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center;">
                <span style="color: #26a69a; font-size: 11px; font-weight: bold;">🟩 日線支撐</span><br>
                <span style="color: #ffffff; font-size: 16px; font-weight: bold;">{prices['support']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center;">
                <span style="color: #a5d6a7; font-size: 11px; font-weight: bold;">🟨 日關鍵價</span><br>
                <span style="color: #ffffff; font-size: 16px; font-weight: bold;">{prices['day']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center;">
                <span style="color: #2196F3; font-size: 11px; font-weight: bold;">🟦 周關鍵價</span><br>
                <span style="color: #ffffff; font-size: 16px; font-weight: bold;">{prices['week']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center;">
                <span style="color: #ff7043; font-size: 11px; font-weight: bold;">🟫 月關鍵價</span><br>
                <span style="color: #ffffff; font-size: 16px; font-weight: bold;">{prices['month']:.1f}</span>
            </div>
        </div>
        """
        st.markdown(html_table, unsafe_allow_html=True)

        # 擷取最後 60 根 K 線
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

        # 均線 (MA)
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

        # 技術水平線
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

        # 佈局配置
        fig.update_layout(
            height=450,
            xaxis_rangeslider_visible=False,
            xaxis=dict(type="category", tickangle=-45),
            template="plotly_dark",
            margin=dict(l=5, r=5, t=5, b=5),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.5,
                xanchor="center",
                x=0.5,
                font=dict(size=10),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"❌ 無法獲取股票 {stock_id} 的資料。")
