import yfinance as yf
from datetime import datetime

def get_stock_data(symbol):
    """
    Fetches the latest stock data for a given symbol using yfinance.
    Used for quick price checks.
    """
    try:
        stock = yf.Ticker(symbol)
        data = stock.fast_info
        
        if 'lastPrice' not in data or data['lastPrice'] is None:
            return None

        return {
            'current_price': data.get('lastPrice'),
            'company_name': data.get('longName', symbol)
        }
    except Exception as e:
        print(f"An error occurred while fetching data for {symbol}: {e}")
        return None

def get_price_history(symbol):
    """Fetches historical price data for the last year for charting."""
    try:
        stock = yf.Ticker(symbol)
        # Fetch data for the past 1 year
        hist = stock.history(period="1y")
        if hist.empty:
            return None
        # Format the data for Chart.js
        hist.index = hist.index.strftime('%Y-%m-%d')
        return {
            'dates': list(hist.index),
            'prices': list(hist['Close'])
        }
    except Exception as e:
        print(f"An error occurred while fetching price history for {symbol}: {e}")
        return None

def get_stock_details(symbol):
    """
    Fetches a comprehensive set of details for a given stock symbol.
    Now includes more business and financial metrics.
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        if info.get('regularMarketPrice') is None and info.get('currentPrice') is None:
            return None
        
        def format_large_number(n):
            if not n: return 'N/A'
            if n > 1e12: return f'${n/1e12:.2f}T'
            if n > 1e9: return f'${n/1e9:.2f}B'
            if n > 1e6: return f'${n/1e6:.2f}M'
            return f'${n:,.0f}'

        ex_div_date_timestamp = info.get('exDividendDate')
        ex_div_date = datetime.fromtimestamp(ex_div_date_timestamp).strftime('%Y-%m-%d') if ex_div_date_timestamp else None

        details = {
            'symbol': info.get('symbol'),
            'longName': info.get('longName', 'N/A'),
            'currentPrice': info.get('currentPrice', info.get('regularMarketPrice')),
            'dayHigh': info.get('dayHigh'),
            'dayLow': info.get('dayLow'),
            'open': info.get('open'),
            'previousClose': info.get('previousClose'),
            'volume': info.get('volume'),
            'marketCap': format_large_number(info.get('marketCap')),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
            'summary': info.get('longBusinessSummary', 'No summary available.'),
            'dividendYield': info.get('dividendYield'),
            'lastDividendValue': info.get('lastDividendValue'),
            'exDividendDate': ex_div_date,
            'trailingPE': info.get('trailingPE'),
            'profitMargins': info.get('profitMargins'),
            'totalRevenue': format_large_number(info.get('totalRevenue')),
            'freeCashflow': format_large_number(info.get('freeCashflow'))
        }
        return details
    except Exception as e:
        print(f"An error occurred while fetching details for {symbol}: {e}")
        return None
