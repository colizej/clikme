import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def price_format(value):
    """Format a decimal price as '100 000,00' (space thousands, comma decimal)."""
    try:
        parts = f"{float(value):.2f}".split('.')
        integer = parts[0]
        decimals = parts[1]
        # Insert non-breaking space every 3 digits from the right
        grouped = []
        for i, ch in enumerate(reversed(integer)):
            if i and i % 3 == 0:
                grouped.append('\u00a0')
            grouped.append(ch)
        return ''.join(reversed(grouped)) + ',' + decimals
    except (ValueError, TypeError):
        return value


@register.filter(is_safe=True)
def insert_before_first_h2(html: str, content: str) -> str:
    """
    Вставляет контент перед первым <h2 в HTML.
    
    Usage:
        {{ article.content|insert_before_first_h2:ad_html }}
    """
    if not html or not content:
        return html
    
    # Находим первое <h2 (case insensitive)
    match = re.search(r'<h2', html, re.IGNORECASE)
    if match:
        pos = match.start()
        return mark_safe(html[:pos] + content + html[pos:])
    
    return html


@register.filter
def strip_first_image(html: str) -> str:
    """
    Убирает первое изображение из HTML контента статьи.
    Используется на странице статьи, где картинка уже показана как hero.
    Удаляет:
      - <p><img ...></p>
      - <img ...>  (в начале или после первого <p> пустого)
    """
    if not html:
        return html
    # Вариант 1: <p>\n<img ...>\n</p> в самом начале
    result = re.sub(
        r'^\s*<p>\s*<img\b[^>]*/?>\s*</p>\s*',
        '',
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    if result != html:
        return mark_safe(result)

    # Вариант 2: <img ...> без <p>-обёртки в самом начале
    result = re.sub(
        r'^\s*<img\b[^>]*/?>\s*',
        '',
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    return mark_safe(result)
