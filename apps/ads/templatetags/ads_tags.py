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
            return render_ad_html(slot, ad, article)
        return slot.fallback_text or ''
    
    result = AD_SHORTCODE_PATTERN.sub(replace_shortcode, text)
    return mark_safe(result)


def render_ad_html(slot, ad, article=None):
    """Генерирует HTML для объявления"""
    click_url = f"/ads/click/{ad.id}/"
    if article:
        click_url += f"?article={article.slug}"
    
    if ad.ad_type == 'widget':
        return ad.widget_code or ''
    elif ad.ad_type == 'banner':
        if ad.html_code:
            return ad.html_code
        if ad.image:
            alt = ad.text or ad.partner.name
            return f'<a href="{click_url}" target="_blank" rel="nofollow sponsored"><img src="{ad.image.url}" alt="{alt}" loading="lazy"></a>'
        return ''
    elif ad.ad_type == 'html':
        return ad.html_code or ''
    elif ad.ad_type == 'text':
        intro = f'{ad.intro_text} ' if ad.intro_text else ''
        return f'<a href="{click_url}" target="_blank" rel="nofollow sponsored">{intro}{ad.text}</a>'
    return ''


@register.inclusion_tag('ads/unit.html', takes_context=True)
def ad_slot(context, slot_slug, article=None, page_type='article'):
    """
    Тег для вставки рекламной позиции.
    
    Usage:
        {% ad_slot 'article-middle' article %}
        {% ad_slot 'article-end' article 'article' %}
        {% ad_slot 'news-top' None 'news' %}
    """
    try:
        slot = AdSlot.objects.get(slug=slot_slug, page_type=page_type, is_active=True)
    except AdSlot.DoesNotExist:
        return {'slot': None, 'ad': None, 'article': article}
    
    ad = AdService.get_ad_for_slot(slot, article)
    
    if ad:
        AdService.increment_impression(ad)
    
    return {
        'slot': slot,
        'ad': ad,
        'article': article,
    }


@register.simple_tag
def get_ad_html(slot_slug, article=None, page_type='article'):
    """
    Возвращает HTML объявления для вставки.
    
    Usage:
        {% get_ad_html 'article-before_h2' article as ad_html %}
        {{ content|insert_before_first_h2:ad_html }}
    """
    try:
        slot = AdSlot.objects.get(slug=slot_slug, page_type=page_type, is_active=True)
    except AdSlot.DoesNotExist:
        return ''
    
    ad = AdService.get_ad_for_slot(slot, article)
    
    if ad:
        AdService.increment_impression(ad)
        return render_ad_unit(ad, article)
    
    return ''


def render_ad_unit(ad, article=None):
    """Генерирует HTML для объявления (полный контейнер)"""
    slot_slug = ad.slot.slug if ad.slot else 'unknown'
    click_url = f"/ads/click/{ad.id}/"
    if article:
        click_url += f"?article={article.slug}"
    
    # Inline styles - только внутренний padding
    html = f'<div class="ad-container" style="padding: 1.5rem; background: var(--color-bg-warm); border-radius: 1rem; border: 1px solid var(--color-border); text-align: center; box-sizing: border-box; display: block !important;">'
    
    if ad.intro_text:
        html += f'<p class="ad-intro" style="margin: 0 0 0.75rem; font-size: 0.875rem; color: var(--color-text-muted); font-weight: 500;">{ad.intro_text}</p>'
    
    if ad.ad_type == 'widget':
        # Заменяем width в iframe на 100%
        import re
        widget_code = re.sub(r'width:\s*\d+px', 'width:100%', ad.widget_code)
        widget_code = re.sub(r'width="\d+"', 'width="100%"', widget_code)
        html += f'<div style="text-align: center; width: 100%;">{widget_code}</div>'
    elif ad.ad_type == 'banner':
        if ad.html_code:
            html += f'<div style="text-align: center;">{ad.html_code}</div>'
        elif ad.image:
            html += f'<a href="{click_url}" target="_blank" rel="noopener sponsored" style="display: inline-block;"><img src="{ad.image.url}" alt="{ad.partner.name}" loading="lazy" style="max-width: 100%; height: auto;"></a>'
    elif ad.ad_type == 'html':
        html += f'<div style="text-align: center;">{ad.html_code}</div>'
    elif ad.ad_type == 'text':
        intro = f'{ad.intro_text} ' if ad.intro_text else ''
        html += f'<a href="{click_url}" style="display: inline-block; padding: 0.5rem 1rem; background: var(--color-accent); color: white; border-radius: 9999px; font-weight: 600; text-decoration: none;" target="_blank" rel="noopener sponsored">{intro}{ad.text}</a>'
    
    html += '</div>'
    
    return mark_safe(html)
