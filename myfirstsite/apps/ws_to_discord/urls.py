from django.urls import path
from . import views

app_name = 'ws_to_discord'

urlpatterns = [
    path('', views.index, name='index'),
]
