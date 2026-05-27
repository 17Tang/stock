import datetime
import pandas as pd
import plotly.graph_objects as graph_objects
import streamlit as st
import yfinance as yf

# 1. 網頁基本設定 (安全邊距維持 3.5rem 確保手機不截斷)
st.set_page_config(
    page_title="行動看盤系統", layout="wide", initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
        .block-container {padding-top: 3.5rem; padding-bottom: 0rem; padding-left: 0.4rem; padding-right: 0.4rem;}
        h3 { margin-top: 0rem; margin-bottom: 0.5rem; }
    </style>
""",
    unsafe_allow_html=True,
)


# 2. 數據下載與核心計算 (支援前日數據與當日修正)
@st.cache_data(ttl=60)
def load_data_and_calculate(stock_id):
    days_back = 365
    today = datetime.date.today()
    # 修正日期邏輯：結束日期設為明天，確保能抓到今天的最新數據
    end_date = today + datetime.timedelta(days=1)
    start_date = today - datetime.timedelta(days=days_back)

    if len(stock_id) >= 4 and stock_id.isdigit():
        ticker_id = f"{stock_id}.TW"
        df_daily = yf.download(ticker_id, start=start_date, end=end_date)
        if df_daily.empty:
            ticker_id = f"{stock_id}.TWO"
            df_daily = yf.download(ticker_id, start=start_date, end=end_date)
    else:
        ticker_id = stock_id.upper()
        df_daily = yf.download(ticker_id, start=start_date, end=end_date)

    if df_daily.empty or len(df_daily) < 2:
        return None, None, stock_id

    if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)

    # 計算均線
    df_daily["MA37"] = df_daily["Close"].rolling(window=37).mean()
    df_daily["MA160"] = df_daily["Close"].rolling(window=160).mean()

    # --- 數據提取 ---
    # 今日數據 (T)
    t_day = df_daily.iloc[-1]
    t_h, t_l, t_c = float(t_day["High"]), float(t_day["Low"]), float(t_day["Close"])
    
    # 前一交易日數據 (P)
    p_day = df_daily.iloc[-2]
    p_h, p_l = float(p_day["High"]), float(p_day["Low"])

    # --- 計算數值 ---
    # 今日 R/K/S
    t_res = t_h + (t_h - t_l) * 0.382
    t_key = (t_h + t_l) / 2
    t_sup = t_l - (t_h - t_l) * 0.382

    # 前日 R/K/S
    p_res = p_h + (p_h - p_l) * 0.382
    p_key = (p_h + p_l) / 2
    p_sup = p_l - (p_h - p_l) * 0.382

    # 周/月關鍵價 (基於採樣)
    df_weekly = df_daily.resample("W-FRI").agg({"High": "max", "Low": "min"})
    w_key = float((df_weekly.iloc[-1]["High"] + df_weekly.iloc[-1]["Low"]) / 2)

    df_monthly = df_daily.resample("ME").agg({"High": "max", "Low": "min"})
    m_key = float((df_monthly.iloc[-1]["High"] + df_monthly.iloc[-1]["Low"]) / 2)

    prices = {
        "current": t_c,
        "t_res": t_res, "t_key": t_key, "t_sup": t_sup,
        "p_res": p_res, "p_key": p_key, "p_sup": p_sup,
        "w_key": w_key, "m_key": m_key
    }
    return df_daily, prices, ticker_id


# --- 頂部輸入區 ---
stock_id = st.text_input("🔍 輸入股票代號", value="2330").strip()

if stock_id:
    df, prices, full_ticker = load_data_and_calculate(stock_id)

    if df is not None:
        st.markdown(f"### 📊 {full_ticker}")

        # ⚡ 3x3 九宮格 UI：左列前日、中列今日、右列現價與長線
        html_grid = f"""
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 12px;">
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #7f1d1d;">
                <span style="color: #ef9a9a; font-size: 10px;">前日壓力</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['p_res']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #ef5350;">
                <span style="color: #ef5350; font-size: 10px;">今日壓力</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['t_res']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border: 1px solid #ffb74d;">
                <span style="color: #ffb74d; font-size: 10px; font-weight: bold;">股票現價</span><br>
                <span style="color: #ffb74d; font-size: 15px; font-weight: bold;">{prices['current']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #827717;">
                <span style="color: #dce775; font-size: 10px;">前日關鍵</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['p_key']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #cddc39;">
                <span style="color: #cddc39; font-size: 10px;">今日關鍵</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['t_key']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #2196F3;">
                <span style="color: #2196F3; font-size: 10px;">周關鍵價</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['w_key']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #1b5e20;">
                <span style="color: #a5d6a7; font-size: 10px;">前日支撐</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['p_sup']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #4CAF50;">
                <span style="color: #4CAF50; font-size: 10px;">今日支撐</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['t_sup']:.1f}</span>
            </div>
            <div style="background-color: #1e222d; padding: 6px; border-radius: 6px; text-align: center; border-left: 3px solid #FF5722;">
                <span style="color: #FF5722; font-size: 10px;">月關鍵價</span><br>
                <span style="color: #ffffff; font-size: 15px; font-weight: bold;">{prices['m_key']:.1f}</span>
            </div>
        </div>
        """
        st.markdown(html_grid, unsafe_allow_html=True)

        # 4. K 線圖 (僅保留 K 線與均線)
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
                name="37MA",
                line=dict(color="#FFD700", width=1.5),
            )
        )
        fig.add_trace(
            graph_objects.Scatter(
                x=df_plot["Date_Str"],
                y=df_plot["MA160"],
                mode="lines",
                name="160MA",
                line=dict(color="#E040FB", width=2.5),
            )
        )

        # 佈局配置 (取消所有水平線，回歸純淨 K 線圖)
        fig.update_layout(
            height=480,
            xaxis_rangeslider_visible=False,
            xaxis=dict(type="category", tickangle=-45),
            template="plotly_dark",
            margin=dict(l=5, r=5, t=5, b=5),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.35,
                xanchor="center",
                x=0.5,
                font=dict(size=10),
            ),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"❌ 無法獲取股票 {stock_id} 的資料。")
