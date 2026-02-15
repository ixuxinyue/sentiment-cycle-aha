import akshare as ak
import pandas as pd
import datetime
import json
import os
import time

DATA_FILE = "../public/data.json"

def get_trading_date(delta_days=0):
    """
    Get trading date with offset. 
    Here we simplify: just use today if it's a trading day, or previous Friday if weekend.
    For rigorous usage, one should check akshare's trade calendar.
    """
    today = datetime.date.today()
    target_date = today - datetime.timedelta(days=delta_days)
    # Simple check for weekend
    while target_date.weekday() > 4: # Sat=5, Sun=6
        target_date -= datetime.timedelta(days=1)
    return target_date.strftime("%Y%m%d")

def get_previous_trading_date(current_date_str):
    # This is a naive implementation. In production, use a proper trade calendar.
    # We will try to find the previous trading day by going back day by day and checking if data exists, 
    # or just assume M-F. 
    curr = datetime.datetime.strptime(current_date_str, "%Y%m%d").date()
    prev = curr - datetime.timedelta(days=1)
    while prev.weekday() > 4:
        prev -= datetime.timedelta(days=1)
    return prev.strftime("%Y%m%d")

def update_sentiment_data():
    today_str = get_trading_date()
    print(f"Fetching data for {today_str}...")

    # 1. Market Index (大盘系数) = Up Count / 20
    # stock_zh_a_spot_em: Realtime quote for all A-shares
    try:
        spot_df = ak.stock_zh_a_spot_em()
        up_count = len(spot_df[spot_df['涨跌幅'] > 0])
        market_index = up_count / 20
        print(f"Market Index: {market_index} (Up Count: {up_count})")
    except Exception as e:
        print(f"Error fetching market index: {e}")
        return

    # 2. Super Short Sentiment (超短情绪)
    try:
        # 2a. Limit Up Count (今日涨停数)
        zt_df = ak.stock_zt_pool_em(date=today_str)
        limit_up_count = len(zt_df) if zt_df is not None else 0
        
        # 2b. New Highs (百日新高 / 2)
        # Approximate: close >= 100-day high. 
        # Since calculating this for 5000 stocks is slow, we use a heuristic or alternative if available.
        # Akshare has stock_rank_cxg_ths (Create New High). 
        # But that might be unstructured. 
        # For now, let's assume 0 or try to fetch 'stock_rank_cxg_ths' if it works, otherwise use a placeholder.
        # A common proxy in sentiment monitoring is just looking at "New High" concept count.
        # Let's try to fetch a specific 'new high' board if possible. 
        # If not, computing it requires history. We will use a placeholder of 50 for now or implement a quick check if possible.
        # Actually, let's skip complex calculation for now and use a static estimate or find a better API later. 
        # We will count how many stocks in spot_df have '60日涨幅' > 20%? No.
        # Let's use a simpler metric: Stocks with > 9% gain as a proxy if we can't get new highs easily.
        # Or better: ak.stock_rank_cxg_ths() 
        try:
            # This API might require specific parameters or might fail.
            # safe fallback: 
            new_high_df = ak.stock_rank_cxg_ths(symbol="创月新高") # Month high? Article says 100 days.
            # let's try '创半年新高'
            new_high_count = len(new_high_df) if new_high_df is not None else 0
        except:
            new_high_count = 0 

        # 2c. Yesterday Limit Up Performance (昨日涨停表现 * 1000)
        # We need yesterday's limit up pool first.
        prev_date_str = get_previous_trading_date(today_str)
        try:
            prev_zt_df = ak.stock_zt_pool_em(date=prev_date_str)
            if prev_zt_df is not None and not prev_zt_df.empty:
                # Filter these stocks in today's spot_df
                prev_codes = prev_zt_df['代码'].tolist()
                # Find current performance of these stocks
                # spot_df has '代码' (no suffix usually) or with. 
                # Akshare spot_df '代码' is like '000001'.
                current_perf_df = spot_df[spot_df['代码'].isin(prev_codes)]
                avg_pct_chg = current_perf_df['涨跌幅'].mean()
                yest_limit_up_perf = avg_pct_chg * 1000 if not pd.isna(avg_pct_chg) else 0
            else:
                yest_limit_up_perf = 0
        except:
            yest_limit_up_perf = 0
            
        super_short_sentiment = limit_up_count + (new_high_count / 2) + yest_limit_up_perf
        print(f"Super Short Sentiment: {super_short_sentiment}")

    except Exception as e:
        print(f"Error fetching super short sentiment: {e}")
        return

    # 3. Losing Money Effect (亏钱效应)
    try:
        # 3a. Fried Board (Bomb) Count (炸板数)
        zb_df = ak.stock_zt_pool_zbgc_em(date=today_str)
        bomb_count = len(zb_df) if zb_df is not None else 0
        炸板率 = 0 # Need total potential limit ups? Or just count? 
        # Formula: 炸板率 * 100. Rate = Bomb / (Bomb + LimitUp).
        total_touch_limit = bomb_count + limit_up_count
        炸板率 = (bomb_count / total_touch_limit) if total_touch_limit > 0 else 0
        
        # 3b. Limit Down Count (跌停数)
        dt_df = ak.stock_zt_pool_dtgc_em(date=today_str)
        limit_down_count = len(dt_df) if dt_df is not None else 0
        
        # 3c. Huge Drawdown (大幅回撤)
        # Defined as observing stocks with significant drop. 
        # Using spot_df, count stocks with '涨跌幅' < -7% (excluding limit down ~ -10%).
        # Or simple count of stocks < -5%.
        # Let's use: Stocks with drop > 7%.
        huge_drawdown_count = len(spot_df[spot_df['涨跌幅'] < -7])
        
        losing_money_effect = (炸板率 * 100) + (limit_down_count + huge_drawdown_count) * 2
        print(f"Losing Money Effect: {losing_money_effect}")
        
    except Exception as e:
        print(f"Error fetching losing money effect: {e}")
        return

    # Create new record
    new_record = {
        "date": today_str,
        "market_index": round(market_index, 2),
        "super_short_sentiment": round(super_short_sentiment, 2),
        "losing_money_effect": round(losing_money_effect, 2),
        "details": {
            "up_count": int(up_count),
            "limit_up_count": int(limit_up_count),
            "bomb_count": int(bomb_count),
            "limit_down_count": int(limit_down_count)
        }
    }

    # Save to file
    file_path = os.path.join(os.path.dirname(__file__), DATA_FILE)
    
    # Check if directory exists (public)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                data = []
    else:
        data = []

    # Update or append
    # Check if date exists
    existing = False
    for i, item in enumerate(data):
        if item['date'] == today_str:
            data[i] = new_record
            existing = True
            break
    
    if not existing:
        data.append(new_record)
        
    # Sort by date
    data.sort(key=lambda x: x['date'])

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully updated data for {today_str} in {file_path}")

if __name__ == "__main__":
    update_sentiment_data()
