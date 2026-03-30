from django.core.cache import cache
from django.db.models import Count, F, Q
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
    paginate_by = 18

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
            .filter(is_published=True, is_featured=False)
            .select_related('category')
            .order_by('-views_count')[:4]
        )
        ctx['featured_articles'] = (
            Article.objects
            .filter(is_published=True, is_featured=True)
            .select_related('category')
            .order_by('-published_at')[:3]
        )
        ctx['latest_news'] = (
            NewsItem.objects
            .filter(status=NewsItem.PUBLISHED)
            .only('title', 'slug', 'tag', 'published_at', 'image', 'image_url')
            .order_by('-published_at')[:6]
        )
        return ctx


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        return Article.objects.filter(is_published=True).select_related('category').prefetch_related('tags')

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            # Фолбэк 1: старые OpenCart URL вида /<vendor>/<product>/ — ищем продукт по slug
            product = Product.objects.filter(slug=kwargs.get('slug'), is_active=True).first()
            if product:
                return HttpResponseRedirect(product.get_absolute_url(), status=301)
            # Фолбэк 2: OpenCart подкатегории вида /<cat>/<subcategory>/ — на /vendors/
            vendor = Vendor.objects.filter(slug=kwargs.get('cat'), is_active=True).first()
            if vendor:
                return HttpResponseRedirect(vendor.get_absolute_url(), status=301)
            return HttpResponseRedirect('/vendors/', status=301)
        # Если в URL передана категория — проверяем соответствие, иначе 301 на canonical
        cat_in_url = kwargs.get('cat')
        article_cat_slug = self.object.category.slug if self.object.category else None
        if cat_in_url is not None and cat_in_url != article_cat_slug:
            return HttpResponseRedirect(self.object.get_absolute_url(), status=301)
        # Инкремент счётчика просмотров (без гонки через F-expression)
        Article.objects.filter(pk=self.object.pk).update(views_count=F('views_count') + 1)
        return self.render_to_response(self.get_context_data())

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
        ctx['featured_articles'] = (
            Article.objects
            .filter(is_published=True, is_featured=True)
            .exclude(pk=article.pk)
            .select_related('category')
            .order_by('-published_at')[:3]
        )
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
    ).select_related('category').only('title', 'slug', 'category__slug')[:5]:
        results.append({'type': 'article', 'label': 'Статья', 'title': a.title, 'url': a.get_absolute_url()})

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


class CategoryDetailView(ListView):
    template_name = 'blog/category_detail.html'
    context_object_name = 'articles'
    paginate_by = 18

    def get_queryset(self):
        self.category = Category.objects.filter(slug=self.kwargs['slug'], is_active=True).first()
        if not self.category:
            raise Http404
        qs = (
            Article.objects
            .filter(category=self.category, is_published=True)
            .select_related('category')
            .prefetch_related('tags')
        )
        tag_slug = self.request.GET.get('tag', '').strip()
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        return qs.order_by('-published_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['category'] = self.category
        tag_slug = self.request.GET.get('tag', '').strip()
        ctx['active_tag'] = Tag.objects.filter(slug=tag_slug).first() if tag_slug else None
        ctx['all_tags'] = (
            Tag.objects
            .annotate(cnt=Count('article'))
            .filter(cnt__gt=0, article__category=self.category, article__is_published=True)
            .order_by('-cnt')
            .distinct()
        )
        return ctx


def slug_dispatch(request, slug):
    """Диспатчер: Category | Article | Vendor | Product | Page по slug.
    Тип slug кешируется на 5 минут чтобы избежать 5 SQL на каждый запрос.
    """
    _CACHE_TTL = 300  # 5 минут

    cache_key = f'slug_type:{slug}'
    obj_type = cache.get(cache_key)

    if obj_type is None:
        if Category.objects.filter(slug=slug, is_active=True).exists():
            obj_type = 'category'
        elif Article.objects.filter(slug=slug, is_published=True).exists():
            obj_type = 'article'
        elif Vendor.objects.filter(slug=slug, is_active=True).exists():
            obj_type = 'vendor'
        elif Product.objects.filter(slug=slug, is_active=True).exists():
            obj_type = 'product'
        elif Page.objects.filter(slug=slug, is_published=True).exists():
            obj_type = 'page'
        else:
            obj_type = '404'
        cache.set(cache_key, obj_type, _CACHE_TTL)

    if obj_type == 'category':
        return CategoryDetailView.as_view()(request, slug=slug)

    if obj_type == 'article':
        # Если у статьи есть категория — редирект на каноничный URL
        article = Article.objects.filter(slug=slug, is_published=True).only(
            'slug', 'category__slug'
        ).select_related('category').first()
        if article and article.category:
            canonical_url = article.get_absolute_url()
            if request.path != canonical_url:
                return HttpResponseRedirect(canonical_url, status=301)
        return ArticleDetailView.as_view()(request, slug=slug)

    if obj_type == 'vendor':
        from apps.vendors.views import VendorDetailView
        return VendorDetailView.as_view()(request, slug=slug)

    if obj_type == 'product':
        from apps.vendors.views import ProductDetailView
        return ProductDetailView.as_view()(request, slug=slug)

    if obj_type == 'page':
        from apps.pages.views import PageDetailView
        return PageDetailView.as_view()(request, slug=slug)

    raise Http404
