from apps.pages.models import Page


def footer_pages(request):
    """Добавляет страницы для футера в контекст всех шаблонов"""
    from apps.blog.models import Category
    return {
        'footer_pages': Page.objects.filter(
            is_published=True
        ).order_by('sort_order', 'title')[:5],
        'nav_categories': Category.objects.filter(
            is_active=True
        ).order_by('sort_order', 'name'),
    }
