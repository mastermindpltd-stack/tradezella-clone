import sqlite3

DB_NAME = "trades.db"

# -------------------------------------------------
# GET CONNECTION
# -------------------------------------------------
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# -------------------------------------------------
# CREATE TABLE (MAIN)
# -------------------------------------------------
def create_table():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,

        pair TEXT,
        direction TEXT,

        entry REAL,
        stoploss REAL,
        takeprofit REAL,
        lot REAL,

        screenshot TEXT,
        notes TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------
# INSERT TRADE (MANUAL / CSV / WEBHOOK)
# -------------------------------------------------
def insert_trade(
    username,
    pair,
    direction,
    entry,
    stoploss,
    takeprofit,
    lot,
    screenshot=None,
    notes=None
):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO trades
        (username, pair, direction, entry, stoploss, takeprofit, lot, screenshot, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            pair,
            direction,
            entry,
            stoploss,
            takeprofit,
            lot,
            screenshot,
            notes
        )
    )
    conn.commit()
    conn.close()


# -------------------------------------------------
# UPDATE SCREENSHOT & NOTES
# -------------------------------------------------
def update_trade_review(trade_id, screenshot_path, notes):
    conn = get_connection()
    conn.execute(
        """
        UPDATE trades
        SET screenshot = ?, notes = ?
        WHERE id = ?
        """,
        (screenshot_path, notes, trade_id)
    )
    conn.commit()
    conn.close()


# -------------------------------------------------
# GET USER TRADES
# -------------------------------------------------
def get_user_trades(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM trades WHERE username = ? ORDER BY created_at",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


# -------------------------------------------------
# DELETE TRADE (OPTIONAL)
# -------------------------------------------------
def delete_trade(trade_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM trades WHERE id = ?",
        (trade_id,)
    )
    conn.commit()
    conn.close()
