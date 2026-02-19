from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from deck_analysis.services.scraper import scrape_deck_simple
from .services.showcase import generate_showcase_image


@ensure_csrf_cookie
def showcase_page(request):
    """Showcase standalone page."""
    return render(request, 'deck_showcase/showcase.html')


def showcase_cards(request):
    """
    AJAX endpoint: fetch deck and return unique card list for selection.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    deck_code = request.POST.get('deck_code', '').strip()
    if not deck_code:
        return JsonResponse({'error': 'Please provide a deck code.'}, status=400)

    try:
        deck_data = scrape_deck_simple(deck_code, merge_alts=False)

        if not deck_data.get('cards'):
            return JsonResponse({
                'error': f'Could not find deck with code "{deck_code}".'
            }, status=404)

        cards = []
        for c in deck_data['cards']:
            img_path = c.get('img', '')
            if img_path:
                img_url = f'https://ws-tcg.com/wordpress/wp-content/images/cardlist/{img_path}'
            else:
                img_url = ''
            cards.append({
                'card_number': c.get('card_number', ''),
                'card_name': c.get('card_name', ''),
                'img_url': img_url,
                'level': c.get('level', ''),
                'card_type': c.get('card_type', ''),
                'count': c.get('count', 1),
                'rare': c.get('rare', ''),
            })

        return JsonResponse({
            'series_name': deck_data.get('series_name', ''),
            'deck_code': deck_code,
            'cards': cards,
        })

    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)


def showcase_generate(request):
    """
    AJAX endpoint: generate showcase image from user-selected cards.
    Accepts deck_code + selected_cards[] (card_number list).
    Returns PNG image.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    deck_code = request.POST.get('deck_code', '').strip()
    selected_numbers = request.POST.getlist('selected_cards[]')
    player_name = request.POST.get('player_name', '').strip()[:20]
    player_message = request.POST.get('player_message', '').strip()[:40]

    if not deck_code:
        return JsonResponse({'error': 'Please provide a deck code.'}, status=400)
    if not selected_numbers:
        return JsonResponse({'error': 'Please select at least one card.'}, status=400)

    try:
        deck_data = scrape_deck_simple(deck_code, merge_alts=False)

        if not deck_data.get('cards'):
            return JsonResponse({
                'error': f'Could not find deck with code "{deck_code}".'
            }, status=404)

        # Filter to only user-selected cards (preserve selection order)
        card_map = {c['card_number']: c for c in deck_data['cards']}
        selected_cards = []
        for num in selected_numbers:
            if num in card_map:
                selected_cards.append(card_map[num])

        if not selected_cards:
            return JsonResponse({'error': 'No valid cards selected.'}, status=400)

        png_bytes = generate_showcase_image(
            selected_cards, deck_data,
            player_name=player_name,
            player_message=player_message,
        )

        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="deck_{deck_code}.png"'
        return response

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to generate showcase: {str(e)}'
        }, status=500)
