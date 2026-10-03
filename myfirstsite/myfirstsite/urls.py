"""
URL configuration for myfirstsite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.conf.urls import include

from django.views.generic import RedirectView

# Use static() to add url mapping to serve static files during development (only)
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalog/', include('catalog.urls')),
    path('pie_chart/', include(('pie_chart.urls', 'pie_chart'))),
    path('home_page/', include(('home_page.urls', 'home_page'))),
    path('journal/', include(('journal.urls', 'journal'))),
    path('color_palette/', include(('color_palette.urls', 'color_palette'))),
    path('pomodoro/', include(('pomodoro.urls', 'pomodoro'))),
    path('deck_analysis/', include(('deck_analysis.urls', 'deck_analysis'))),
    path('deck_showcase/', include(('deck_showcase.urls', 'deck_showcase'))),
    path('stock_market/', include(('stock_market.urls', 'stock_market'))),
    path('finance_brief/', include(('finance_brief.urls', 'finance_brief'))),
    path('ws_damage_sim/', include(('apps.ws_damage_sim.urls', 'ws_damage_sim'))),
    path('ws_to_discord/', include(('apps.ws_to_discord.urls', 'ws_to_discord'))),
    path('ws_opening_sim/', include(('apps.ws_opening_sim.urls', 'ws_opening_sim'))),
    path('tournament_pie/', include(('tournament_pie.urls', 'tournament_pie'))),

    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', RedirectView.as_view(url='/home_page/', permanent=True)),

    
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
