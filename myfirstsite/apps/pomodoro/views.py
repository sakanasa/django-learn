from django.shortcuts import render


def index(request):
    return render(request, 'pomodoro/index.html')
