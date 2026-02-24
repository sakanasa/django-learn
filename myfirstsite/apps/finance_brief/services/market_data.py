import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

INDICES = [
    {'symbol': '^GSPC',  'name': 'S&P 500',      'category': 'index', 'flag': '🇺🇸'},
    {'symbol': '^IXIC',  'name': 'NASDAQ',        'category': 'index', 'flag': '🇺🇸'},
    {'symbol': '^DJI',   'name': '道瓊工業',       'category': 'index', 'flag': '🇺🇸'},
    {'symbol': '^SOX',   'name': '費城半導體',      'category': 'index', 'flag': '🇺🇸'},
    {'symbol': '^TWII',  'name': '台灣加權',        'category': 'index', 'flag': '🇹🇼'},
    {'symbol': '^N225',  'name': '日經 225',        'category': 'index', 'flag': '🇯🇵'},
    {'symbol': '^HSI',   'name': '恆生指數',        'category': 'index', 'flag': '🇭🇰'},
]

FX = [
    {'symbol': 'TWD=X',    'name': 'USD/TWD', 'base': 'USD', 'quote': 'TWD'},
    {'symbol': 'EURUSD=X', 'name': 'EUR/USD', 'base': 'EUR', 'quote': 'USD'},
    {'symbol': 'JPY=X',    'name': 'USD/JPY', 'base': 'USD', 'quote': 'JPY'},
]

COMMODITIES = [
    {'symbol': 'GC=F',    'name': '黃金',      'unit': 'USD/oz'},
    {'symbol': 'CL=F',    'name': 'WTI 原油',  'unit': 'USD/bbl'},
    {'symbol': 'BTC-USD', 'name': 'Bitcoin',  'unit': 'USD'},
]


def _fetch_ticker(info):
    """Fetch a single ticker using yfinance (last 2 trading days for change calculation)."""
    symbol = info['symbol']
    try:
        ticker = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # buffer for weekends/holidays
        hist = ticker.history(
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
        )

        if hist.empty:
            return None

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]

        current_price = float(latest['Close'])
        prev_close = float(prev['Close'])
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

        result = dict(info)
        result.update({
            'price': round(current_price, 4),
            'change': round(change, 4),
            'change_pct': round(change_pct, 2),
            'prev_close': round(prev_close, 4),
            'last_updated': hist.index[-1].strftime('%Y-%m-%d'),
        })
        return result
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def get_all_market_data():
    """Fetch all indices, FX, and commodities concurrently.

    Returns:
        dict with keys 'indices', 'fx', 'commodities'
    """
    all_tickers = (
        [(item, 'index') for item in INDICES] +
        [(item, 'fx') for item in FX] +
        [(item, 'commodity') for item in COMMODITIES]
    )

    results = {'indices': [], 'fx': [], 'commodities': []}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_ticker, item): (item, category)
                   for item, category in all_tickers}
        for future in as_completed(futures):
            item, category = futures[future]
            result = future.result()
            if result:
                if category == 'index':
                    results['indices'].append(result)
                elif category == 'fx':
                    results['fx'].append(result)
                else:
                    results['commodities'].append(result)

    # Preserve original order
    def sort_by_original(lst, originals):
        order = {item['symbol']: i for i, item in enumerate(originals)}
        lst.sort(key=lambda x: order.get(x['symbol'], 999))

    sort_by_original(results['indices'], INDICES)
    sort_by_original(results['fx'], FX)
    sort_by_original(results['commodities'], COMMODITIES)

    return results
