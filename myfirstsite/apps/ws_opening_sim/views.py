from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.deck_showcase.services.scraper import WS_TCG_IMG_BASE, scrape_deck

VALID_SOURCES = {'decklog_en', 'decklog_jp', 'bottleneko'}


@ensure_csrf_cookie
def index(request):
    return render(request, 'ws_opening_sim/index.html')


def load_deck(request):
    """AJAX endpoint: fetch a deck and return merged cards with counts."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    deck_code = request.POST.get('deck_code', '').strip()
    source = request.POST.get('source', 'bottleneko').strip()
    if not deck_code:
        return JsonResponse({'error': 'Please provide a deck code.'}, status=400)
    if source not in VALID_SOURCES:
        source = 'bottleneko'

    try:
        deck = scrape_deck(deck_code, source=source, merge_alts=True)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    cards = [{
        'card_number': c.get('card_number', ''),
        'card_name': c.get('card_name', ''),
        'count': c.get('count', 1),
        'level': c.get('level', ''),
        'card_type': c.get('card_type', ''),
        'img_url': WS_TCG_IMG_BASE + c['img'] if c.get('img') else '',
    } for c in deck.get('cards', [])]

    if not cards:
        return JsonResponse({'error': f'Could not find deck "{deck_code}".'}, status=404)

    return JsonResponse({
        'deck_code': deck_code,
        'series_name': deck.get('series_name', ''),
        'total_cards': sum(c['count'] for c in cards),
        'cards': cards,
    })
