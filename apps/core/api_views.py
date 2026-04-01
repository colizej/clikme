"""
Простой JSON API для Telegram бота и WebApp.
"""
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.db.models import Q


@require_GET
def api_vendors(request):
    """Список активных компаний для WebApp."""
    from apps.vendors.models import Vendor

    search = request.GET.get('q', '').strip()
    qs = Vendor.objects.filter(is_active=True, approved=True).order_by('display_name')

    if search:
        qs = qs.filter(
            Q(display_name__icontains=search) |
            Q(description__icontains=search) |
            Q(city__icontains=search)
        )

    data = []
    for v in qs[:100]:
        data.append({
            'name': v.display_name,
            'description': _strip_tags(v.description)[:200] if v.description else '',
            'url': f'https://clikme.ru{v.get_absolute_url()}',
            'logo_url': f'https://clikme.ru{v.image.url}' if v.image else '',
            'city': v.city,
            'telephone': v.telephone,
            'zone': _detect_zone(v),
        })

    return JsonResponse(data, safe=False)


@require_GET
def api_articles(request):
    """Список статей для WebApp."""
    from apps.blog.models import Article

    search = request.GET.get('q', '').strip()
    now = timezone.now()
    qs = (
        Article.objects
        .filter(is_published=True, published_at__lte=now)
        .select_related('category')
        .prefetch_related('tags')
        .order_by('-published_at')
    )

    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(short_description__icontains=search)
        )

    data = []
    for a in qs[:100]:
        tags = [t.name for t in a.tags.all()]
        data.append({
            'title': a.title,
            'url': f'https://clikme.ru{a.get_absolute_url()}',
            'image_url': f'https://clikme.ru{a.image.url}' if a.image else '',
            'tag': ', '.join(tags) if tags else (a.category.name if a.category else ''),
            'short_description': a.short_description or '',
        })

    return JsonResponse(data, safe=False)


@require_GET
def api_news(request):
    """Последние новости для бота /news команды."""
    from apps.news.models import NewsItem

    now = timezone.now()
    qs = NewsItem.objects.filter(
        status=NewsItem.PUBLISHED,
        published_at__lte=now,
    ).order_by('-published_at')[:10]

    data = []
    for n in qs:
        data.append({
            'title': n.title,
            'url': f'https://clikme.ru/news/{n.slug}/',
            'summary': n.summary[:300] if n.summary else '',
            'published_at': n.published_at.strftime('%d.%m.%Y %H:%M') if n.published_at else '',
            'image_url': f'https://clikme.ru{n.image.url}' if n.image else n.image_url or '',
        })

    return JsonResponse(data, safe=False)


@require_GET
def api_search(request):
    """Поиск по компаниям, статьям и новостям."""
    from apps.vendors.models import Vendor
    from apps.blog.models import Article
    from apps.news.models import NewsItem

    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'error': 'Слишком короткий запрос'}, status=400)

    now = timezone.now()
    results = []

    # Компании
    for v in Vendor.objects.filter(
        is_active=True, approved=True,
        display_name__icontains=q
    )[:5]:
        results.append({
            'type': 'vendor',
            'title': v.display_name,
            'url': f'https://clikme.ru{v.get_absolute_url()}',
        })

    # Статьи
    for a in Article.objects.filter(
        is_published=True, published_at__lte=now,
        title__icontains=q
    ).select_related('category')[:5]:
        results.append({
            'type': 'article',
            'title': a.title,
            'url': f'https://clikme.ru{a.get_absolute_url()}',
        })

    # Новости
    for n in NewsItem.objects.filter(
        status=NewsItem.PUBLISHED, published_at__lte=now,
        title__icontains=q
    )[:5]:
        results.append({
            'type': 'news',
            'title': n.title,
            'url': f'https://clikme.ru/news/{n.slug}/',
        })

    return JsonResponse(results, safe=False)


def _strip_tags(text):
    """Убирает HTML теги."""
    import re
    return re.sub(r'<[^>]+>', '', text or '')


def _detect_zone(vendor):
    """Определяет зону по адресу или городу."""
    address = (vendor.address or '').lower()
    if any(w in address for w in ['северн', 'north', 'северная']):
        return 'northern_zone'
    return 'central_zone'
