import akshare as ak
import pandas as pd
import datetime
import json
import os
import sys

DATA_FILE = "public/data.json"

def test_fetch_one(date_str):
    print(f"Testing Fetch for Date: {date_str}")
    
    # 1. Market Index Proxy
    try:
        index_df = ak.stock_zh_index_daily(symbol="sh000001")
        target_date_obj = datetime.datetime.strptime(date_str, "%Y%m%d").date()
        row = index_df[index_df['date'] == target_date_obj]
        
        if not row.empty:
            idx = row.index[0]
            if idx > 0:
                prev_close = index_df.iloc[idx-1]['close'] # Get preview
                curr_close = row.iloc[0]['close']
                pct_chg = ((curr_close - prev_close) / prev_close) * 100
                market_index = max(0, min(200, 100 + (pct_chg * 50)))
                print(f"  [Market Index] Success! Index Value: {market_index:.2f} (Based on SSE Change: {pct_chg:.2f}%)")
            else:
                print("  [Market Index] Found row but no previous day.")
        else:
            print(f"  [Market Index] No data found for {date_str} in index history.")
            
    except Exception as e:
        print(f"  [Market Index] Error: {e}")

    # 2. Limit Up Count (Sentiment)
    try:
        zt_df = ak.stock_zt_pool_em(date=date_str)
        if zt_df is not None:
            limit_up_count = len(zt_df)
            print(f"  [Sentiment] Success! Limit Up Count: {limit_up_count}")
        else:
            print("  [Sentiment] No data (None returned).")
            limit_up_count = 0
            
    except Exception as e:
        print(f"  [Sentiment] Error: {e}")

    # 3. Limit Down (Losing Money) & Bomb Count
    try:
        dt_df = ak.stock_zt_pool_dtgc_em(date=date_str)
        if dt_df is not None:
            limit_down_count = len(dt_df)
            print(f"  [Losing Money] Success! Limit Down Count: {limit_down_count}")
        else:
            print("  [Losing Money] No Limit Down data.")
            limit_down_count = 0
            
        zb_df = ak.stock_zt_pool_zbgc_em(date=date_str)
        if zb_df is not None:
             bomb_count = len(zb_df)
             print(f"  [Bomb Count] Success! Bomb Count: {bomb_count}")
        else:
             print("  [Bomb Count] No Bomb data.")
             bomb_count = 0
            
    except Exception as e:
        print(f"  [Losing Money/Bomb] Error: {e}")

    # Save to simplistic JSON for proof
    record = {
        "date": date_str,
        "test": "valid"
    }
    
    # Write to verify file system access
    try:
        with open("public/data.json", "w") as f:
            json.dump([record], f, indent=2)
        print("  [File I/O] Successfully wrote dummy record to public/data.json")
    except Exception as e:
        print(f"  [File I/O] Error: {e}")

if __name__ == "__main__":
    test_fetch_one("20260202")
