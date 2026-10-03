from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .services.scraper import scrape_deck, parse_deck_input
from .services.showcase import generate_showcase_image

VALID_SOURCES = {'decklog_en', 'decklog_jp', 'bottleneko'}


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

    deck_code_raw = request.POST.get('deck_code', '').strip()
    source = request.POST.get('source', 'decklog_en').strip()

    if not deck_code_raw:
        return JsonResponse({'error': 'Please provide a deck code.'}, status=400)
    deck_code, source = parse_deck_input(deck_code_raw, default_source=source)
    if source not in VALID_SOURCES:
        source = 'decklog_en'

    try:
        deck_data = scrape_deck(deck_code, source=source, merge_alts=False)

        if not deck_data.get('cards'):
            return JsonResponse({
                'error': f'Could not find deck with code "{deck_code}".'
            }, status=404)

        cards = []
        for c in deck_data['cards']:
            img_path = c.get('img', '')
            if not img_path:
                img_url = ''
            elif img_path.startswith('http'):
                img_url = img_path
            else:
                img_url = f'https://ws-tcg.com/wordpress/wp-content/images/cardlist/{img_path}'
            cards.append({
                'card_number': c.get('card_number', ''),
                'card_name': c.get('card_name', ''),
                'img_url': img_url,
                'level': c.get('level', ''),
                'card_type': c.get('card_type', ''),
                'count': c.get('count', 1),
                'rare': c.get('rare', ''),
                'color': c.get('color', ''),
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

    deck_code_raw = request.POST.get('deck_code', '').strip()
    source = request.POST.get('source', 'decklog_en').strip()
    selected_numbers = request.POST.getlist('selected_cards[]')
    player_name = request.POST.get('player_name', '').strip()[:20]
    player_message = request.POST.get('player_message', '').strip()[:40]

    if not deck_code_raw:
        return JsonResponse({'error': 'Please provide a deck code.'}, status=400)
    if not selected_numbers:
        return JsonResponse({'error': 'Please select at least one card.'}, status=400)
    deck_code, source = parse_deck_input(deck_code_raw, default_source=source)
    if source not in VALID_SOURCES:
        source = 'decklog_en'

    # Read background parameters
    bg_type = request.POST.get('bg_type', 'tech').strip()
    bg_blur = int(request.POST.get('bg_blur', '0'))

    bg_tech_overlay = request.POST.get('bg_tech_overlay', '1') == '1'
    bg_params = {
        'type': bg_type, 'blur': bg_blur,
        'tech_overlay': bg_tech_overlay,
    }

    if bg_type == 'solid':
        bg_params['color'] = request.POST.get('bg_color', '#1a1a2e')
    elif bg_type == 'gradient':
        bg_params['color1'] = request.POST.get('bg_color1', '#1a1a2e')
        bg_params['color2'] = request.POST.get('bg_color2', '#0f3460')
        bg_params['direction'] = request.POST.get('bg_direction', 'horizontal')
    elif bg_type == 'image':
        if 'bg_image' in request.FILES:
            bg_params['image_file'] = request.FILES['bg_image']

    try:
        deck_data = scrape_deck(deck_code, source=source, merge_alts=False)

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
            bg_params=bg_params,
            source=source,
        )

        response = HttpResponse(png_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="deck_{deck_code}.png"'
        return response

    except Exception as e:
        return JsonResponse({
            'error': f'Failed to generate showcase: {str(e)}'
        }, status=500)
