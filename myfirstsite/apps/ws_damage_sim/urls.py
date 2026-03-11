from django.urls import path
from . import views

app_name = 'ws_damage_sim'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/simulate', views.api_simulate, name='api_simulate'),
    path('api/combos', views.api_combos, name='api_combos'),
    path('api/combos/<str:combo_id>', views.api_combo_detail, name='api_combo_detail'),
]
