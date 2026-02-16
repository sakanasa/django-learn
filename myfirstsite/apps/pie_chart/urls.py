from django.urls import path
from . import views

app_name = 'pie_chart'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]