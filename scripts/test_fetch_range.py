import akshare as ak
import pandas as pd
import datetime
import time

def test_fetch_range(start_date, end_date):
    print(f"Testing Fetch for Range: {start_date} to {end_date}")
    
    start_dt = datetime.datetime.strptime(start_date, "%Y%m%d").date()
    end_dt = datetime.datetime.strptime(end_date, "%Y%m%d").date()
    
    current = start_dt
    
    # Pre-fetch index data once to be faster
    try:
        index_df = ak.stock_zh_index_daily(symbol="sh000001")
    except:
        index_df = pd.DataFrame()
    
    while current <= end_dt:
        date_str = current.strftime("%Y%m%d")
        
        # Simple weekday check
        if current.weekday() > 4:
            print(f"Skipping {date_str} (Weekend)")
            current += datetime.timedelta(days=1)
            continue
            
        print(f"Fetching {date_str}...")
        
        market_index = 0
        pct_chg = 0
        limit_up_count = 0
        limit_down_count = 0
        
        try:
            # 1. Market Index (SSE Composite Proxy)
            if not index_df.empty:
                row = index_df[index_df['date'] == current]
                if not row.empty:
                    idx = row.index[0]
                    if idx > 0:
                        prev_close = index_df.iloc[idx-1]['close']
                        curr_close = row.iloc[0]['close']
                        pct_chg = ((curr_close - prev_close) / prev_close) * 100
                        market_index = max(0, min(200, 100 + (pct_chg * 50)))
                else:
                    pass # Keep 0
            
            # 2. Limit Up
            zt_df = ak.stock_zt_pool_em(date=date_str)
            if zt_df is not None:
                limit_up_count = len(zt_df)
                
            # 3. Limit Down
            dt_df = ak.stock_zt_pool_dtgc_em(date=date_str)
            if dt_df is not None:
                limit_down_count = len(dt_df)
                
            print(f"  Result -> Market Idx: {market_index:.2f} ({pct_chg:+.2f}%) | LimitUp: {limit_up_count} | LimitDown: {limit_down_count}")

        except Exception as e:
            print(f"  Failed date {date_str}: {e}")
        
        current += datetime.timedelta(days=1)
        time.sleep(1) # Be nice to API

if __name__ == "__main__":
    test_fetch_range("20250813", "20250828")
