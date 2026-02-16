from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    path('', views.journal_list, name='list'),
    path('create/', views.journal_create, name='create'),
    path('<int:pk>/delete/', views.journal_delete, name='delete'),
]
