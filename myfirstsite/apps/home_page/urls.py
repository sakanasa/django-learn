from django.urls import path
from . import views

app_name = 'home_page'

urlpatterns = [
    path('',      views.dashboard,    name='index'),
    path('edit/', views.edit_profile, name='edit_profile'),
]
