import random
from django import template
from django.db.models import F

register = template.Library()


@register.inclusion_tag('ads/unit.html', takes_context=True)
def ad_slot(context, slot_slug, article=None):
    """
    Тег для вставки рекламного слота.
    
    Usage:
        {% ad_slot 'article_middle' article as ad %}
        
    """
    from ads.models import AdUnit, AdSlot
    
    try:
        slot = AdSlot.objects.get(slug=slot_slug, is_active=True)
    except AdSlot.DoesNotExist:
        return {'slot': None, 'ad': None, 'slot_type': None}
    
    # Поиск активных объявлений для слота
    queryset = AdUnit.objects.filter(
        slot_type=slot.slot_type,
        is_active=True
    )
    
    # Фильтр по датам
    now = context['request']._current_scheme_host  # не используем, но оставим
    from django.utils import timezone
    now = timezone.now()
    queryset = queryset.filter(
        models.Q(is_permanent=True) |
        models.Q(start_date__lte=now, end_date__gte=now)
    )
    
    # Фильтр по лимитам
    queryset = queryset.filter(
        models.Q(max_impressions__isnull=True) |
        models.Q(impressions_count__lt=F('max_impressions'))
    )
    
    # Ротация: берём топ-3 по приоритету, случайный из них
    top_units = list(queryset.order_by('-priority')[:3])
    
    ad = None
    if top_units:
        ad = random.choice(top_units)
        # Увеличиваем счётчик показов
        AdUnit.objects.filter(pk=ad.pk).update(
            impressions_count=F('impressions_count') + 1
        )
    
    return {
        'slot': slot,
        'ad': ad,
        'slot_type': slot.slot_type,
        'article': article,
    }


# Нужен импорт для QuerySet фильтрации
from django.db import models
