from django.db.models import Count, Q
from django.http import Http404, JsonResponse, HttpResponseRedirect
from django.views.generic import ListView, DetailView

from .models import Article, Category, Tag
from apps.vendors.models import Vendor, Product
from apps.news.models import NewsItem
from apps.pages.models import Page


def _ci_q(field, q):
    """Case-insensitive contains for Cyrillic in SQLite.
    SQLite LIKE is only ASCII case-insensitive, so we OR multiple case variants."""
    variants = {q, q.lower(), q.upper(), q.title(), q.capitalize()}
    combined = Q()
    for v in variants:
        combined |= Q(**{f'{field}__contains': v})
    return combined


class HomeView(ListView):
    model = Article
    template_name = 'blog/home.html'
    context_object_name = 'articles'
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Article.objects
            .filter(is_published=True)
            .select_related('category', 'author')
            .prefetch_related('tags')
        )
        q = self.request.GET.get('q', '').strip()
        tag_slug = self.request.GET.get('tag', '').strip()
        cat_slug = self.request.GET.get('category', '').strip()
        if q:
            qs = qs.filter(
                _ci_q('title', q) |
                _ci_q('short_description', q) |
                _ci_q('meta_keywords', q)
            )
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        return qs.order_by('-published_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['top_vendors'] = Vendor.objects.filter(is_active=True, approved=True)[:10]
        ctx['stats_articles'] = Article.objects.filter(is_published=True).count()
        ctx['stats_vendors'] = Vendor.objects.filter(is_active=True, approved=True).count()
        ctx['stats_news'] = NewsItem.objects.filter(status=NewsItem.PUBLISHED).count()
        ctx['all_tags'] = (
            Tag.objects
            .annotate(cnt=Count('article'))
            .filter(cnt__gt=0)
            .order_by('-cnt')
        )
        tag_slug = self.request.GET.get('tag', '').strip()
        ctx['active_tag'] = Tag.objects.filter(slug=tag_slug).first() if tag_slug else None
        ctx['top_articles'] = (
            Article.objects
            .filter(is_published=True)
            .select_related('category')
            .order_by('-views_count')[:2]
        )
        return ctx


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        return Article.objects.filter(is_published=True).prefetch_related('tags')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        article = self.object
        ctx['prev_article'] = (
            Article.objects
            .filter(is_published=True, published_at__lt=article.published_at)
            .order_by('-published_at')
            .first()
        )
        ctx['next_article'] = (
            Article.objects
            .filter(is_published=True, published_at__gt=article.published_at)
            .order_by('published_at')
            .first()
        )
        tag_ids = list(article.tags.values_list('id', flat=True))
        if tag_ids:
            ctx['related_articles'] = (
                Article.objects
                .filter(is_published=True, tags__in=tag_ids)
                .exclude(pk=article.pk)
                .prefetch_related('tags')
                .distinct()
                .order_by('-published_at')[:3]
            )
        else:
            ctx['related_articles'] = []
        ctx['manual_faqs'] = article.faqs.filter(is_auto=False)
        return ctx


class SearchView(ListView):
    template_name = 'blog/search.html'
    context_object_name = 'articles'
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        if not q or len(q) < 2:
            return Article.objects.none()
        return Article.objects.filter(
            _ci_q('title', q) |
            _ci_q('short_description', q) |
            _ci_q('meta_keywords', q),
            is_published=True
        ).order_by('-published_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        ctx['query'] = q
        if q and len(q) >= 2:
            ctx['vendors'] = Vendor.objects.filter(
                _ci_q('display_name', q) | _ci_q('description', q),
                is_active=True
            )[:8]
            ctx['news_items'] = NewsItem.objects.filter(
                _ci_q('title', q) | _ci_q('summary', q),
                status=NewsItem.PUBLISHED
            ).order_by('-pk')[:8]
            ctx['products'] = Product.objects.filter(
                _ci_q('name', q) | _ci_q('description', q),
                is_active=True
            ).select_related('vendor')[:8]
        return ctx


def search_api(request):
    """Live search JSON endpoint — returns up to 5 results per category."""
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 2:
        return JsonResponse({'results': []})

    results = []

    for a in Article.objects.filter(
        _ci_q('title', q) | _ci_q('short_description', q),
        is_published=True
    ).only('title', 'slug')[:5]:
        results.append({'type': 'article', 'label': 'Статья', 'title': a.title, 'url': f'/{a.slug}/'})

    for n in NewsItem.objects.filter(
        _ci_q('title', q),
        status=NewsItem.PUBLISHED
    ).only('title', 'slug')[:5]:
        results.append({'type': 'news', 'label': 'Новость', 'title': n.title, 'url': f'/news/{n.slug}/'})

    for v in Vendor.objects.filter(
        _ci_q('display_name', q),
        is_active=True
    ).only('display_name', 'slug')[:5]:
        results.append({'type': 'vendor', 'label': 'Компания', 'title': v.display_name, 'url': f'/{v.slug}/'})

    for p in Product.objects.filter(
        _ci_q('name', q),
        is_active=True
    ).only('name', 'slug')[:5]:
        results.append({'type': 'product', 'label': 'Товар', 'title': p.name, 'url': f'/{p.slug}/'})

    return JsonResponse({'results': results})


def slug_dispatch(request, slug):
    """Диспатчер: Article | Vendor | Product | Page по slug"""
    article = Article.objects.filter(slug=slug, is_published=True).first()
    if article:
        # Если у статьи есть категория — редирект на каноничный URL
        if article.category:
            canonical_url = article.get_absolute_url()
            if request.path != canonical_url:
                return HttpResponseRedirect(canonical_url, status=301)
        return ArticleDetailView.as_view()(request, slug=slug)

    vendor = Vendor.objects.filter(slug=slug, is_active=True).first()
    if vendor:
        from apps.vendors.views import VendorDetailView
        return VendorDetailView.as_view()(request, slug=slug)

    product = Product.objects.filter(slug=slug, is_active=True).first()
    if product:
        from apps.vendors.views import ProductDetailView
        return ProductDetailView.as_view()(request, slug=slug)

    page = Page.objects.filter(slug=slug, is_published=True).first()
    if page:
        from apps.pages.views import PageDetailView
        return PageDetailView.as_view()(request, slug=slug)

    raise Http404
