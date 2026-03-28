from django import template
from apps.ads.services import AdService

register = template.Library()


@register.inclusion_tag('ads/unit.html', takes_context=True)
def ad_slot(context, slot_slug, article=None):
    """
    Тег для вставки рекламного слота.
    
    Usage:
        {% ad_slot 'article_middle' article %}
        {% ad_slot 'before_faq' %}
    """
    from apps.ads.models import AdSlot
    
    try:
        slot = AdSlot.objects.get(slug=slot_slug, is_active=True)
    except AdSlot.DoesNotExist:
        return {'slot': None, 'ad': None, 'slot_type': None, 'article': article}
    
    # Получаем объявление через сервис
    ad = AdService.get_ad_for_slot(slot, article)
    
    # Увеличиваем счётчик показов
    if ad:
        AdService.increment_impression(ad)
    
    return {
        'slot': slot,
        'ad': ad,
        'slot_type': slot.slot_type,
        'article': article,
    }
