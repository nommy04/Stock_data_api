import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time
from sqlalchemy import create_engine

# Step 1: Load S&P 500 Tickers
def load_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return df['Symbol'].str.replace('.', '-', regex=False).tolist()

# Step 2: Get stock data for a specific date
def fetch_stock_data(ticker, date):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=date, end=(pd.to_datetime(date) + timedelta(days=1)).strftime('%Y-%m-%d'))
        price = hist['Close'].iloc[0] if not hist.empty else None
        info = stock.info
        market_cap = info.get("marketCap")
        name = info.get("longName")
        sector=info.get("sector")
        industry=info.get("sector")
        return {
            "ticker": ticker,
            "name":name,
            "sector":sector,
            "industry":industry,
            "price": price,
            "market_cap": market_cap
            
        }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Step 3: Build top 100 list for a given date
def get_data_by_market_cap(tickers, date):
    results = []
    for i, ticker in enumerate(tickers):
        data = fetch_stock_data(ticker, date)
        if data and data["market_cap"]:
            results.append(data)
        time.sleep(0.5)  # To avoid rate limits
        print(f"[{i+1}/{len(tickers)}] Processed {ticker}")
    df = pd.DataFrame(results)
    df = df.dropna()
    # df = df.sort_values(by="market_cap", ascending=False).head(100)
    df["date"] = date
    return df

# Step 4: Store to SQLite
def save_to_sqlite(df, db_path="index_data.db"):
    engine = create_engine(f"sqlite:///{db_path}")
    df.to_sql("raw_stock_data", engine, if_exists="append", index=False)

# Step 5: Run for multiple days
def ingest_for_date_range(start_date: str, end_date: str):
    tickers = load_sp500_tickers()
    current_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    while current_date <= end_date:
        print(f"\nFetching data for {current_date.date()}")
        df = get_data_by_market_cap(tickers, current_date.strftime('%Y-%m-%d'))
        save_to_sqlite(df)
        current_date += timedelta(days=1)

# ===== Run It =====
if __name__ == "__main__":
    #can use dt.datetime.today and make it an automatic process
    # ingest_for_date_range((datetime.today()-timedelta(days=1)).strftime('%Y-%m-%d')
    #                       ,(datetime.today()).strftime('%Y-%m-%d'))
    ingest_for_date_range("2024-06-18", "2024-06-25")
