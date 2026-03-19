from django.views.generic import ListView, DetailView
from .models import NewsItem


class NewsListView(ListView):
    model = NewsItem
    template_name = 'news/news_list.html'
    context_object_name = 'news_items'
    paginate_by = 20

    def get_queryset(self):
        return NewsItem.objects.filter(status=NewsItem.PUBLISHED)


class NewsDetailView(DetailView):
    model = NewsItem
    template_name = 'news/news_detail.html'
    context_object_name = 'news_item'

    def get_queryset(self):
        return NewsItem.objects.filter(status=NewsItem.PUBLISHED)
