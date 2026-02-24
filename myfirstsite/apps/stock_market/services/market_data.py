import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Index definitions
INDICES = [
    {'symbol': '^GSPC',  'name_zh': 'S&P 500',      'name_en': 'S&P 500',           'flag': '🇺🇸'},
    {'symbol': '^DJI',   'name_zh': '道瓊工業指數',   'name_en': 'Dow Jones',          'flag': '🇺🇸'},
    {'symbol': '^IXIC',  'name_zh': 'NASDAQ 綜合',   'name_en': 'NASDAQ Composite',   'flag': '🇺🇸'},
    {'symbol': '^SOX',   'name_zh': '費城半導體指數',  'name_en': 'PHLX Semiconductor', 'flag': '🇺🇸'},
    {'symbol': '^TWII',  'name_zh': '台灣加權指數',    'name_en': 'TAIEX',             'flag': '🇹🇼'},
]


def _fetch_single_index(index_info):
    """Fetch data for a single index using yfinance."""
    symbol = index_info['symbol']
    try:
        ticker = yf.Ticker(symbol)

        # Get 30-day history for the sparkline chart
        end_date = datetime.now()
        start_date = end_date - timedelta(days=45)  # extra buffer for weekends/holidays
        hist = ticker.history(start=start_date.strftime('%Y-%m-%d'),
                              end=end_date.strftime('%Y-%m-%d'))

        if hist.empty:
            return None

        # Latest data
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else hist.iloc[-1]

        current_price = float(latest['Close'])
        prev_close = float(prev['Close'])
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

        # Sparkline data: last 30 close prices
        sparkline = hist['Close'].tail(30).tolist()

        return {
            'symbol': symbol,
            'name_zh': index_info['name_zh'],
            'name_en': index_info['name_en'],
            'flag': index_info['flag'],
            'price': round(current_price, 2),
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'open': round(float(latest['Open']), 2),
            'high': round(float(latest['High']), 2),
            'low': round(float(latest['Low']), 2),
            'prev_close': round(prev_close, 2),
            'sparkline': [round(v, 2) for v in sparkline],
            'last_updated': hist.index[-1].strftime('%Y-%m-%d'),
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def get_all_indices():
    """Fetch all indices concurrently."""
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_single_index, idx): idx for idx in INDICES}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Sort results in the original order
    order = {idx['symbol']: i for i, idx in enumerate(INDICES)}
    results.sort(key=lambda x: order.get(x['symbol'], 999))
    return results
