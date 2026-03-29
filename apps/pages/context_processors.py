from apps.pages.models import Page


def footer_pages(request):
    """Добавляет страницы для футера в контекст всех шаблонов"""
    return {
        'footer_pages': Page.objects.filter(
            is_published=True
        ).order_by('sort_order', 'title')[:5]
    }
