from django.db import models


class Page(models.Model):
    slug = models.SlugField(unique=True, max_length=255)
    title = models.CharField(max_length=500)
    content = models.TextField(blank=True)
    content_md = models.TextField(
        blank=True,
        verbose_name='Контент (Markdown)',
        help_text='Markdown версия контента. Приоритетнее чем HTML.'
    )
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    is_published = models.BooleanField(default=True)
    noindex = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f'/{self.slug}/'
    
    def get_rendered_content(self):
        if self.content_md:
            import markdown
            return markdown.markdown(
                self.content_md,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
        return self.content
