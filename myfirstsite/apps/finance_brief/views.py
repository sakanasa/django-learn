from datetime import date

from django.http import JsonResponse
from django.shortcuts import render

from .models import DailyBrief
from .services.market_data import get_all_market_data
from .services.news_fetcher import fetch_news
from .services.llm import generate_daily_summary, check_ollama_status


def dashboard(request):
    """Render the HTML skeleton; data is loaded via JS AJAX."""
    ollama_status = check_ollama_status()
    return render(request, 'finance_brief/dashboard.html', {
        'ollama_status': ollama_status,
    })


def api_market(request):
    """GET: Return today's market data + news (24-hour cache)."""
    today = date.today()
    brief = DailyBrief.objects.filter(date=today).first()

    if brief and brief.market_data:
        # news_headlines 為空代表之前抓取失敗（如 RSS 解析 bug），嘗試重新抓取
        if not brief.news_headlines:
            news = fetch_news(max_per_source=6)
            if news:
                brief.news_headlines = news
                brief.save(update_fields=['news_headlines'])
        return JsonResponse({
            'status': 'ok',
            'from_cache': True,
            'market_data': brief.market_data,
            'news': brief.news_headlines or [],
            'date': str(today),
        })

    # Fetch fresh data
    market_data = get_all_market_data()
    news = fetch_news(max_per_source=6)

    brief, _ = DailyBrief.objects.get_or_create(date=today)
    brief.market_data = market_data
    brief.news_headlines = news
    brief.save()

    return JsonResponse({
        'status': 'ok',
        'from_cache': False,
        'market_data': market_data,
        'news': news,
        'date': str(today),
    })


def api_summary(request):
    """GET: Return LLM summary (24h cache; first call may take 30-60s)."""
    today = date.today()
    brief = DailyBrief.objects.filter(date=today).first()

    if brief and brief.llm_summary:
        return JsonResponse({
            'status': 'ok',
            'summary': brief.llm_summary,
            'from_cache': True,
        })

    if not brief or not brief.market_data:
        return JsonResponse({'status': 'pending'}, status=202)

    summary = generate_daily_summary(
        brief.market_data,
        brief.news_headlines,
        str(today),
    )
    brief.llm_summary = summary
    brief.save()

    return JsonResponse({
        'status': 'ok',
        'summary': summary,
        'from_cache': False,
    })
