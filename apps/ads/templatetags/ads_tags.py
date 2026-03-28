import re
from django import template
from django.utils.safestring import mark_safe
from apps.ads.models import AdSlot
from apps.ads.services import AdService

register = template.Library()

AD_SHORTCODE_PATTERN = re.compile(r'\[ad:([^\]]+)\]')


@register.filter(name='parse_ad_shortcodes')
def parse_ad_shortcodes(text, article=None):
    """
    Заменяет шорткоды [ad:slot_slug] на HTML рекламных слотов.
    
    Usage:
        {{ article.content|parse_ad_shortcodes }}
        {{ article.content|parse_ad_shortcodes:article }}
    """
    if not text:
        return text
    
    def replace_shortcode(match):
        slot_slug = match.group(1).strip()
        try:
            slot = AdSlot.objects.get(slug=slot_slug, is_active=True)
        except AdSlot.DoesNotExist:
            return ''
        
        ad = AdService.get_ad_for_slot(slot, article)
        if ad:
            AdService.increment_impression(ad)
            return render_ad_html(slot, ad)
        return slot.fallback_text or ''
    
    result = AD_SHORTCODE_PATTERN.sub(replace_shortcode, text)
    return mark_safe(result)


def render_ad_html(slot, ad):
    """Генерирует HTML для объявления"""
    if ad.ad_type == 'widget':
        return ad.widget_code or ''
    elif ad.ad_type == 'banner':
        alt = ad.text or ad.partner.name
        click_url = f"/ads/click/{ad.id}/"
        if ad.article:
            click_url += f"?article={ad.article.slug}"
        return f'<a href="{click_url}" target="_blank" rel="nofollow"><img src="{ad.image.url}" alt="{alt}" width="{ad.widget_width or 300}" height="{ad.widget_height or 250}"></a>'
    elif ad.ad_type == 'text':
        click_url = f"/ads/click/{ad.id}/"
        if ad.article:
            click_url += f"?article={ad.article.slug}"
        intro = f'{ad.intro_text} ' if ad.intro_text else ''
        return f'<a href="{click_url}" target="_blank" rel="nofollow">{intro}{ad.text}</a>'
    return ''


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
