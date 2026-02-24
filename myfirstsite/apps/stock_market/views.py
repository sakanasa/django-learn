from django.shortcuts import render
from django.http import JsonResponse
from .services.market_data import get_all_indices


def dashboard(request):
    return render(request, 'stock_market/dashboard.html')


def api_indices(request):
    """API endpoint that returns all index data as JSON."""
    try:
        data = get_all_indices()
        return JsonResponse({'status': 'ok', 'indices': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
