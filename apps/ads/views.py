from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django.utils import timezone

from .models import AdUnit, AdClick


def get_client_ip(request):
    """Получить IP пользователя"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_GET
def ads_click(request, ad_id):
    """
    Обработка клика по рекламе.
    
    URL: /ads/click/{ad_id}/?next={encoded_url}&article={article_slug}
    """
    ad_unit = get_object_or_404(AdUnit, pk=ad_id)
    
    # Получаем целевую ссылку
    next_url = request.GET.get('next', ad_unit.link or ad_unit.partner.url)
    
    # Если ссылки нет, редирект на партнёра
    if not next_url:
        next_url = ad_unit.partner.url
    
    # Логируем клик
    article_slug = request.GET.get('article')
    
    # Получаем article_id из slug если передан
    article_id = None
    if article_slug:
        try:
            from apps.blog.models import Article
            article = Article.objects.filter(slug=article_slug).first()
            if article:
                article_id = article.id
        except Exception:
            pass
    
    AdClick.objects.create(
        ad_unit=ad_unit,
        article_id=article_id,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        referer=request.META.get('HTTP_REFERER', '')[:500],
    )
    
    # Увеличиваем счётчик кликов
    AdUnit.objects.filter(pk=ad_id).update(
        clicks_count=ad_unit.clicks_count + 1
    )
    
    return redirect(next_url)


@require_GET
def ads_pixel(request, ad_id):
    """
    Пустой пиксель для отслеживания показов (1x1 transparent GIF).
    """
    # Можно добавить логику отслеживания показов
    response = HttpResponse(
        bytes([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 
               0x01, 0x00, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff,
               0x00, 0x00, 0x00, 0x21, 0xf9, 0x04, 0x01, 0x00,
               0x00, 0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00,
               0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
               0x01, 0x00, 0x3b]),
        content_type='image/gif'
    )
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
