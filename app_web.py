import datetime
import mplfinance as mpf
import pandas as pd
import yfinance as yf


def get_stock_key_prices(stock_id, days_back=120):
    """下載股票資料並計算日、周、月關鍵價"""
    if len(stock_id) >= 4 and stock_id.isdigit():
        ticker_id = f"{stock_id}.TW"
    else:
        ticker_id = stock_id.upper()

    print(f"正在抓取 {ticker_id} 的歷史資料...")

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days_back)

    df_daily = yf.download(ticker_id, start=start_date, end=end_date)

    if df_daily.empty:
        print("❌ 找不到該股票資料，請檢查股號是否正確。")
        return None, None

    if isinstance(df_daily.columns, pd.MultiIndex):
        df_daily.columns = df_daily.columns.get_level_values(0)

    # --- 計算關鍵價 ---
    latest_day = df_daily.iloc[-1]
    day_key_price = float((latest_day["High"] + latest_day["Low"]) / 2)

    df_weekly = df_daily.resample("W-FRI").agg(
        {"High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    latest_week = df_weekly.iloc[-1]
    week_key_price = float((latest_week["High"] + latest_week["Low"]) / 2)

    df_monthly = df_daily.resample("ME").agg(
        {"High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    )
    latest_month = df_monthly.iloc[-1]
    month_key_price = float((latest_month["High"] + latest_month["Low"]) / 2)

    # 將畫圖要用的這60根K線切出來
    df_plot = df_daily.tail(60).copy()

    # 關鍵技巧：在 DataFrame 裡面建立三個新欄位，填滿算好的關鍵價數值
    # 這樣 mplfinance 畫線時才會自動幫我們產生圖例標籤
    df_plot["Day_Key"] = day_key_price
    df_plot["Week_Key"] = week_key_price
    df_plot["Month_Key"] = month_key_price

    key_prices = {
        "day": day_key_price,
        "week": week_key_price,
        "month": month_key_price,
    }
    return df_plot, key_prices


# --- 主程式執行區 ---
if __name__ == "__main__":
    user_input = input("請輸入股票代號（台股如 2330，美股如 AAPL）: ").strip()

    df_plot, prices = get_stock_key_prices(user_input)

    if df_plot is not None:
        # 設定繁體中文字型，避免標題和圖例出現亂碼
        custom_rc = {"font.sans-serif": ["Microsoft JhengHei", "Heiti TC", "Arial"]}
        my_style = mpf.make_mpf_style(
            base_mpf_style="charles", rc=custom_rc, gridstyle=":"
        )

        # 這裡利用 make_addplot 產生三條水平線，並指定 label 來作為圖例
        # 綠色 = 日關鍵, 藍色 = 周關鍵, 橘色 = 月關鍵
        ap = [
            mpf.make_addplot(
                df_plot["Day_Key"],
                color="#4CAF50",
                linestyle="--",
                width=1.5,
                label=f"日關鍵價: {prices['day']:.2f}",
            ),
            mpf.make_addplot(
                df_plot["Week_Key"],
                color="#2196F3",
                linestyle="--",
                width=1.5,
                label=f"周關鍵價: {prices['week']:.2f}",
            ),
            mpf.make_addplot(
                df_plot["Month_Key"],
                color="#FF5722",
                linestyle="--",
                width=1.5,
                label=f"月關鍵價: {prices['month']:.2f}",
            ),
        ]

        print("📈 正在開啟 K 線圖視窗...")

        # 開始畫圖
        mpf.plot(
            df_plot,
            type="candle",
            volume=True,
            style=my_style,
            title=f"\nStock {user_input} K-Line & Key Prices",
            ylabel="Price",
            ylabel_lower="Volume",
            addplot=ap,  # 將剛才設定的加載圖線與圖例放進去
            figscale=1.2,
            block=True,
        )

        input("\n按 [Enter] 鍵結束程式並關閉視窗...")
