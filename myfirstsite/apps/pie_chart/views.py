from django.shortcuts import render, redirect,get_object_or_404
from .models import Series, DeckCode, Game
import json
from django.http import JsonResponse
from .main_app import get_pie_chart
from django.conf import settings 


def dashboard(request):
    if request.method == 'POST':
        print("收到 POST！", request.POST)
        name = request.POST.get('game_name')
        date = request.POST.get('game_date')
        
        deck_codes_str = request.POST.get('deck_codes', '')
        deck_codes_list = [code.strip() for code in deck_codes_str.split(',') if code.strip()]
        participants = len(deck_codes_list)

        # 臨時指定 series
        series = Series.objects.first()  # 或 get(name="臨時測試系列")

        print(name, date, participants, deck_codes_list, series,participants)


        if not name or not date or participants == 0 or not series:
            return render(request, 'pie_chart/index.html', {'error': '請填寫所有欄位'})

        game = Game.objects.create(
            name=name,
            date=date,
            participants=participants,
        )
        for code in deck_codes_list:
            deck_obj, _ = DeckCode.objects.get_or_create(code=code, series=series)
            game.decks.add(deck_obj)


        get_pie_chart(name,deck_codes_list)
        chart_url = f"{settings.MEDIA_URL}charts/{name}.png"
        return render(request, 'pie_chart/index.html', {
            'chart_url': chart_url,
            # ...其他 context...
        })




            

        

    
    

    return render(request, 'pie_chart/index.html')
