import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


# Decklog REST API endpoint
DECKLOG_API_URL = 'https://decklog-en.bushiroad.com/system/app-ja/api/view/{deck_code}'

# WS-TCG card detail URL for scraping card effects
WS_TCG_SEARCH_URL = 'https://ws-tcg.com/cardlist/?cardno={card_no}&cmd=search'

# WS-TCG card image base URL
WS_TCG_IMG_BASE = 'https://ws-tcg.com/wordpress/wp-content/images/cardlist/'

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

# Rarity priority for choosing the best card image (higher = preferred)
_RARITY_PRIORITY = {
    'TD': 0, 'C': 1, 'U': 2, 'R': 3, 'RR': 4, 'RRR': 5, 'LRR': 6, 'SP': 7,
    'CR': 5, 'SR': 6, 'SSP': 7, 'SEC': 7,
}

# Regex to strip rarity suffixes from card numbers for merging alternate arts
# e.g. LRC/W105-036SP -> LRC/W105-036, LRC/W105-036LRR -> LRC/W105-036
_RARITY_SUFFIX_RE = re.compile(r'^(.+?-[A-Za-z]?\d+)[A-Za-z]+$')


def _base_card_number(card_number):
    """Strip rarity suffix to get the base card number for merging."""
    m = _RARITY_SUFFIX_RE.match(card_number)
    return m.group(1) if m else card_number


def scrape_deck_simple(deck_code, merge_alts=True):
    """
    Fetch deck data from the Decklog REST API.

    Args:
        deck_code: The deck code (e.g. 'X8SA')
        merge_alts: If True (default), merge alternate art versions using
                    _base_card_number. If False, keep each API entry as-is.

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

    # Fallback: use first value in s_list2, or deck title
    if not series_name and s_list2:
        series_name = next(iter(s_list2.values()), '')
    if not series_name:
        series_name = data.get('title', '')

    deck_title = data.get('title', '')

    # Parse cards
    cards = []
    if merge_alts:
        # Merge alternate art versions using base card number
        merged = {}  # base_card_number -> card dict
        card_order = []  # preserve order

        for item in data['list']:
            card_number = item.get('card_number', '')
            base_num = _base_card_number(card_number)
            num = item.get('num', 1)
            item_rare = item.get('rare', '')
            item_img = item.get('img', '')

            if base_num in merged:
                merged[base_num]['count'] += num
                # Keep img from highest rarity version
                existing_priority = _RARITY_PRIORITY.get(merged[base_num].get('rare', ''), -1)
                new_priority = _RARITY_PRIORITY.get(item_rare, -1)
                if new_priority > existing_priority and item_img:
                    merged[base_num]['img'] = item_img
                    merged[base_num]['rare'] = item_rare
            else:
                card_kind = item.get('card_kind', 2)
                level = item.get('level', '0')
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
                    'rare': item_rare,
                    'img': item_img,
                }
                merged[base_num] = card_data
                card_order.append(base_num)

        cards = [merged[k] for k in card_order]
    else:
        # Keep each API entry as-is (no merging)
        for item in data['list']:
            card_kind = item.get('card_kind', 2)
            level = item.get('level', '0')
            if card_kind == 4:
                level = 'CX'

            color_raw = item.get('color', '')
            color = COLOR_MAP.get(color_raw, color_raw)

            cards.append({
                'card_number': item.get('card_number', ''),
                'card_name': item.get('name', ''),
                'count': item.get('num', 1),
                'level': level,
                'card_type': CARD_KIND_MAP.get(card_kind, 'キャラ'),
                'cost': item.get('cost', ''),
                'power': item.get('power', ''),
                'color': color,
                'trigger': '',
                'rare': item.get('rare', ''),
                'img': item.get('img', ''),
            })

    total_cards = sum(c['count'] for c in cards)

    return {
        'series_name': series_name,
        'deck_code': deck_code,
        'deck_title': deck_title,
        'cards': cards,
        'total_cards': total_cards,
    }


# Regex to extract quoted CX names from card effect text (Japanese quotes)
_CX_NAME_RE = re.compile(r'「([^」]+)」')


def _fetch_card_effect(card_no):
    """Fetch card effect HTML from ws-tcg.com and return the text content."""
    url = WS_TCG_SEARCH_URL.format(card_no=card_no)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.text
    except requests.exceptions.RequestException:
        return ''


def _parse_cx_combo(html_text, cx_names_set):
    """
    Parse HTML for 【CXコンボ】 and extract linked CX names.
    Returns the CX name if it's in cx_names_set, else None.
    """
    # Find all CX combo sections
    idx = 0
    while True:
        pos = html_text.find('【CXコンボ】', idx)
        if pos == -1:
            break
        # Search the surrounding text (next ~500 chars) for quoted CX names
        snippet = html_text[pos:pos + 500]
        names = _CX_NAME_RE.findall(snippet)
        for name in names:
            if name in cx_names_set:
                return name
        idx = pos + 1
    return None


def detect_cx_combo_cards(deck_data):
    """
    Detect character cards that have CX combo linking to CX cards in the deck.

    Args:
        deck_data: dict from scrape_deck_simple()

    Returns:
        list of {'card': card_data, 'cx_name': str}
    """
    cards = deck_data.get('cards', [])

    # Collect CX card names in the deck
    cx_names = set()
    for card in cards:
        if card.get('level') == 'CX':
            cx_names.add(card['card_name'])

    if not cx_names:
        return []

    # Filter Lv1 and Lv3 character cards (CX combos are almost always on these levels)
    candidates = []
    for card in cards:
        if card.get('card_type') == 'キャラ' and card.get('level') in ('1', '3', 1, 3):
            candidates.append(card)

    if not candidates:
        return []

    # Fetch card effects concurrently
    combo_cards = []

    def _check_card(card):
        card_no = card['card_number']
        html = _fetch_card_effect(card_no)
        if not html:
            return None
        cx_name = _parse_cx_combo(html, cx_names)
        if cx_name:
            return {'card': card, 'cx_name': cx_name}
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_check_card, c): c for c in candidates}
        for future in as_completed(futures):
            result = future.result()
            if result:
                combo_cards.append(result)

    return combo_cards
