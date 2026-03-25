from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, allow_unicode=True)
    description = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to='catalog/category/', blank=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/{self.slug}/'


class Tag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Article(models.Model):
    oc_id = models.IntegerField(null=True, blank=True, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, db_index=True, allow_unicode=True)

    title = models.CharField(max_length=500)
    subtitle = models.CharField(max_length=500, blank=True)
    short_description = models.TextField(blank=True)

    # Markdown-источник (редактируется в админке)
    content_md = models.TextField(
        blank=True,
        verbose_name='Контент (Markdown)',
        help_text='Пишите здесь в Markdown. HTML в поле «content» генерируется автоматически.',
    )
    # Отрендеренный HTML (генерируется из content_md при сохранении)
    content = models.TextField(blank=True)

    image = models.ImageField(upload_to='catalog/', blank=True)
    image_alt = models.CharField(
        max_length=300, blank=True,
        verbose_name='Alt-текст изображения',
        help_text='Описание изображения для поисковиков и screen reader',
    )

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='articles'
    )
    tags = models.ManyToManyField(Tag, blank=True)
    author = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    noindex = models.BooleanField(default=False)

    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        if self.category:
            return f'/{self.category.slug}/{self.slug}/'
        return f'/{self.slug}/'

    def save(self, *args, **kwargs):
        self.render_content()
        super().save(*args, **kwargs)

    def render_content(self):
        """Рендерит content_md → content, заменяя [imageN] на HTML."""
        import re
        import markdown
        from django.utils.html import escape

        source = self.content_md or ''

        # Собираем словарь {number: ArticleImage} если pk уже есть
        image_map = {}
        if self.pk:
            try:
                image_map = {
                    img.number: img
                    for img in self.extra_images.select_related().all()
                }
            except Exception:
                pass

        def _replace(m):
            n = int(m.group(1))
            img_obj = image_map.get(n)
            if not img_obj or not img_obj.image:
                return f'<p class="text-red-500 text-sm">[image{n}: картинка не найдена]</p>'
            url  = img_obj.image.url
            alt  = escape(img_obj.alt or self.title or '')
            title_attr = f' title="{escape(img_obj.title)}"' if img_obj.title else ''
            width_attr = ''
            classes = 'rounded-2xl w-full shadow-sm'
            html = (
                f'<figure>\n'
                f'<img src="{url}" alt="{alt}"{title_attr}'
                f' loading="lazy" decoding="async" class="{classes}"{width_attr}>\n'
            )
            if img_obj.caption:
                html += f'<figcaption>{escape(img_obj.caption)}</figcaption>\n'
            html += '</figure>'
            return html

        # Заменить [imageN] до рендера Markdown (markdown сохранит сырой HTML)
        source = re.sub(r'\[image(\d+)\]', _replace, source, flags=re.IGNORECASE)

        self.content = markdown.markdown(
            source,
            extensions=['extra', 'toc', 'nl2br', 'sane_lists'],
            output_format='html',
        )


class ArticleFAQ(models.Model):
    """Вопросы и ответы для FAQ-схемы (schema.org/FAQPage)."""
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order']
        verbose_name = 'FAQ-вопрос'
        verbose_name_plural = 'FAQ'

    def __str__(self):
        return self.question


class ArticleImage(models.Model):
    """Дополнительные изображения статьи, вставляемые через [imageN]."""
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='extra_images',
        verbose_name='Статья',
    )
    number = models.PositiveSmallIntegerField(
        verbose_name='Номер',
        help_text='Используйте [imageN] в контенте статьи (N = это число)',
    )
    image = models.ImageField(
        upload_to='catalog/article/',
        verbose_name='Изображение',
    )
    alt = models.CharField(
        max_length=300, blank=True,
        verbose_name='Alt-текст',
        help_text='Описание для SEO и screen-reader',
    )
    title = models.CharField(
        max_length=300, blank=True,
        verbose_name='Title',
        help_text='Всплывающая подсказка (title="...")',
    )
    caption = models.CharField(
        max_length=500, blank=True,
        verbose_name='Подпись',
        help_text='Подпись под изображением (figcaption)',
    )

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'
        ordering = ['number']
        unique_together = [('article', 'number')]

    def __str__(self):
        return f'[image{self.number}] — {self.article.title}'

    def shortcode(self):
        return f'[image{self.number}]'

