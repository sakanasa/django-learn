import requests
from django.conf import settings

OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://100.94.135.11:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:72b-instruct-q4_K_M')

SYSTEM_PROMPT = """你是一位專業的金融分析師，擅長總結每日市場動態。
請用繁體中文撰寫今日金融市場總覽，格式清晰、重點突出。
回覆必須使用以下 Markdown 結構，每個段落都要有實質內容：

## 今日市場概況
## 重要新聞解讀
## 台灣投資人注意事項
## 今日需關注風險"""


def build_market_prompt(market_data, news_headlines, date_str):
    """Build the LLM prompt from market data and news headlines."""
    indices = market_data.get('indices', [])
    fx = market_data.get('fx', [])
    commodities = market_data.get('commodities', [])

    lines = [f"# {date_str} 金融市場數據\n"]

    # Indices table
    lines.append("## 主要股票指數")
    lines.append("| 指數 | 收盤 | 漲跌 | 漲跌幅 |")
    lines.append("|------|------|------|--------|")
    for idx in indices:
        sign = '+' if idx['change'] >= 0 else ''
        lines.append(
            f"| {idx['flag']} {idx['name']} | {idx['price']:,.2f} "
            f"| {sign}{idx['change']:,.2f} | {sign}{idx['change_pct']:.2f}% |"
        )

    # FX table
    lines.append("\n## 外匯匯率")
    lines.append("| 貨幣對 | 匯率 | 漲跌幅 |")
    lines.append("|--------|------|--------|")
    for item in fx:
        sign = '+' if item['change'] >= 0 else ''
        lines.append(
            f"| {item['name']} | {item['price']:.4f} | {sign}{item['change_pct']:.2f}% |"
        )

    # Commodities table
    lines.append("\n## 大宗商品")
    lines.append("| 商品 | 單位 | 價格 | 漲跌幅 |")
    lines.append("|------|------|------|--------|")
    for item in commodities:
        sign = '+' if item['change'] >= 0 else ''
        lines.append(
            f"| {item['name']} | {item['unit']} | {item['price']:,.2f} "
            f"| {sign}{item['change_pct']:.2f}% |"
        )

    # News headlines
    if news_headlines:
        lines.append("\n## 今日財經新聞標題")
        for i, news in enumerate(news_headlines[:12], 1):
            lines.append(f"{i}. [{news['title']}] ({news['source']})")

    lines.append(
        f"\n請根據以上 {date_str} 的市場數據與新聞，"
        "撰寫今日金融市場總覽（繁體中文），"
        "包含：今日市場概況、重要新聞解讀、台灣投資人注意事項、今日需關注風險。"
    )

    return '\n'.join(lines)


def generate_daily_summary(market_data, news_headlines, date_str):
    """Call Ollama to generate a daily market summary in Traditional Chinese.

    Returns:
        str: markdown-formatted summary text
    """
    user_prompt = build_market_prompt(market_data, news_headlines, date_str)

    payload = {
        'model': OLLAMA_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user',   'content': user_prompt},
        ],
        'stream': False,
        'options': {
            'temperature': 0.4,
            'num_predict': 2048,
        },
    }

    try:
        response = requests.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        result = response.json()
        return result.get('message', {}).get('content', 'LLM 未返回內容。')
    except requests.exceptions.ConnectionError:
        return (
            "**錯誤：無法連接 Ollama 伺服器。**\n\n"
            f"請確認 Ollama 已在 `{OLLAMA_BASE_URL}` 上運行，且模型已載入。"
        )
    except requests.exceptions.Timeout:
        return "**錯誤：LLM 請求逾時。** 模型可能仍在載入，請稍後再試。"
    except Exception as e:
        return f"**LLM 呼叫失敗：** {str(e)}"


def check_ollama_status():
    """Check if Ollama server is reachable."""
    try:
        response = requests.get(f'{OLLAMA_BASE_URL}/api/tags', timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [m['name'] for m in data.get('models', [])]
        return {
            'online': True,
            'models': models,
            'has_target_model': OLLAMA_MODEL in models,
        }
    except Exception:
        return {
            'online': False,
            'models': [],
            'has_target_model': False,
        }
