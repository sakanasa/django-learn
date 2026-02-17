from django.shortcuts import render


def index(request):
    return render(request, 'color_palette/index.html')
