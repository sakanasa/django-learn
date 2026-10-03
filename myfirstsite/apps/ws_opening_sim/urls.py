from django.urls import path
from . import views

app_name = 'ws_opening_sim'

urlpatterns = [
    path('', views.index, name='index'),
    path('deck/', views.load_deck, name='load_deck'),
]
