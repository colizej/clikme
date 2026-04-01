from django.views.generic import TemplateView, DetailView
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from .models import Page


class PageDetailView(DetailView):
    model = Page
    template_name = 'pages/page_detail.html'
    context_object_name = 'page'

    def get_queryset(self):
        return Page.objects.filter(is_published=True)
    
    def get_object(self, queryset=None):
        if 'slug' in self.kwargs:
            return get_object_or_404(Page, slug=self.kwargs['slug'], is_published=True)
        return super().get_object(queryset)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['rendered_content'] = self.object.get_rendered_content()
        return ctx


class ContactsView(TemplateView):
    template_name = 'pages/contacts.html'

    def post(self, request, *args, **kwargs):
        if request.POST.get('website'):  # honeypot
            return self.get(request, *args, **kwargs)
        name = request.POST.get('name', '').strip()[:100]
        email = request.POST.get('email', '').strip()[:200]
        message = request.POST.get('message', '').strip()[:2000]
        if name and email and message:
            send_mail(
                subject=f'[ClikMe] Сообщение от {name}',
                message=f'От: {name} <{email}>\n\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        return self.render_to_response(self.get_context_data(success=True))


class SitemapView(TemplateView):
    template_name = 'pages/sitemap.xml'
    content_type = 'application/xml'

    def get_context_data(self, **kwargs):
        from apps.blog.models import Article, Category
        from apps.vendors.models import Vendor
        from apps.news.models import NewsItem
        ctx = super().get_context_data(**kwargs)
        ctx['base_url'] = self.request.build_absolute_uri('/').rstrip('/')
        ctx['articles'] = Article.objects.filter(is_published=True).select_related('category').only('slug', 'published_at', 'category__slug')
        ctx['categories'] = Category.objects.filter(is_active=True).only('slug')
        ctx['vendors'] = Vendor.objects.filter(is_active=True, approved=True).only('slug')
        ctx['news_items'] = NewsItem.objects.filter(status='published').only('slug', 'published_at')[:200]
        ctx['pages'] = Page.objects.filter(is_published=True).only('slug', 'updated_at')
        return ctx
