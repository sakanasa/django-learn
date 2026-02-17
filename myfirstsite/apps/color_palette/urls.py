from django.urls import path
from . import views

app_name = 'color_palette'

urlpatterns = [
    path('', views.index, name='index'),
]
