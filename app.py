from flask import Flask, render_template, request, redirect, url_for, flash, json, jsonify, Response
import database as db
import stock_api
import os
from collections import defaultdict
import requests
import yfinance as yf
import io
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'a_very_secret_key_that_should_be_changed'

if not os.path.exists(db.DB_FILE):
    db.create_tables()

# ... (calculate_portfolio function and other routes remain the same) ...

@app.route('/search', methods=['GET', 'POST'])
def search_stocks_api():
    stock_details = None
    price_history = None
    if request.method == 'POST':
        ticker = request.form['ticker'].strip().upper()
        if ticker:
            stock_details = stock_api.get_stock_details(ticker)
            # Also fetch price history for the chart
            price_history = stock_api.get_price_history(ticker)
            
            if not stock_details:
                flash(f"Could not find any data for the symbol '{ticker}'.", 'error')
        else:
            flash("Please enter a ticker symbol to search.", "error")
            
    return render_template('search.html', 
                           stock=stock_details, 
                           price_history=price_history)

# ... (The rest of your app.py file) ...
# For brevity, I am omitting the rest of the routes which are unchanged.
# Make sure to include the full app.py code from the previous version for the routes below this comment.
def calculate_portfolio():
    transactions = db.get_all_transactions()
    transactions.reverse() 
    holdings = defaultdict(lambda: {'shares': 0, 'total_cost': 0, 'realized_pl': 0})
    for trans in transactions:
        symbol = trans['symbol']
        if trans['transaction_type'] == 'BUY':
            holdings[symbol]['shares'] += trans['shares']
            holdings[symbol]['total_cost'] += (trans['shares'] * trans['price_per_share']) + trans['transaction_cost'] + trans['tax_cost']
        elif trans['transaction_type'] == 'SELL':
            if holdings[symbol]['shares'] < trans['shares']: continue
            avg_cost = holdings[symbol]['total_cost'] / holdings[symbol]['shares']
            cost_of_sold = trans['shares'] * avg_cost
            proceeds = (trans['shares'] * trans['price_per_share']) - trans['transaction_cost'] - trans['tax_cost']
            holdings[symbol]['realized_pl'] += proceeds - cost_of_sold
            holdings[symbol]['shares'] -= trans['shares']
            holdings[symbol]['total_cost'] -= cost_of_sold
        elif trans['transaction_type'] == 'DIVIDEND':
            holdings[symbol]['realized_pl'] += (trans['shares'] * trans['price_per_share']) - trans['tax_cost']
    portfolio_view = []
    total_value = sum(data['shares'] * (stock_api.get_stock_data(symbol)['current_price'] if stock_api.get_stock_data(symbol) else 0) for symbol, data in holdings.items())
    for symbol, data in holdings.items():
        if data['shares'] <= 1e-5: continue
        live_data = stock_api.get_stock_data(symbol)
        current_price = live_data['current_price'] if live_data else 0
        current_value = data['shares'] * current_price
        cost_basis = data['total_cost']
        unrealized_pl = current_value - cost_basis
        total_pl = unrealized_pl + data['realized_pl']
        portfolio_view.append({
            'symbol': symbol, 'name': live_data['company_name'] if live_data else symbol,
            'shares': data['shares'], 'avg_cost_per_share': cost_basis / data['shares'] if data['shares'] > 0 else 0,
            'current_price': current_price, 'current_value': current_value,
            'total_pl': total_pl, 'latest_transaction_id': db.get_latest_transaction_id_for_symbol(symbol),
            'allocation': (current_value / total_value * 100) if total_value > 0 else 0,
            'pl_percentage': (total_pl / cost_basis * 100) if cost_basis > 0 else 0
        })
    portfolio_view.sort(key=lambda x: x['allocation'], reverse=True)
    return portfolio_view

@app.route('/')
def index():
    portfolio = calculate_portfolio()
    summary = {'total_value': sum(s['current_value'] for s in portfolio), 'total_pl': sum(s['total_pl'] for s in portfolio)}
    return render_template('index.html', portfolio=portfolio, summary=summary,
                           chart_labels=json.dumps([s['symbol'] for s in portfolio if s['current_value'] > 0]), 
                           chart_values=json.dumps([s['current_value'] for s in portfolio if s['current_value'] > 0]))

@app.route('/dividends')
def dividends_list():
    dividends = db.get_all_dividends()
    total_income = sum(d['shares'] * d['price_per_share'] - d['tax_cost'] for d in dividends)
    monthly_income = defaultdict(float)
    for div in dividends:
        monthly_income[div['transaction_date'][:7]] += (div['shares'] * div['price_per_share']) - div['tax_cost']
    sorted_months = sorted(monthly_income.keys())
    return render_template('dividends.html', dividends=dividends, total_income=total_income,
                           chart_labels=json.dumps([datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in sorted_months]),
                           chart_values=json.dumps([monthly_income[m] for m in sorted_months]))

@app.route('/import_dividends', methods=['POST'])
def import_dividends():
    all_symbols = db.get_unique_symbols()
    all_transactions = db.get_all_transactions()
    existing_dividends = {(d['symbol'], d['transaction_date']) for d in all_transactions if d['transaction_type'] == 'DIVIDEND'}
    imported_count = 0
    for symbol in all_symbols:
        try:
            ticker = yf.Ticker(symbol)
            api_dividends = ticker.dividends.loc[str(datetime.now().year - 5):]
            if api_dividends.empty: continue
            for date, amount in api_dividends.items():
                div_date_str = date.strftime('%Y-%m-%d')
                if (symbol, div_date_str) in existing_dividends: continue
                shares_owned = 0
                for trans in all_transactions:
                    if trans['symbol'] == symbol and trans['transaction_date'] < div_date_str:
                        if trans['transaction_type'] == 'BUY': shares_owned += trans['shares']
                        elif trans['transaction_type'] == 'SELL': shares_owned -= trans['shares']
                if shares_owned > 0:
                    db.add_transaction(symbol, 'DIVIDEND', shares_owned, amount, 0, 0, div_date_str, None, "Auto-imported")
                    imported_count += 1
        except Exception as e:
            print(f"Could not process dividends for {symbol}: {e}")
    if imported_count > 0: flash(f'Successfully imported {imported_count} new dividend payments!', 'success')
    else: flash('No new dividend payments to import.', 'info')
    return redirect(url_for('dividends_list'))

@app.route('/export_csv')
def export_csv():
    transactions = db.get_all_transactions()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Symbol', 'Type', 'Shares', 'Price', 'Cost', 'Tax', 'Group', 'Notes'])
    for trans in transactions:
        writer.writerow([trans['id'], trans['transaction_date'], trans['symbol'], trans['transaction_type'],
                         trans['shares'], trans['price_per_share'], trans['transaction_cost'],
                         trans['tax_cost'], trans['group_name'], trans['notes']])
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=transactions.csv"})

@app.route('/transactions')
def transaction_list():
    filter_symbol = request.args.get('symbol', None)
    transactions = db.get_transactions_by_symbol(filter_symbol) if filter_symbol else db.get_all_transactions()
    return render_template('transactions.html', transactions=transactions, filter_symbol=filter_symbol)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        try:
            symbol, trans_type, date = request.form.get('symbol'), request.form.get('trans_type'), request.form.get('date')
            shares_str, price_str = request.form.get('shares'), request.form.get('price')
            if not all([symbol, trans_type, date]):
                flash('Symbol, Transaction Type, and Date are required.', 'error'); return redirect(url_for('add_transaction'))
            if trans_type in ['BUY', 'SELL', 'DIVIDEND']:
                if not shares_str or not price_str:
                    flash('For this transaction type, Shares and Price are required.', 'error'); return redirect(url_for('add_transaction'))
                shares, price = float(shares_str), float(price_str)
                if shares <= 0:
                    flash('Number of shares must be a positive number.', 'error'); return redirect(url_for('add_transaction'))
            else:
                shares, price = (float(shares_str) if shares_str else 0), (float(price_str) if price_str else 0)
            cost, tax = float(request.form.get('cost', '0') or '0'), float(request.form.get('tax', '0') or '0')
            group, notes = request.form.get('group'), request.form.get('notes')
            db.add_transaction(symbol.strip().upper(), trans_type, shares, price, cost, tax, date, group, notes)
            flash(f"Successfully added {trans_type} transaction for {symbol}.", 'success')
            return redirect(url_for('transaction_list'))
        except ValueError:
            flash('Invalid number format. Please check shares, price, and cost fields.', 'error'); return redirect(url_for('add_transaction'))
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", "error"); return redirect(url_for('add_transaction'))
    return render_template('add_transaction.html')

@app.route('/edit/<int:trans_id>', methods=['GET', 'POST'])
def edit_transaction(trans_id):
    transaction = db.get_transaction(trans_id)
    if request.method == 'POST':
        try:
            db.update_transaction(trans_id, request.form['symbol'], request.form['trans_type'],
                                  float(request.form.get('shares', 0)), float(request.form.get('price', 0)),
                                  float(request.form.get('cost', 0)), float(request.form.get('tax', 0)),
                                  request.form['date'], request.form.get('group'), request.form.get('notes'))
            flash("Transaction updated successfully!", "success"); return redirect(url_for('transaction_list'))
        except Exception as e:
            flash(f"Error updating transaction: {e}", "error")
    return render_template('edit_transaction.html', trans=transaction)

@app.route('/delete_stock/<string:symbol>', methods=['POST'])
def delete_stock_holding(symbol):
    db.delete_all_transactions_for_symbol(symbol)
    flash(f"Successfully removed all records for {symbol} from your portfolio.", "success")
    return redirect(url_for('index'))

@app.route('/delete/<int:trans_id>', methods=['POST'])
def delete_transaction(trans_id):
    db.delete_transaction(trans_id); flash("Transaction deleted successfully.", "success")
    return redirect(url_for('transaction_list'))

@app.route('/api/search-tickers')
def api_search_tickers():
    query = request.args.get('q', '').strip()
    if not query: return jsonify([])
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status(); data = response.json()
        results = [{'symbol': item.get('symbol'), 'name': item.get('longname', item.get('shortname', '')), 'group': item.get('industry', '')}
                   for item in data.get('quotes', []) if 'symbol' in item and item.get('isYahooFinance')]
        return jsonify(results)
    except requests.exceptions.RequestException as e:
        print(f"API search error: {e}"); return jsonify({'error': str(e)}), 500

@app.route('/api/get-historical-price')
def api_get_historical_price():
    ticker_symbol, date_str = request.args.get('ticker'), request.args.get('date')
    if not ticker_symbol or not date_str: return jsonify({'error': 'Ticker and date are required'}), 400
    try:
        ticker = yf.Ticker(ticker_symbol); hist = ticker.history(start=date_str, end=date_str)
        if hist.empty:
            hist = ticker.history(end=date_str, period="5d")
            if hist.empty: return jsonify({'error': 'No historical data found'}), 404
            price = hist['Close'].iloc[-1]
        else: price = hist['Close'].iloc[0]
        return jsonify({'price': price})
    except Exception as e:
        print(f"Historical price error: {e}"); return jsonify({'error': 'Could not fetch price.'}), 500
        
@app.route('/api/get-dividend-info')
def api_get_dividend_info():
    ticker_symbol, date_str = request.args.get('ticker'), request.args.get('date')
    if not ticker_symbol or not date_str: return jsonify({'error': 'Ticker and date are required'}), 400
    try:
        ticker = yf.Ticker(ticker_symbol)
        dividends = ticker.dividends.loc[date_str.split('-')[0]]
        if dividends.empty: return jsonify({'error': 'No dividend found for that year.'}), 404
        closest_dividend = dividends.iloc[dividends.index.get_loc(date_str, method='nearest')]
        return jsonify({'dividend_per_share': closest_dividend})
    except Exception as e:
        print(f"Dividend lookup error: {e}"); return jsonify({'error': 'Could not fetch dividend info.'}), 500
        
if __name__ == '__main__':
    app.run(debug=True)
