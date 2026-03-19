from django.db import models
from django.utils import timezone


class NewsSource(models.Model):
    RSS = 'rss'
    HTML = 'html'
    SOURCE_TYPES = [(RSS, 'RSS-лента'), (HTML, 'HTML-страница')]

    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default=RSS)
    html_selectors = models.JSONField(default=dict, blank=True)
    source_language = models.CharField(max_length=10, default='ru')
    needs_translation = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Источник'
        verbose_name_plural = 'Источники'

    def __str__(self):
        return self.name


class NewsItem(models.Model):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    REJECTED = 'rejected'
    STATUSES = [
        (DRAFT, 'Черновик'),
        (PUBLISHED, 'Опубликовано'),
        (REJECTED, 'Отклонено'),
    ]

    source = models.ForeignKey(
        NewsSource, on_delete=models.SET_NULL, null=True, related_name='items'
    )
    source_url = models.URLField(unique=True)
    slug = models.SlugField(unique=True, max_length=255, blank=True)

    title_original = models.CharField(max_length=500, blank=True)
    summary_original = models.TextField(blank=True)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)

    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='news/', blank=True)

    ai_processed = models.BooleanField(default=False)
    ai_model_used = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=15, choices=STATUSES, default=DRAFT)
    telegram_message_id = models.CharField(max_length=50, blank=True)

    fetched_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-fetched_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f'/news/{self.slug}/'
