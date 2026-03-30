from django.core.cache import cache
from apps.pages.models import Page


def footer_pages(request):
    """Добавляет страницы для футера и категории навигации в контекст всех шаблонов.
    Кешируется на 5 минут чтобы не делать 2 SQL-запроса на каждой странице.
    """
    from apps.blog.models import Category

    result = cache.get('global_context')
    if result is None:
        result = {
            'footer_pages': list(Page.objects.filter(
                is_published=True
            ).order_by('sort_order', 'title')[:5]),
            'nav_categories': list(Category.objects.filter(
                is_active=True
            ).order_by('sort_order', 'name')),
        }
        cache.set('global_context', result, 300)  # 5 минут
    return result
