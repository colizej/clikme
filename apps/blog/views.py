from django.db.models import Count, Q
from django.http import Http404
from django.views.generic import ListView, DetailView

from .models import Article, Category, Tag
from apps.vendors.models import Vendor, Product
from apps.pages.models import Page


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
                Q(title__icontains=q) |
                Q(short_description__icontains=q) |
                Q(meta_keywords__icontains=q)
            )
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        return qs.order_by('-published_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['top_vendors'] = Vendor.objects.filter(is_active=True, approved=True)[:6]
        ctx['all_tags'] = (
            Tag.objects
            .annotate(cnt=Count('article'))
            .filter(cnt__gt=0)
            .order_by('-cnt')
        )
        tag_slug = self.request.GET.get('tag', '').strip()
        ctx['active_tag'] = Tag.objects.filter(slug=tag_slug).first() if tag_slug else None
        return ctx


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        return Article.objects.filter(is_published=True)


class SearchView(ListView):
    template_name = 'blog/search.html'
    context_object_name = 'articles'
    paginate_by = 20

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        if not q or len(q) < 3:
            return Article.objects.none()
        return Article.objects.filter(
            Q(title__icontains=q) |
            Q(short_description__icontains=q) |
            Q(meta_keywords__icontains=q),
            is_published=True
        ).order_by('-published_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        ctx['query'] = q
        if q and len(q) >= 3:
            ctx['vendors'] = Vendor.objects.filter(
                Q(display_name__icontains=q) | Q(description__icontains=q),
                is_active=True
            )[:5]
        return ctx


def slug_dispatch(request, slug):
    """Диспатчер: Article | Vendor | Product | Page по slug"""
    article = Article.objects.filter(slug=slug, is_published=True).first()
    if article:
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
