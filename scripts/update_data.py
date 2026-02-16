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

# Modified main function signature to accept date
def update_sentiment_data(target_date_str=None):
    if target_date_str is None:
        today_str = get_trading_date()
    else:
        today_str = target_date_str
        
    print(f"Fetching data for {today_str}...")

    new_record = fetch_record_for_date(today_str)

    if new_record is None:
        print(f"Failed to fetch data for {today_str}. Aborting update.")
        return

    # Save to file
    file_path = os.path.join(os.path.dirname(__file__), DATA_FILE)
    
    # Check if directory exists (public)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                if content.strip(): # Handle empty file
                    data = json.loads(content)
            except Exception as e:
                print(f"Warning: Could not load existing data from {file_path}: {e}. Starting with empty data.")
                data = []

    # Update or append
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

def batch_update_history(days=30):
    """
    Fetch data for the last 'days' trading days.
    Optimized: Read file ONCE, Update list, Save file ONCE.
    """
    print(f"Starting batch update for last {days} days...")
    
    # 1. Load existing data
    file_path = os.path.join(os.path.dirname(__file__), DATA_FILE)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                if content.strip():
                    data = json.loads(content)
            except Exception as e:
                print(f"Warning: Could not load existing data: {e}")
                data = []

    # 2. Get trading dates
    try:
        trade_date_df = ak.tool_trade_date_hist_sina()
        trade_dates = trade_date_df['trade_date'].tolist()
        today = datetime.date.today()
        valid_dates = [d for d in trade_dates if d <= today]
        target_dates = valid_dates[-days:]
        
        # 3. Process each date
        for date_obj in target_dates:
            date_str = date_obj.strftime("%Y%m%d")
            
            # Check if we already have valid data for this date?
            # Optional: skip if exists. But for now, let's overwrite to ensure correctness.
            
            print(f"Processing history for {date_str}...")
            
            # Call a helper that returns the record logic, instead of saving itself
            # We need to extract the logic from update_sentiment_data into a get_sentiment_record function
            # But to minimize refactoring, let's just use update_sentiment_data's logic.
            # Wait, update_sentiment_data currently saves to file. 
            # We should refactor update_sentiment_data to separating fetching and saving.
            
            # Hack for now: We will iterate and call a new function `fetch_record_for_date`.
            record = fetch_record_for_date(date_str)
            
            if record:
                # Update or Append
                existing = False
                for i, item in enumerate(data):
                    if item['date'] == date_str:
                        data[i] = record
                        existing = True
                        break
                if not existing:
                    data.append(record)
            
            # Sleep to be nice to API
            time.sleep(1)

        # 4. Save file ONCE
        data.sort(key=lambda x: x['date'])
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Batch update completed. Saved {len(data)} records to {file_path}")
            
    except Exception as e:
        print(f"Error in batch update: {e}")

def fetch_record_for_date(target_date_str):
    """
    Pure Fetch Logic, returns dict or None.
    STRATEGY for History:
    1. Super Short Sentiment: Use 'Limit Up Count' (Real API).
    2. Losing Money: Use 'Limit Down Count' & 'Bomb Count' (Real API).
    3. Market Index: Real 'Up Count' is hard.
       Use Proxy: SSE Composite Index (000001) Change %.
       If Index > 0.5%, assume strong market (~3000 up) -> Index=150
       If Index < -0.5%, assume weak market (~500 up) -> Index=25
       Linear Interpolation: Index = (PctChg + 2) * 40 (clamped 0-200)
    """
    today_str = target_date_str
    print(f"  Fetching data for {today_str}...")
    
    market_index = 0
    up_count = 0
    is_today = (today_str == datetime.date.today().strftime("%Y%m%d"))
    spot_df = pd.DataFrame() 
    
    # 1. Market Index Proxy
    try:
        if is_today:
            spot_df = ak.stock_zh_a_spot_em()
            up_count = len(spot_df[spot_df['涨跌幅'] > 0])
            market_index = up_count / 20
            print(f"  Market Index: {market_index} (Up Count: {up_count})")
        else:
            # HISTORY PROXY: Use SSE Index (000001)
            try:
                # Fetch index history for specific date?
                # Better: Fetch full history ONCE outside loop?
                # For simplicity here: fetch single day index data if possible, or just specific range.
                # ak.stock_zh_index_daily(symbol="sh000001")
                # This is fast.
                index_df = ak.stock_zh_index_daily(symbol="sh000001")
                # Format date to match index_df 'date' column (usually datetime object)
                # index_df['date'] is the index.
                # Let's filter.
                target_date_obj = datetime.datetime.strptime(today_str, "%Y%m%d").date()
                # index_df index is likely dates.
                # Reset index to access date column if needed, or use .loc
                # Convert 'date' column to date object just in case
                # Actually stock_zh_index_daily returns a df with 'date' column.
                # Let's find the row.
                row = index_df[index_df['date'] == target_date_obj]
                
                if not row.empty:
                    # PCT Change calculation
                    # Or use close - open? No, compare to prev close.
                    # This API might not have pct_chg directly?
                    # Columns: date, open, high, low, close, volume
                    # We need prev close.
                    # Let's just find the index of the row and look at previous row.
                    idx = row.index[0]
                    if idx > 0:
                        prev_close = index_df.iloc[idx-1]['close']
                        curr_close = row.iloc[0]['close']
                        pct_chg = ((curr_close - prev_close) / prev_close) * 100
                        
                        # Proxy Formula:
                        # 0% change -> Neutral (~100 index?)
                        # +1% -> Strong (~150)
                        # +2% -> Super Strong (~200)
                        # -1% -> Weak (~50)
                        # -2% -> Super Weak (~0)
                        # New Proxy Formula (Less sensitive):
                        # 0% change -> 100
                        # +3.3% -> 200
                        # -3.3% -> 0
                        # Formula: 100 + (PctChg * 30)
                        # Clamped between 10 and 200 (Visual floor 10)
                        raw_index = 100 + (pct_chg * 30)
                        market_index = max(10, min(200, raw_index))
                        
                        # Creating a fake 'up_count' for UI consistency
                        up_count = int(market_index * 20)
                        print(f"  Market Index (Proxy): {market_index:.2f} (SSE PctChg: {pct_chg:.2f}%)")
                    else:
                        market_index = 100 # Neutral fallback
                        up_count = int(market_index * 20)
                        print(f"  Market Index (Proxy): {market_index:.2f} (No previous day for PctChg)")
                else:
                    market_index = 0 # No trading data?
                    up_count = 0
                    # print(f"    [Warn] No index data for {today_str}")
            except Exception as e:
                print(f"    [Error] Proxy Market Index failed: {e}")
                market_index = 0
                up_count = 0
                
    except Exception as e:
        print(f"  [Error] Market index block failed: {e}")
        # Continue with 0 for market_index

    # 2. Super Short Sentiment
    limit_up_count = 0
    new_high_count = 0 
    yest_limit_up_perf = 0
    
    try:
        zt_df = ak.stock_zt_pool_em(date=today_str)
        if zt_df is not None:
            limit_up_count = len(zt_df)
        else:
            limit_up_count = 0
        
        if is_today:
            try:
                new_high_df = ak.stock_rank_cxg_ths(symbol="创月新高")
                new_high_count = len(new_high_df) if new_high_df is not None else 0
            except: 
                new_high_count = 0
                print(f"  Warning: Could not fetch new highs for {today_str}.")

            prev_date_str = get_previous_trading_date(today_str)
            try:
                prev_zt_df = ak.stock_zt_pool_em(date=prev_date_str)
                if prev_zt_df is not None and not prev_zt_df.empty:
                    prev_codes = prev_zt_df['代码'].tolist()
                    current_perf_df = spot_df[spot_df['代码'].isin(prev_codes)]
                    avg_pct_chg = current_perf_df['涨跌幅'].mean()
                    yest_limit_up_perf = avg_pct_chg * 1000 if not pd.isna(avg_pct_chg) else 0
                else:
                    yest_limit_up_perf = 0
            except: 
                yest_limit_up_perf = 0
                print(f"  Warning: Could not fetch yesterday limit up performance for {today_str}.")
            
            super_short_sentiment = limit_up_count + (new_high_count / 2) + yest_limit_up_perf
        else:
            # History: Use Limit Up Count as primary driver.
            # Maybe add a small 'sentiment' bonus if Market Index (Proxy) was high?
            # Let's keep it simple: Just Limit Up Count * 1.5? (Since we miss New Highs)
            # Or just Limit Up Count.
            super_short_sentiment = limit_up_count 
            
        print(f"  Super Short Sentiment: {super_short_sentiment}")
            
    except Exception as e:
        print(f"  [Error] Sentiment block failed: {e}")
        # Continue with 0 for super_short_sentiment

    # 3. Losing Money
    bomb_count = 0
    limit_down_count = 0
    huge_drawdown_count = 0
    losing_money_effect = 0
    
    try:
        zb_df = ak.stock_zt_pool_zbgc_em(date=today_str)
        if zb_df is not None:
             bomb_count = len(zb_df)
        
        dt_df = ak.stock_zt_pool_dtgc_em(date=today_str)
        if dt_df is not None:
            limit_down_count = len(dt_df)
        
        if is_today:
            huge_drawdown_count = len(spot_df[spot_df['涨跌幅'] < -7])
        else:
            # History Proxy for Huge Drawdown
            # If Market Index is very negative, assume some drawdown.
            if market_index < 50: 
                huge_drawdown_count = 50 # Guess
            else:
                huge_drawdown_count = 0
        
        total_touch_limit = bomb_count + limit_up_count
        炸板率 = (bomb_count / total_touch_limit) if total_touch_limit > 0 else 0
        
        losing_money_effect = (炸板率 * 100) + (limit_down_count + huge_drawdown_count) * 2
        print(f"  Losing Money Effect: {losing_money_effect}")
        
    except Exception as e:
        print(f"  [Error] Losing money block failed: {e}")
        # Continue with 0

    # Prepare details
    details = {
        "limit_up_count": int(limit_up_count),
        "bomb_count": int(bomb_count),
        "limit_down_count": int(limit_down_count)
    }
    
    if is_today:
        details["up_count"] = int(up_count)
    else:
        # History: up_count is not available from API
        details["up_count"] = None
        # Add the proxy source data
        if 'pct_chg' in locals():
             details["sse_change_pct"] = round(pct_chg, 2)

    return {
        "date": today_str,
        "market_index": round(market_index, 2),
        "super_short_sentiment": round(super_short_sentiment, 2),
        "losing_money_effect": round(losing_money_effect, 2),
        "details": details
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

def batch_update_history(days=30):
    """
    Fetch data for the last 'days' trading days.
    """
    # Get last N trading days. 
    # Since we don't have a perfect calendar, we just iterate back and check if it's a weekday.
    # A better way is to use ak.tool_trade_date_hist_sina() to get actual trading dates.
    try:
        trade_date_df = ak.tool_trade_date_hist_sina()
        trade_dates = trade_date_df['trade_date'].tolist()
        # Filter dates up to today
        today = datetime.date.today()
        # Ensure dates are datetime.date objects
        valid_dates = [d for d in trade_dates if d <= today]
        # Get last 30 days (STRICT API LIMIT)
        # We cap it at 30 to avoid errors.
        actual_days = min(days, 30)
        target_dates = valid_dates[-actual_days:]
        
        for date_obj in target_dates:
            date_str = date_obj.strftime("%Y%m%d")
            print(f"Processing history for {date_str}...")
            # We need to adapt the main logic to accept a specific date
            # Refactoring update_sentiment_data to accept 'target_date_str'
            update_sentiment_data(target_date_str=date_str)
            # Sleep to avoid rate limits
            time.sleep(2)
            
    except Exception as e:
        print(f"Error getting trade dates: {e}")

if __name__ == "__main__":
    # Batch update history (e.g. last 30 days)
    batch_update_history(days=30)
    
    # Or just today
    # update_sentiment_data()
