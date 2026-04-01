"""
Отдаёт WebApp для Telegram бота по URL /bot/
"""
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt


@xframe_options_exempt
def bot_webapp(request):
    return render(request, 'bot/index.html')
