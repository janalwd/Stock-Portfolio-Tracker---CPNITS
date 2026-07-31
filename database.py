import sqlite3
from flask import session

DB_FILE = "portfolio.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def _user_id():
    user_id = session.get("user_id")
    if not user_id:
        raise RuntimeError("Login required")
    return user_id


def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            shares REAL,
            price_per_share REAL,
            transaction_cost REAL DEFAULT 0,
            tax_cost REAL DEFAULT 0,
            transaction_date TEXT NOT NULL,
            group_name TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


def create_user(username, password_hash):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username.strip().lower(), password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username.strip().lower(),),
    ).fetchone()
    conn.close()
    return user


def get_unique_symbols():
    conn = get_db_connection()
    symbols = conn.execute(
        "SELECT DISTINCT symbol FROM transactions WHERE user_id = ?",
        (_user_id(),),
    ).fetchall()
    conn.close()
    return [s["symbol"] for s in symbols]


def add_transaction(symbol, trans_type, shares, price, cost, tax, date, group, notes):
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO transactions
           (user_id, symbol, transaction_type, shares, price_per_share,
            transaction_cost, tax_cost, transaction_date, group_name, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (_user_id(), symbol.upper(), trans_type, shares, price, cost, tax, date, group, notes),
    )
    conn.commit()
    conn.close()


def get_all_transactions():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY transaction_date DESC, id DESC",
        (_user_id(),),
    ).fetchall()
    conn.close()
    return rows


def get_all_dividends():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND transaction_type = 'DIVIDEND' ORDER BY transaction_date DESC",
        (_user_id(),),
    ).fetchall()
    conn.close()
    return rows


def get_transactions_by_symbol(symbol):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? AND symbol = ? ORDER BY transaction_date DESC, id DESC",
        (_user_id(), symbol.upper()),
    ).fetchall()
    conn.close()
    return rows


def get_transaction(transaction_id):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, _user_id()),
    ).fetchone()
    conn.close()
    return row


def get_latest_transaction_id_for_symbol(symbol):
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id FROM transactions WHERE user_id = ? AND symbol = ? ORDER BY transaction_date DESC, id DESC LIMIT 1",
        (_user_id(), symbol.upper()),
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def update_transaction(trans_id, symbol, trans_type, shares, price, cost, tax, date, group, notes):
    conn = get_db_connection()
    conn.execute(
        '''UPDATE transactions
           SET symbol=?, transaction_type=?, shares=?, price_per_share=?,
               transaction_cost=?, tax_cost=?, transaction_date=?, group_name=?, notes=?
           WHERE id=? AND user_id=?''',
        (symbol.upper(), trans_type, shares, price, cost, tax, date, group, notes, trans_id, _user_id()),
    )
    conn.commit()
    conn.close()


def delete_transaction(transaction_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, _user_id()),
    )
    conn.commit()
    conn.close()


def delete_all_transactions_for_symbol(symbol):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM transactions WHERE symbol = ? AND user_id = ?",
        (symbol.upper(), _user_id()),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
