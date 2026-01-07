import sqlite3

def get_connection():
    return sqlite3.connect("trades.db", check_same_thread=False)

def create_table():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        pair TEXT,
        direction TEXT,
        entry REAL,
        stoploss REAL,
        takeprofit REAL,
        lot REAL
    )
    """)

    conn.commit()
    conn.close()
