from django.views.generic import TemplateView, DetailView
from .models import Page


class PageDetailView(DetailView):
    model = Page
    template_name = 'pages/page_detail.html'
    context_object_name = 'page'

    def get_queryset(self):
        return Page.objects.filter(is_published=True)


class PrivacyView(TemplateView):
    template_name = 'pages/privacy.html'


class ContactsView(TemplateView):
    template_name = 'pages/contacts.html'


class SitemapView(TemplateView):
    template_name = 'pages/sitemap.xml'
    content_type = 'application/xml'
