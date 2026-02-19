from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .services.scraper import scrape_deck_simple
from .services.llm import analyze_deck, check_ollama_status


@ensure_csrf_cookie
def index(request):
    """Deck analysis main page."""
    ollama_status = check_ollama_status()
    return render(request, 'deck_analysis/index.html', {
        'ollama_status': ollama_status,
    })


def analyze(request):
    """
    AJAX endpoint: scrape deck and run LLM analysis.
    Returns JSON with the analysis result.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    deck_code = request.POST.get('deck_code', '').strip()
    if not deck_code:
        return JsonResponse({'error': 'Please provide a deck code.'}, status=400)

    try:
        # Step 1: Scrape deck data
        deck_data = scrape_deck_simple(deck_code)

        if not deck_data.get('series_name') and not deck_data.get('cards'):
            return JsonResponse({
                'error': f'Could not find deck with code "{deck_code}". Please check the code and try again.'
            }, status=404)

        # Step 2: Call LLM for analysis
        analysis = analyze_deck(deck_data)

        return JsonResponse({
            'success': True,
            'series_name': deck_data.get('series_name', ''),
            'deck_code': deck_code,
            'total_cards': deck_data.get('total_cards', 0),
            'card_count': len(deck_data.get('cards', [])),
            'analysis': analysis,
        })

    except Exception as e:
        return JsonResponse({
            'error': f'An error occurred: {str(e)}'
        }, status=500)
