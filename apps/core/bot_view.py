"""
Отдаёт WebApp для Telegram бота по URL /bot/
"""
import os
from django.http import HttpResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.conf import settings


@xframe_options_exempt
def bot_webapp(request):
    """Главная страница WebApp."""
    html_path = os.path.join(settings.BASE_DIR, 'bot_eat_blog', 'website', 'index.html')
    if not os.path.exists(html_path):
        raise Http404
    with open(html_path, 'r', encoding='utf-8') as f:
        return HttpResponse(f.read(), content_type='text/html')
