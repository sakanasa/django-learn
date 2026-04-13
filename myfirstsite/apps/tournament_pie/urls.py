from django.urls import path
from . import views

app_name = 'tournament_pie'

urlpatterns = [
    path('', views.editor_page, name='editor'),
    path('fetch_deck/', views.fetch_deck, name='fetch_deck'),
    path('proxy_image/', views.proxy_image, name='proxy_image'),
]
