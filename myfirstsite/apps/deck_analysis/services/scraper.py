import re
import requests


# Decklog REST API endpoint
DECKLOG_API_URL = 'https://decklog-en.bushiroad.com/system/app-ja/api/view/{deck_code}'

# card_kind mapping
CARD_KIND_MAP = {
    2: 'キャラ',
    3: 'イベント',
    4: 'クライマックス',
}

# Color mapping from image filename to readable name
COLOR_MAP = {
    '[[red.gif]]': 'red',
    '[[blue.gif]]': 'blue',
    '[[yellow.gif]]': 'yellow',
    '[[green.gif]]': 'green',
}

# Regex to strip rarity suffixes from card numbers for merging alternate arts
# e.g. LRC/W105-036SP -> LRC/W105-036, LRC/W105-036LRR -> LRC/W105-036
_RARITY_SUFFIX_RE = re.compile(r'^(.+?-[A-Za-z]?\d+)[A-Za-z]+$')


def _base_card_number(card_number):
    """Strip rarity suffix to get the base card number for merging."""
    m = _RARITY_SUFFIX_RE.match(card_number)
    return m.group(1) if m else card_number


def scrape_deck_simple(deck_code):
    """
    Fetch deck data from the Decklog REST API.

    Args:
        deck_code: The deck code (e.g. 'X8SA')

    Returns:
        dict with series_name, deck_code, deck_title, cards, total_cards
    """
    url = DECKLOG_API_URL.format(deck_code=deck_code)
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': f'https://decklog-en.bushiroad.com/ja/view/{deck_code}',
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'Failed to fetch deck {deck_code}: {e}')

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f'Invalid JSON response for deck {deck_code}')

    if not data or not data.get('list'):
        raise RuntimeError(f'Empty deck or invalid deck code: {deck_code}')

    # Extract series name from s_list2 using deck_param2 as key
    series_name = ''
    deck_param2 = data.get('deck_param2', '')
    s_list2 = data.get('s_list2', {})
    if deck_param2 and s_list2:
        # deck_param2 may contain multiple keys like "##LRC####ABC##"
        # Extract the first key
        keys = [k for k in deck_param2.split('##') if k]
        if keys:
            series_key = f'##{keys[0]}##'
            series_name = s_list2.get(series_key, '')

    deck_title = data.get('title', '')

    # Parse and merge cards
    # Use base card number as merge key to combine alternate art versions
    merged = {}  # base_card_number -> card dict
    card_order = []  # preserve order

    for item in data['list']:
        card_number = item.get('card_number', '')
        base_num = _base_card_number(card_number)
        num = item.get('num', 1)

        if base_num in merged:
            merged[base_num]['count'] += num
        else:
            card_kind = item.get('card_kind', 2)
            level = item.get('level', '0')
            # CX cards have level "-", map to "CX" for grouping
            if card_kind == 4:
                level = 'CX'

            color_raw = item.get('color', '')
            color = COLOR_MAP.get(color_raw, color_raw)

            card_data = {
                'card_number': base_num if base_num != card_number else card_number,
                'card_name': item.get('name', ''),
                'count': num,
                'level': level,
                'card_type': CARD_KIND_MAP.get(card_kind, 'キャラ'),
                'cost': item.get('cost', ''),
                'power': item.get('power', ''),
                'color': color,
                'trigger': '',
                'rare': item.get('rare', ''),
            }
            merged[base_num] = card_data
            card_order.append(base_num)

    cards = [merged[k] for k in card_order]
    total_cards = sum(c['count'] for c in cards)

    return {
        'series_name': series_name,
        'deck_code': deck_code,
        'deck_title': deck_title,
        'cards': cards,
        'total_cards': total_cards,
    }
