from django.urls import path
from . import views

app_name = 'deck_analysis'

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.analyze, name='analyze'),
]
