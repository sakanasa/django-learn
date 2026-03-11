from django.shortcuts import render

def index(request):
    return render(request, 'ws_to_discord/index.html')
