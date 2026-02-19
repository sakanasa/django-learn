import requests
from django.conf import settings

# Ollama server on Mac Studio via Tailscale
OLLAMA_BASE_URL = getattr(settings, 'OLLAMA_BASE_URL', 'http://100.94.135.11:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5:72b-instruct-q4_K_M')

SYSTEM_PROMPT = """You are a Weiß Schwarz (ヴァイスシュヴァルツ) deck analysis expert. You provide strategic analysis of WS decks in Traditional Chinese (繁體中文).

## Game Rules Context

Weiß Schwarz is a Japanese trading card game by Bushiroad. Key mechanics:

**Deck Structure:**
- Exactly 50 cards per deck
- Cards belong to a single title/series (e.g., "ソードアート・オンライン")
- Card types: Character (キャラ), Event (イベント), Climax (クライマックス/CX)
- Exactly 8 Climax cards required
- Levels: 0, 1, 2, 3 (determines when a card can be played)

**Game Flow:**
- Both players start at Level 0 with 7 cards in hand
- Clock phase: optionally clock a card for 2 draws
- Main phase: play characters, events from hand
- Attack phase: characters attack (front attack, side attack, direct attack)
- Damage is dealt by flipping cards from the deck; Climax cards cancel damage
- Taking 7 clock advances your level; Level 4 = lose

**Key Strategic Concepts:**
- Level 0 game: early card advantage, hand filtering, establishing board
- Level 1 game: maintaining board control, CX combo execution, building stock
- Level 2 game: early play of Level 3 characters, change mechanics, healing
- Level 3 game: finishing combos, burn damage, heal loops, closing the game
- Stock management: balancing between paying costs and maintaining resources
- Climax combo (CXコンボ): card abilities that trigger when a specific CX is played
- Compression (圧縮): increasing the ratio of CX cards in deck to survive longer
- Cancel rate: probability of damage being canceled by a CX in remaining deck
- Soul damage vs. burn damage: direct damage vs. effect-based damage

**Common Archetypes:**
- Aggro/Rush: heavy Level 0-1 focus, fast soul damage
- Midrange: balanced curve, strong CX combos at Level 1 and Level 3
- Control: heal-heavy, defensive Level 2-3, win by outlasting opponents
- Burn/Finish: focus on Level 3 finishers with burn effects that bypass cancellation

## Your Task

Analyze the provided deck list and produce a structured strategic breakdown. Consider the card distribution across levels, the CX triggers, and any recognizable card effects or combos. If you recognize specific cards, reference their effects. If not, analyze based on level distribution, card type ratios, and CX trigger types.

## Output Format

Always respond in **Traditional Chinese (繁體中文)**. Structure your analysis as:

### 牌組概覽
Brief summary: series, archetype, general strategy (2-3 sentences).

### 等級分佈分析
Analyze Level 0/1/2/3 distribution and what it implies about the game plan.

### CX（高潮卡）配置
Analyze the 8 climax cards: trigger types and how they support the strategy.

### 關鍵卡牌與連攜
Identify key cards and likely CX combos. If card numbers are recognizable, explain the combos.

### 各階段戰略
- **前期（Lv0）**: Early game plan
- **中期（Lv1-2）**: Mid-game transitions
- **後期（Lv3）**: Finisher strategy and win condition

### 優勢與弱點
- **優勢**: Strengths of this build
- **弱點**: Vulnerabilities and weaknesses

### 調整建議
Optional suggestions for improvement."""


def build_user_prompt(deck_data):
    """Build the user prompt from scraped deck data."""
    cards = deck_data.get('cards', [])
    series_name = deck_data.get('series_name', 'Unknown')
    deck_code = deck_data.get('deck_code', '')
    total_cards = deck_data.get('total_cards', 0)

    # Group cards by level
    level_groups = {'0': [], '1': [], '2': [], '3': [], 'CX': []}
    for card in cards:
        level = card.get('level', '0')
        if level in level_groups:
            level_groups[level].append(card)
        else:
            level_groups['0'].append(card)

    prompt = f"""以下是一組ヴァイスシュヴァルツ牌組，請進行詳細分析。

## 牌組資訊
- **系列名**: {series_name}
- **牌組代碼**: {deck_code}
- **卡牌總數**: {total_cards}

## 卡牌列表
"""

    for level_key, level_label in [('0', 'Lv0'), ('1', 'Lv1'), ('2', 'Lv2'), ('3', 'Lv3')]:
        group = level_groups[level_key]
        count = sum(c['count'] for c in group)
        prompt += f"\n### {level_label} ({count}張)\n"
        if group:
            prompt += "| 數量 | 卡號 | 卡名 | 類型 | 費用 | 力量 | 顏色 |\n"
            prompt += "|------|------|------|------|------|------|------|\n"
            for card in group:
                prompt += (
                    f"| {card['count']} | {card['card_number']} | {card['card_name']} "
                    f"| {card.get('card_type', '')} | {card.get('cost', '')} "
                    f"| {card.get('power', '')} | {card.get('color', '')} |\n"
                )
        else:
            prompt += "（無）\n"

    # CX cards
    cx_group = level_groups['CX']
    cx_count = sum(c['count'] for c in cx_group)
    prompt += f"\n### CX ({cx_count}張)\n"
    if cx_group:
        prompt += "| 數量 | 卡號 | 卡名 | 顏色 |\n"
        prompt += "|------|------|------|------|\n"
        for card in cx_group:
            prompt += f"| {card['count']} | {card['card_number']} | {card['card_name']} | {card.get('color', '')} |\n"
    else:
        prompt += "（無法識別CX卡）\n"

    return prompt


def build_user_prompt_from_raw(deck_data):
    """Build user prompt from raw text when structured parsing fails."""
    series_name = deck_data.get('series_name', 'Unknown')
    deck_code = deck_data.get('deck_code', '')
    raw_text = deck_data.get('raw_text', '')

    prompt = f"""以下是一組ヴァイスシュヴァルツ牌組，請進行詳細分析。

## 牌組資訊
- **系列名**: {series_name}
- **牌組代碼**: {deck_code}

## 頁面上的卡牌資訊（原始文本）

{raw_text[:3000]}

請根據以上資訊分析這組牌組。如果你認得這些卡牌，請詳細說明它們的效果和策略。如果部分卡牌無法辨識，請基於可識別的資訊進行推論分析。
"""
    return prompt


def analyze_deck(deck_data):
    """
    Call Ollama to analyze a deck.

    Args:
        deck_data: dict from scraper containing card data

    Returns:
        str: LLM analysis text in Traditional Chinese
    """
    cards = deck_data.get('cards', [])

    # Choose prompt strategy based on whether we got structured card data
    if cards and len(cards) > 0:
        user_prompt = build_user_prompt(deck_data)
    else:
        user_prompt = build_user_prompt_from_raw(deck_data)

    payload = {
        'model': OLLAMA_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_prompt},
        ],
        'stream': False,
        'options': {
            'temperature': 0.4,
            'num_predict': 4096,
            'num_ctx': 8192,
        },
    }

    try:
        response = requests.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            json=payload,
            timeout=300,  # 5 min timeout for large models
        )
        response.raise_for_status()
        result = response.json()
        return result.get('message', {}).get('content', 'No response from LLM.')
    except requests.exceptions.ConnectionError:
        return (
            "**Error: Unable to connect to Ollama server.**\n\n"
            f"Please ensure Ollama is running on `{OLLAMA_BASE_URL}` "
            "and the model is loaded.\n\n"
            "```bash\n"
            "# On Mac Studio:\n"
            "export OLLAMA_HOST=0.0.0.0\n"
            "ollama serve &\n"
            f"ollama pull {OLLAMA_MODEL}\n"
            "```"
        )
    except requests.exceptions.Timeout:
        return "**Error: LLM request timed out.** The model may still be loading. Please try again."
    except Exception as e:
        return f"**Error calling LLM:** {str(e)}"


def check_ollama_status():
    """Check if Ollama server is reachable and what models are available."""
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
