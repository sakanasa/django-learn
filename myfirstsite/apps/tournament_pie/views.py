import json
import re
from urllib.parse import urlparse

import requests as http_requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from deck_showcase.services.scraper import parse_deck_input, scrape_deck

WS_CARD_IMG_BASE = 'https://ws-tcg.com/wordpress/wp-content/images/cardlist/'

# Hosts allowed through proxy_image's ?url= passthrough (Bottleneko's own
# card image CDN). Keep this tight — proxy_image is server-side fetch, so an
# unrestricted host would make it an open proxy / SSRF vector.
ALLOWED_PROXY_HOSTS = {'img.bottleneko.app'}


def editor_page(request):
    return render(request, 'tournament_pie/editor.html')


@require_http_methods(['POST'])
def fetch_deck(request):
    try:
        body = json.loads(request.body)
    except (ValueError, KeyError):
        return JsonResponse({'error': '無效的請求格式'}, status=400)

    url = body.get('url', '').strip()
    if not url:
        return JsonResponse({'error': '請輸入貓罐子網址'}, status=400)

    deck_code, _source = parse_deck_input(url, default_source='bottleneko')

    try:
        result = scrape_deck(deck_code, source='bottleneko')
    except RuntimeError as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Build proxy image URLs so canvas can read them without CORS issues
    cards = []
    for c in result['cards']:
        img_path = c.get('img', '')
        if not img_path:
            img_url = ''
        elif img_path.startswith('http'):
            img_url = f'/tournament_pie/proxy_image/?url={img_path}'
        else:
            img_url = f'/tournament_pie/proxy_image/?path={img_path}'
        cards.append({
            'card_number': c['card_number'],
            'card_name': c.get('card_name', ''),
            'img_url': img_url,
            'count': c.get('count', 1),
            'level': c.get('level', ''),
            'card_type': c.get('card_type', ''),
            'color': c.get('color', ''),
            'series_code': c.get('series_code', ''),
        })

    return JsonResponse({
        'deck_code': result['deck_code'],
        'deck_title': result['deck_title'],
        'cards': cards,
        'products': result.get('products', []),
        'total_cards': result['total_cards'],
    })


def proxy_image(request):
    """Proxy ws-tcg.com card images to avoid CORS issues on canvas.

    WE-series cards have two possible folder naming conventions on ws-tcg.com:
      - {series}_we{n}   e.g. lrc_we47  (single-series WE)
      - {char}xx_we{n}   e.g. kxx_we50  (cross-series WE)
    We try both so every card is found regardless of which convention applies.
    """
    full_url = request.GET.get('url', '').strip()
    if full_url:
        parsed = urlparse(full_url)
        if parsed.scheme != 'https' or parsed.netloc not in ALLOWED_PROXY_HOSTS:
            return HttpResponse(status=400)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            resp = http_requests.get(full_url, timeout=10, headers=headers)
            if resp.status_code == 200:
                return HttpResponse(
                    resp.content,
                    content_type=resp.headers.get('Content-Type', 'image/png'),
                )
        except Exception:
            pass
        return HttpResponse(status=404)

    img_path = request.GET.get('path', '').strip()
    if not img_path or not re.match(r'^[a-z0-9/_.\-]+$', img_path):
        return HttpResponse(status=400)

    # Build candidate paths (primary + WE-series fallback)
    candidates = [img_path]
    we_m = re.match(r'^([a-z])/([a-z0-9]+)_(we\d+)/([a-z0-9_.\-]+)$', img_path)
    if we_m:
        ch, folder_prefix, we_code, filename = we_m.groups()
        # Series prefix embedded in filename (e.g. "lrc_we47_28.png" → "lrc")
        fn_series = filename.split(f'_{we_code}')[0]
        if folder_prefix == fn_series:
            alt_folder = f'{ch}xx_{we_code}'        # lrc_we47 → lxx_we47
        else:
            alt_folder = f'{fn_series}_{we_code}'   # lxx_we47 → lrc_we47
        candidates.append(f'{ch}/{alt_folder}/{filename}')

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for path in candidates:
        url = f'{WS_CARD_IMG_BASE}{path}'
        try:
            resp = http_requests.get(url, timeout=10, headers=headers)
            if resp.status_code == 200:
                return HttpResponse(
                    resp.content,
                    content_type=resp.headers.get('Content-Type', 'image/png'),
                )
        except Exception:
            continue

    return HttpResponse(status=404)
