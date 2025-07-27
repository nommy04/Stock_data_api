import sqlite3
#updates the daily_index_composition table by pulling data from the raw_stock_data table
def update_index_composition(conn, target_date: str):
    
    cursor = conn.cursor()
     
    # ❗ Step 0: Delete existing records for that date (if any)
    cursor.execute("""
        DELETE FROM daily_index_composition
        WHERE date = ?
    """, (target_date,))    

    # Step 1: Select top 100 stocks by market cap for the given date
    cursor.execute("""
        SELECT ticker, price, market_cap
        FROM raw_stock_data
        WHERE date = ?
        AND market_cap IS NOT NULL
        ORDER BY market_cap DESC
        LIMIT 100
    """,(target_date,))
    top_stocks = cursor.fetchall()

    # Step 2: Prepare rows with equal weights
    index_rows = [(target_date, ticker, price, market_cap, 0.01) for (ticker, price, market_cap) in top_stocks]

    # Step 3: Insert into daily_index_composition
    cursor.executemany("""
        INSERT INTO daily_index_composition (date, ticker, price, market_cap, weight)
        VALUES (?, ?, ?, ?, ?)
    """, index_rows)

    conn.commit()

#used to create the index from the base date
def get_base_prices(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date FROM daily_index_composition ORDER BY date LIMIT 1
    """)
    base_date = cursor.fetchone()[0]

    cursor.execute("""
        SELECT ticker, price FROM daily_index_composition
        WHERE date = ?
    """, (base_date,))
    
    base_prices = {row[0]: row[1] for row in cursor.fetchall()}
    return base_date, base_prices

#update the index performance table

def update_index_performance(conn, start_date, end_date):
    base_date, base_prices = get_base_prices(conn)
    
    cursor = conn.cursor()
    
    
     #  Delete existing records for that date range
    cursor.execute("""
        DELETE FROM index_performance
        WHERE date BETWEEN ? AND ?
    """, (start_date, end_date))

    cursor.execute("""
        SELECT DISTINCT date FROM daily_index_composition
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    """, (start_date,end_date,))
    dates = [row[0] for row in cursor.fetchall()]

    performance_data = []

    for date in dates:
        cursor.execute("""
            SELECT ticker, price, weight
            FROM daily_index_composition
            WHERE date = ?
        """, (date,))
        rows = cursor.fetchall()

        index_value = 0.0
        for ticker, price, weight in rows:
            base_price = base_prices.get(ticker)
            if base_price:
                weighted_return = (float(price) * float(weight)) / float(base_price)
                index_value += weighted_return

        performance_data.append((date, index_value))
    

    cursor.execute("""
        SELECT index_value FROM index_performance
        WHERE date = ?
    """, (base_date,))
    base_index_row = cursor.fetchone()
    print("base_index_row####",base_index_row)
    # If no index_value exists for base_date, use from performance_data (first computation)
    if base_index_row:
        base_index = base_index_row[0]
    else:
        # fallback: recalculate base index if not yet present
        base_index = performance_data[0][1]
    
    
    normalized_data = [(date, idx_val, idx_val *100/base_index) for date, idx_val in performance_data]

    # Insert into index_performance table
    cursor.executemany("""
        INSERT OR REPLACE INTO index_performance (date, index_value, normalized_index_value)
        VALUES (?, ?, ?)
    """, normalized_data)

    conn.commit()

