import sqlite3
import os

DB_FILE = "portfolio.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            shares REAL,
            price_per_share REAL,
            transaction_cost REAL DEFAULT 0,
            tax_cost REAL DEFAULT 0,
            transaction_date TEXT NOT NULL,
            group_name TEXT,
            notes TEXT
        );
    ''')
    conn.commit()
    conn.close()
    print("Database and 'transactions' table are ready.")

def get_unique_symbols():
    """Gets a list of all unique stock symbols from the transactions table."""
    conn = get_db_connection()
    symbols = conn.execute("SELECT DISTINCT symbol FROM transactions").fetchall()
    conn.close()
    return [s['symbol'] for s in symbols]

def add_transaction(symbol, trans_type, shares, price, cost, tax, date, group, notes):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO transactions (symbol, transaction_type, shares, price_per_share, transaction_cost, tax_cost, transaction_date, group_name, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (symbol.upper(), trans_type, shares, price, cost, tax, date, group, notes)
    )
    conn.commit()
    conn.close()

def get_all_transactions():
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM transactions ORDER BY transaction_date DESC, id DESC').fetchall()
    conn.close()
    return transactions

def get_all_dividends():
    """Retrieves all dividend transactions from the database."""
    conn = get_db_connection()
    dividends = conn.execute("SELECT * FROM transactions WHERE transaction_type = 'DIVIDEND' ORDER BY transaction_date DESC").fetchall()
    conn.close()
    return dividends

def get_transactions_by_symbol(symbol):
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM transactions WHERE symbol = ? ORDER BY transaction_date DESC, id DESC', (symbol.upper(),)).fetchall()
    conn.close()
    return transactions

def get_transaction(transaction_id):
    conn = get_db_connection()
    transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
    conn.close()
    return transaction

def get_latest_transaction_id_for_symbol(symbol):
    conn = get_db_connection()
    result = conn.execute('SELECT id FROM transactions WHERE symbol = ? ORDER BY transaction_date DESC, id DESC LIMIT 1', (symbol.upper(),)).fetchone()
    conn.close()
    return result['id'] if result else None

def update_transaction(trans_id, symbol, trans_type, shares, price, cost, tax, date, group, notes):
    conn = get_db_connection()
    conn.execute(
        '''UPDATE transactions SET symbol=?, transaction_type=?, shares=?, price_per_share=?, transaction_cost=?, tax_cost=?, transaction_date=?, group_name=?, notes=? WHERE id = ?''',
        (symbol.upper(), trans_type, shares, price, cost, tax, date, group, notes, trans_id)
    )
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def delete_all_transactions_for_symbol(symbol):
    conn = get_db_connection()
    conn.execute('DELETE FROM transactions WHERE symbol = ?', (symbol.upper(),))
    conn.commit()
    conn.close()
    print(f"Deleted all transactions for stock: {symbol}")

if __name__ == '__main__':
    create_tables()
