import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


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
