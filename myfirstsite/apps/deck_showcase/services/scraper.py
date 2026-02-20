import re
import requests

# Card image base URL
WS_TCG_IMG_BASE = 'https://ws-tcg.com/wordpress/wp-content/images/cardlist/'

# Decklog API endpoints
DECKLOG_EN_API = 'https://decklog-en.bushiroad.com/system/app-ja/api/view/{deck_code}'
DECKLOG_JP_API = 'https://decklog.bushiroad.com/system/app/api/view/{deck_code}'

# Bottleneko API endpoint
BOTTLENEKO_API = 'https://bottleneko.app/api/deck/{deck_code}'

# card_kind mapping (Decklog)
CARD_KIND_MAP = {
    2: 'キャラ',
    3: 'イベント',
    4: 'クライマックス',
}

# Color mapping from Decklog image filename to readable name
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
_RARITY_SUFFIX_RE = re.compile(r'^(.+?-[A-Za-z]?\d+)[A-Za-z]+$')


def _base_card_number(card_number):
    """Strip rarity suffix to get the base card number for merging."""
    m = _RARITY_SUFFIX_RE.match(card_number)
    return m.group(1) if m else card_number


def _card_number_to_img_path(card_number):
    """Convert a card number like 'Fab/W120-066' to ws-tcg.com image path.

    Pattern: first char of prefix / series_code_lowercase / full_number_lowercase.png
    e.g. Fab/W120-066 -> f/fab_w120/fab_w120_066.png
    """
    if '/' not in card_number or '-' not in card_number:
        return ''
    prefix = card_number.split('/')[0].lower()
    first_char = prefix[0]
    series_part = card_number.split('-')[0].lower().replace('/', '_')
    cn_lower = card_number.lower().replace('/', '_').replace('-', '_')
    return f'{first_char}/{series_part}/{cn_lower}.png'


# ============================================================
# Unified entry point
# ============================================================

def scrape_deck(deck_code, source='decklog_en', merge_alts=True):
    """Fetch deck data from the specified source.

    Args:
        deck_code: The deck code string.
        source: One of 'decklog_en', 'decklog_jp', 'bottleneko'.
        merge_alts: If True, merge alternate art versions.

    Returns:
        dict with series_name, deck_code, deck_title, cards, total_cards
    """
    if source == 'decklog_en':
        return _scrape_decklog(deck_code, 'en', merge_alts)
    elif source == 'decklog_jp':
        return _scrape_decklog(deck_code, 'jp', merge_alts)
    elif source == 'bottleneko':
        return _scrape_bottleneko(deck_code, merge_alts)
    else:
        raise ValueError(f'Unknown source: {source}')


# ============================================================
# Decklog scraper (EN + JP)
# ============================================================

def _scrape_decklog(deck_code, region='en', merge_alts=True):
    """Fetch deck data from Decklog REST API (EN or JP)."""
    if region == 'jp':
        url = DECKLOG_JP_API.format(deck_code=deck_code)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f'https://decklog.bushiroad.com/view/{deck_code}',
        }
    else:
        url = DECKLOG_EN_API.format(deck_code=deck_code)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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

    if not data or (isinstance(data, list) and len(data) == 0):
        raise RuntimeError(f'Empty deck or invalid deck code: {deck_code}')

    if isinstance(data, list):
        raise RuntimeError(f'Empty deck or invalid deck code: {deck_code}')

    if not data.get('list'):
        raise RuntimeError(f'Empty deck or invalid deck code: {deck_code}')

    # Extract series name
    series_name = ''
    deck_param2 = data.get('deck_param2', '')
    s_list2 = data.get('s_list2', {})
    if deck_param2 and s_list2:
        keys = [k for k in deck_param2.split('##') if k]
        if keys:
            series_key = f'##{keys[0]}##'
            series_name = s_list2.get(series_key, '')

    if not series_name and s_list2:
        series_name = next(iter(s_list2.values()), '')
    if not series_name:
        series_name = data.get('title', '')

    deck_title = data.get('title', '')

    # Parse cards
    cards = []
    if merge_alts:
        merged = {}
        card_order = []

        for item in data['list']:
            card_number = item.get('card_number', '')
            base_num = _base_card_number(card_number)
            num = item.get('num', 1)
            item_rare = item.get('rare', '')
            item_img = item.get('img', '')

            if base_num in merged:
                merged[base_num]['count'] += num
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


# ============================================================
# Bottleneko scraper
# ============================================================

def _scrape_bottleneko(deck_code, merge_alts=True):
    """Fetch deck data from Bottleneko API."""
    url = BOTTLENEKO_API.format(deck_code=deck_code)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'Failed to fetch deck {deck_code}: {e}')

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f'Invalid JSON response for deck {deck_code}')

    if not data or not data.get('cards'):
        raise RuntimeError(f'Empty deck or invalid deck code: {deck_code}')

    series_name = data.get('title', '')
    deck_title = data.get('title', '')

    # Convert Bottleneko card format to unified format
    raw_cards = []
    for c in data['cards']:
        card_number = c.get('id', '')
        card_type = c.get('type', 'キャラ')

        if card_type == 'クライマックス':
            level = 'CX'
        else:
            level = str(c.get('level', '0'))

        color = c.get('color', '')  # already red/blue/yellow/green

        # Derive image path from card number
        img = _card_number_to_img_path(card_number)

        raw_cards.append({
            'card_number': card_number,
            'card_name': c.get('title', ''),
            'count': 1,  # Bottleneko lists each card individually
            'level': level,
            'card_type': card_type,
            'cost': str(c.get('cost', '')),
            'power': str(c.get('attack', '')),
            'color': color,
            'trigger': '',
            'rare': c.get('rare', ''),
            'img': img,
        })

    # Merge duplicate cards
    if merge_alts:
        merged = {}
        card_order = []
        for card in raw_cards:
            cn = card['card_number']
            base_num = _base_card_number(cn)
            if base_num in merged:
                merged[base_num]['count'] += 1
                existing_priority = _RARITY_PRIORITY.get(merged[base_num].get('rare', ''), -1)
                new_priority = _RARITY_PRIORITY.get(card.get('rare', ''), -1)
                if new_priority > existing_priority and card['img']:
                    merged[base_num]['img'] = card['img']
                    merged[base_num]['rare'] = card['rare']
            else:
                card['card_number'] = base_num if base_num != cn else cn
                merged[base_num] = card
                card_order.append(base_num)
        cards = [merged[k] for k in card_order]
    else:
        cards = raw_cards

    total_cards = sum(c['count'] for c in cards)

    return {
        'series_name': series_name,
        'deck_code': deck_code,
        'deck_title': deck_title,
        'cards': cards,
        'total_cards': total_cards,
    }
