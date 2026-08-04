import akshare as ak
import pandas as pd
import datetime
import json
import os
import time
import argparse

DATA_FILE = "../public/data.json"
REQUEST_DELAY_SECONDS = 1

def get_trading_date(delta_days=0):
    """
    Get trading date with offset.
    """
    today = datetime.date.today()
    target_date = today - datetime.timedelta(days=delta_days)
    # Simple check for weekend
    while target_date.weekday() > 4: # Sat=5, Sun=6
        target_date -= datetime.timedelta(days=1)
    return target_date.strftime("%Y%m%d")

def get_previous_trading_date(current_date_str):
    curr = datetime.datetime.strptime(current_date_str, "%Y%m%d").date()
    prev = curr - datetime.timedelta(days=1)
    while prev.weekday() > 4:
        prev -= datetime.timedelta(days=1)
    return prev.strftime("%Y%m%d")

def fetch_record_for_date(target_date_str):
    """
    Fetch sentiment data for a specific date.
    Uses SSE Composite Index (sh000001) as a proxy for market index.
    """
    today_str = target_date_str
    print(f"  Fetching data for {today_str}...")

    market_index = 0
    up_count = 0

    # 1. Market Index Proxy (Use SSE Index for consistency)
    try:
        index_df = ak.stock_zh_index_daily(symbol="sh000001")
        target_date_obj = datetime.datetime.strptime(today_str, "%Y%m%d").date()
        row = index_df[index_df['date'] == target_date_obj]

        if not row.empty:
            idx = row.index[0]
            if idx > 0:
                prev_close = index_df.iloc[idx-1]['close']
                curr_close = row.iloc[0]['close']
                pct_chg = ((curr_close - prev_close) / prev_close) * 100

                # Formula: 100 + (PctChg * 30)
                # Clamped between 10 and 200
                raw_index = 100 + (pct_chg * 30)
                market_index = max(10, min(200, raw_index))

                # Proxy up_count for UI
                up_count = int(market_index * 20)
                print(f"    Market Index (Proxy): {market_index:.2f} (SSE PctChg: {pct_chg:.2f}%)")
            else:
                market_index = 100
                up_count = 2000
    except Exception as e:
        print(f"    [Error] Market index block failed: {e}")

    # 2. Super Short Sentiment & Losing Money
    limit_up_count = 0
    bomb_count = None
    limit_down_count = None

    try:
        # Limit Up
        try:
            zt_df = ak.stock_zt_pool_em(date=today_str)
            limit_up_count = len(zt_df) if zt_df is not None else 0
        except Exception as e:
            print(f"    [Warning] Limit up fetch failed: {e}")

        # Bomb Count
        try:
            zb_df = ak.stock_zt_pool_zbgc_em(date=today_str)
            bomb_count = len(zb_df) if zb_df is not None else 0
        except Exception as e:
            print(f"    [Warning] Bomb count fetch failed: {e}")

        # Limit Down
        try:
            dt_df = ak.stock_zt_pool_dtgc_em(date=today_str)
            limit_down_count = len(dt_df) if dt_df is not None else 0
        except Exception as e:
            print(f"    [Warning] Limit down fetch failed: {e}")

        # Calculations
        super_short_sentiment = limit_up_count # Simplification for history

        has_losing_money_inputs = bomb_count is not None and limit_down_count is not None
        safe_bomb_count = bomb_count if bomb_count is not None else 0
        safe_limit_down_count = limit_down_count if limit_down_count is not None else 0

        total_touch_limit = safe_bomb_count + limit_up_count
        炸板率 = (safe_bomb_count / total_touch_limit) if total_touch_limit > 0 else 0

        # Losing money effect formula
        losing_money_effect = ((炸板率 * 100) + (safe_limit_down_count * 2)) if has_losing_money_inputs else None

        # If it's today, we could try to get more details, but keep it simple for now
        print(f"    Results: LimitUp={limit_up_count}, Bomb={bomb_count}, LimitDown={limit_down_count}")

    except Exception as e:
        print(f"    [Error] Sentiment/Losing money block failed: {e}")
        super_short_sentiment = 0
        losing_money_effect = 0

    return {
        "date": today_str,
        "market_index": round(market_index, 2),
        "super_short_sentiment": round(float(super_short_sentiment), 2),
        "losing_money_effect": round(float(losing_money_effect), 2) if losing_money_effect is not None else None,
        "details": {
            "limit_up_count": int(limit_up_count),
            "bomb_count": int(bomb_count) if bomb_count is not None else None,
            "limit_down_count": int(limit_down_count) if limit_down_count is not None else None,
            "up_count": int(up_count) if up_count > 0 else None
        }
    }

def update_sentiment_data(target_date_str=None):
    if target_date_str is None:
        target_date_str = get_trading_date()

    record = fetch_record_for_date(target_date_str)

    if record and record['market_index'] > 0:
        save_records([record])
        return True
    return False

def save_records(new_records):
    file_path = os.path.join(os.path.dirname(__file__), DATA_FILE)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    data = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                data = []

    for new_record in new_records:
        existing = False
        for i, item in enumerate(data):
            if item['date'] == new_record['date']:
                data[i] = new_record
                existing = True
                break
        if not existing:
            data.append(new_record)

    data.sort(key=lambda x: x['date'])

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Successfully saved records to {file_path}")

def load_records():
    file_path = os.path.join(os.path.dirname(__file__), DATA_FILE)
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

def get_trade_dates_until_today():
    trade_date_df = ak.tool_trade_date_hist_sina()
    trade_dates = trade_date_df['trade_date'].tolist()
    today = datetime.date.today()
    return [d for d in trade_dates if d <= today]

def find_missing_trade_dates(data):
    trade_dates = get_trade_dates_until_today()

    if not trade_dates:
        return []

    existing_dates = {item.get('date') for item in data if item.get('date')}

    if existing_dates:
        start_date = datetime.datetime.strptime(min(existing_dates), "%Y%m%d").date()
    else:
        start_date = trade_dates[-30]

    target_dates = [d for d in trade_dates if d >= start_date]
    return [d for d in target_dates if d.strftime("%Y%m%d") not in existing_dates]

def fill_missing_records(max_records=None):
    data = load_records()
    missing_dates = find_missing_trade_dates(data)

    if max_records is not None:
        missing_dates = missing_dates[:max_records]

    if not missing_dates:
        print("No missing trading dates to update.")
        return

    print(f"Found {len(missing_dates)} missing trading dates.")

    all_new_records = []
    for date_obj in missing_dates:
        date_str = date_obj.strftime("%Y%m%d")
        record = fetch_record_for_date(date_str)
        if record and record['market_index'] > 0:
            all_new_records.append(record)
        time.sleep(REQUEST_DELAY_SECONDS)

    if all_new_records:
        save_records(all_new_records)

def batch_update(days=30):
    print(f"Starting batch update for last {days} days...")
    try:
        trade_date_df = ak.tool_trade_date_hist_sina()
        trade_dates = trade_date_df['trade_date'].tolist()
        today = datetime.date.today()
        valid_dates = [d for d in trade_dates if d <= today]
        target_dates = valid_dates[-days:]

        all_new_records = []
        for date_obj in target_dates:
            date_str = date_obj.strftime("%Y%m%d")
            record = fetch_record_for_date(date_str)
            if record and record['market_index'] > 0:
                all_new_records.append(record)
            time.sleep(REQUEST_DELAY_SECONDS) # Be nice to API

        if all_new_records:
            save_records(all_new_records)

    except Exception as e:
        print(f"Error in batch update: {e}")

def update_date_range(start_date_str, end_date_str):
    print(f"Starting range update from {start_date_str} to {end_date_str}...")

    start_date = datetime.datetime.strptime(start_date_str, "%Y%m%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y%m%d").date()
    cursor = start_date
    all_new_records = []

    while cursor <= end_date:
        if cursor.weekday() < 5:
            date_str = cursor.strftime("%Y%m%d")
            record = fetch_record_for_date(date_str)
            if record and record['market_index'] > 0:
                all_new_records.append(record)
            time.sleep(REQUEST_DELAY_SECONDS)
        cursor += datetime.timedelta(days=1)

    if all_new_records:
        save_records(all_new_records)

def parse_args():
    parser = argparse.ArgumentParser(description="Update market sentiment data.")
    parser.add_argument("--date", help="Update a single date in YYYYMMDD format.")
    parser.add_argument("--from", dest="start_date", help="Start date in YYYYMMDD format.")
    parser.add_argument("--to", dest="end_date", help="End date in YYYYMMDD format.")
    parser.add_argument("--days", type=int, default=30, help="How many recent trading days to backfill.")
    parser.add_argument("--fill-missing", action="store_true", help="Fill missing trading dates in public/data.json.")
    parser.add_argument("--max-records", type=int, help="Limit how many missing records to fetch in one run.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    if args.date:
        update_sentiment_data(args.date)
    elif args.start_date and args.end_date:
        update_date_range(args.start_date, args.end_date)
    elif args.fill_missing:
        fill_missing_records(max_records=args.max_records)
    else:
        fill_missing_records(max_records=args.max_records)
