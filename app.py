from fastapi import FastAPI,HTTPException
from fastapi.responses import JSONResponse,StreamingResponse
from pydantic import BaseModel
from datetime import datetime,timedelta
import sqlite3
import uvicorn
from typing import Optional
import redis
import pandas as pd
import io
import xlsxwriter
import os

#function imports
from sql_codes import update_index_composition,update_index_performance


redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
db_path = os.environ.get("DATABASE_URL", "index_data.db")

r = redis.Redis(host='localhost', port=6379, db=0)


app=FastAPI()


class IndexBuildRequest(BaseModel):
    start_date: str
    end_date: Optional[str] = None
#Post requests
#1 Buliding the index compositions and performance
@app.post("/build-index")
def build_index(request:IndexBuildRequest):
    try:
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date() if request.end_date else start_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    
    # Generate Redis cache key
    cache_key = f"index_built:{start_date}:{end_date}"

    if r.exists(cache_key):
        return {"message": f"Index already built for {start_date} to {end_date}"}
    
    conn=sqlite3.connect('index_data.db')

    try:
        current_date = start_date
        while current_date <= end_date:
            update_index_composition(conn, str(current_date))   
            current_date += timedelta(days=1)
        
        update_index_performance(conn,str(start_date),str(end_date))
        conn.commit()

        r.setex(cache_key,86400, "true")       #expires in 1day
    finally:
        conn.close()

    return {"message": f"Index building triggered from {start_date} to {end_date}"}

#exporting the data to excel
@app.post("/export-data")
def export_data(
    start_date: str = None,
    end_date: str = None
):
    # Connect to database
    conn = sqlite3.connect('index_data.db')

    # Set defaults if dates are not provided
    if not start_date:
        start_date = pd.read_sql_query("SELECT MIN(date) FROM index_performance", conn).iloc[0, 0]
    if not end_date:
        end_date = pd.read_sql_query("SELECT MAX(date) FROM index_performance", conn).iloc[0, 0]

    # 1. Index Performance
    perf = pd.read_sql_query(
        "SELECT date, index_value, normalized_index_value FROM index_performance WHERE date BETWEEN ? AND ? ORDER BY date",
        conn, params=(start_date, end_date)
    )
    perf['index_value'] = perf['index_value'].round(4)
    perf['normalized_index_value'] = perf['normalized_index_value'].round(2)

    # 2. Daily Compositions
    comp = pd.read_sql_query(
        "SELECT date, ticker, price, market_cap, weight FROM daily_index_composition WHERE date BETWEEN ? AND ? ORDER BY date, market_cap DESC",
        conn, params=(start_date, end_date)
    )
    comp['price'] = pd.to_numeric(comp['price']).round(2)
    comp['market_cap'] = pd.to_numeric(comp['market_cap']).round(0)
    comp['weight'] = pd.to_numeric(comp['weight']).round(2)

    # 3. Composition Changes (in memory calculation)
    df = pd.read_sql_query(
        "SELECT date, ticker FROM daily_index_composition WHERE date BETWEEN ? AND ? ORDER BY date, ticker",
        conn, params=(start_date, end_date)
    )
    conn.close()

    daily = {d: set(g['ticker']) for d, g in df.groupby('date')}
    sorted_dates = sorted(daily)
    changes_result = []
    last = None
    for d in sorted_dates:
        current = daily[d]
        if last is not None:
            entered = sorted(list(current - last))
            exited = sorted(list(last - current))
            if entered or exited:
                changes_result.append({
                    "date": d,
                    "entered": ','.join(entered),
                    "exited": ','.join(exited)
                })
        last = current
    changes = pd.DataFrame(changes_result)

    # Write to Excel in memory

    #creates and in memory binary file
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        perf.to_excel(writer, sheet_name="IndexPerformance", index=False)
        comp.to_excel(writer, sheet_name="DailyComposition", index=False)
        changes.to_excel(writer, sheet_name="CompositionChanges", index=False)

        #Format columns
        workbook = writer.book
        if not comp.empty:
            ws = writer.sheets['DailyComposition']
            ws.set_column('C:C', 12)  # price
            ws.set_column('D:D', 20)  # market_cap
            ws.set_column('E:E', 8)   # weight
        if not perf.empty:
            ws = writer.sheets['IndexPerformance']
            ws.set_column('B:C', 20)  # index values
    #moving the memory pointer back to 0
    output.seek(0)

    headers = {
        "Content-Disposition": f"attachment; filename=index_data_export.xlsx"
    }

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

#Get  requests
#index performance for range of date
@app.get("/index-performance")
def get_index_performance(start_date: str, end_date: str):
    cache_key = f"index_performance:{start_date}:{end_date}"
    cached = r.get(cache_key)
    if cached:
        return JSONResponse(content=eval(cached.decode()))

    conn = sqlite3.connect('index_data.db')
    query = """
        SELECT date, normalized_index_value
        FROM index_performance
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="No data in range")
    df['daily_return'] = df['normalized_index_value'].pct_change().fillna(0).round(4)  # e.g., 0.0123 for 1.23%
    df['cumulative_return'] = ((1 + df['daily_return']).cumprod() - 1).round(4)


    result = df.to_dict(orient="records")
    for row in result:
        row['daily_return'] = round(row['daily_return'], 4)
        row['cumulative_return'] = round(row['cumulative_return'], 4)
    # cache 1 hr
    r.setex(cache_key, 3600, str(result))
    return result

#index composition for a particular date

@app.get("/index-composition")
def get_index_composition(date: str):
    cache_key = f"index_composition:{date}"
    cached = r.get(cache_key)
    if cached:
        return JSONResponse(content=eval(cached.decode()))

    conn = sqlite3.connect('index_data.db')
    query = """
        SELECT ticker, price, market_cap, weight
        FROM daily_index_composition
        WHERE date = ?
        ORDER BY market_cap DESC
        LIMIT 100
    """
    df = pd.read_sql_query(query, conn, params=(date,))
    conn.close()

    if df.empty:
        raise HTTPException(status_code=404, detail="No data for this date")

    result = df.to_dict(orient="records")

    # Round for clean output (optional)
    for row in result:
        row['price'] = round(float(row['price']), 2)
        row['market_cap'] = float(row['market_cap'])
        row['weight'] = round(float(row['weight']), 2)


    r.setex(cache_key, 3600, str(result))
    return result

# composition change 

@app.get("/composition-changes")
def get_composition_changes(start_date: str, end_date: str):
    cache_key = f"composition_changes:{start_date}:{end_date}"
    cached = r.get(cache_key)
    if cached:
        return JSONResponse(content=eval(cached.decode()))

    # Query the DB for index compositions in the date range.
    conn = sqlite3.connect('index_data.db')
    query = """
        SELECT date, ticker
        FROM daily_index_composition
        WHERE date BETWEEN ? AND ?
        ORDER BY date, ticker
    """
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="No composition data in range")

    # Building daily sets of tickers
    daily = {d: set(g['ticker']) for d, g in df.groupby('date')}
    sorted_dates = sorted(daily)
    result = []

    last = None
    for d in sorted_dates:
        current = daily[d]
        if last is not None:
            entered = sorted(list(current - last))
            exited = sorted(list(last - current))
            if entered or exited:
                result.append({
                    "date": d,
                    "entered": entered,
                    "exited": exited
                })
        last = current

    r.setex(cache_key, 3600, str(result))
    return result


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
