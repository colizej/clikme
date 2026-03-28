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
    from django.template import Template, Context
    
    template_str = '''
<div class="ad-container ad-container--{{ ad.ad_type }}" data-slot="{{ slot.slug }}" data-ad="{{ ad.id }}">
    {% if ad.intro_text %}
    <p class="ad-intro">{{ ad.intro_text }}</p>
    {% endif %}
    
    {% if ad.ad_type == 'widget' %}
    <div class="ad-widget">
        {{ ad.widget_code|safe }}
    </div>
    
    {% elif ad.ad_type == 'banner' %}
    {% if ad.html_code %}
    <div class="ad-html">{{ ad.html_code|safe }}</div>
    {% elif ad.image %}
    <a href="/ads/click/{{ ad.id }}/{% if article %}?article={{ article.slug }}{% endif %}" 
       target="_blank" rel="noopener sponsored">
        <img src="{{ ad.image.url }}" alt="{{ ad.partner.name }}" loading="lazy">
    </a>
    {% endif %}
    
    {% elif ad.ad_type == 'html' %}
    <div class="ad-html">{{ ad.html_code|safe }}</div>
    
    {% elif ad.ad_type == 'text' %}
    <a href="/ads/click/{{ ad.id }}/{% if article %}?article={{ article.slug }}{% endif %}" 
       class="ad-text-link"
       target="_blank" rel="noopener sponsored">
        {% if ad.intro_text %}{{ ad.intro_text }} {% endif %}{{ ad.text }}
    </a>
    {% endif %}
    
    <span class="ad-disclaimer">Реклама</span>
</div>
'''
    
    # Create a mock slot for template rendering
    class MockSlot:
        def __init__(self):
            self.slug = slot_slug
    
    t = Template(template_str)
    c = Context({'ad': ad, 'slot': MockSlot(), 'article': article})
    return t.render(c)
