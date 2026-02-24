from django.urls import path
from . import views

app_name = 'finance_brief'

urlpatterns = [
    path('',             views.dashboard,    name='dashboard'),
    path('api/market/',  views.api_market,   name='api_market'),
    path('api/summary/', views.api_summary,  name='api_summary'),
]
