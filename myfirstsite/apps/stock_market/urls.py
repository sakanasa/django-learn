from django.urls import path
from . import views

app_name = 'stock_market'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/indices/', views.api_indices, name='api_indices'),
]
