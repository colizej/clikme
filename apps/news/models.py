from django.db import models
from django.utils import timezone
from apps.core.utils.image_utils import process_image_field


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
    keywords = models.CharField(
        max_length=500, blank=True,
        help_text='Ключевые слова через запятую (фильтр). Пусто = брать всё.'
    )
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

    TAG_CHOICES = [
        ('актуально', 'Актуально'),
        ('интересно', 'Интересно'),
        ('экономика', 'Экономика'),
        ('туризм', 'Туризм'),
        ('политика', 'Политика'),
        ('спорт', 'Спорт'),
        ('культура', 'Культура'),
        ('технологии', 'Технологии'),
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
    body = models.TextField(blank=True, help_text='HTML-контент (генерируется из body_md при сохранении)')

    image_url = models.URLField(blank=True, max_length=800)
    image = models.ImageField(upload_to='news/', blank=True)

    # Markdown-источник (редактируется вручную или генерируется из HTML)
    body_md = models.TextField(
        blank=True,
        verbose_name='Контент (Markdown)',
        help_text='Редактируйте перевод здесь. HTML в «body» генерируется автоматически при сохранении.',
    )
    # Флаг: True → fetch_news и translate_news не перезапишут контент
    is_edited = models.BooleanField(
        default=False,
        verbose_name='Отредактировано вручную',
        help_text='Если включено — автоматический fetch/перевод не перезапишет контент.',
    )

    ai_processed = models.BooleanField(default=False)
    ai_model_used = models.CharField(max_length=50, blank=True)

    tag = models.CharField(
        max_length=20, choices=TAG_CHOICES, blank=True, default='',
        verbose_name='Тег',
        help_text='Отображается на карточке новости вместо источника.',
    )

    status = models.CharField(max_length=15, choices=STATUSES, default=DRAFT)
    telegram_message_id = models.CharField(max_length=50, blank=True)

    views_count = models.PositiveIntegerField(default=0)

    fetched_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-fetched_at']

    def __str__(self):
        return self.title

    @property
    def is_new(self):
        if not self.published_at:
            return False
        return (timezone.now() - self.published_at).total_seconds() < 48 * 3600

    def save(self, *args, **kwargs):
        # Если есть body_md — рендерим его в body
        if self.body_md:
            self.render_body()
        super().save(*args, **kwargs)
        if self.image and self.image.name and not self.image.name.endswith('.webp'):
            process_image_field(self.image)
            self.save(update_fields=['image'])

    def render_body(self):
        """Рендерит body_md → body (Markdown → HTML)."""
        import markdown
        self.body = markdown.markdown(
            self.body_md,
            extensions=['extra', 'nl2br'],
        )

    def get_absolute_url(self):
        return f'/news/{self.slug}/'

    @property
    def reading_time(self):
        import re
        text = re.sub(r'<[^>]+>', ' ', self.body or self.summary or '')
        words = len(text.split())
        minutes = max(1, round(words / 200))
        return minutes


# ── Signals ───────────────────────────────────────────────────────────────────

import os
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(pre_save, sender=NewsItem)
def _delete_old_image_on_change(sender, instance, **kwargs):
    """Удаляет старый файл картинки при замене на новый."""
    if not instance.pk:
        return
    try:
        old = NewsItem.objects.get(pk=instance.pk)
    except NewsItem.DoesNotExist:
        return
    if old.image and old.image != instance.image:
        if os.path.isfile(old.image.path):
            os.remove(old.image.path)


@receiver(post_delete, sender=NewsItem)
def _delete_image_on_delete(sender, instance, **kwargs):
    """Удаляет файл картинки при удалении NewsItem."""
    if instance.image:
        try:
            if os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
        except Exception:
            pass


@receiver(post_save, sender=NewsItem)
def auto_send_to_telegram(sender, instance, created, **kwargs):
    """
    При сохранении новости со статусом PUBLISHED + published_at <= now
    и telegram_message_id пустым — автоматически отправляет в канал.
    """
    if instance.status != NewsItem.PUBLISHED:
        return
    if instance.telegram_message_id:
        return  # уже отправлено
    if instance.published_at and instance.published_at > timezone.now():
        return  # отложенная публикация — не отправлять пока
    try:
        from apps.news.telegram import send_news_item
        ok, result = send_news_item(instance)
        if ok:
            # update_fields чтобы не вызвать рекурсию
            NewsItem.objects.filter(pk=instance.pk).update(telegram_message_id=result)
    except Exception:
        pass  # не ломаем сохранение при ошибке Telegram
