from django.urls import path
from . import views

app_name = 'deck_showcase'

urlpatterns = [
    path('', views.showcase_page, name='showcase'),
    path('cards/', views.showcase_cards, name='showcase_cards'),
    path('generate/', views.showcase_generate, name='showcase_generate'),
]
