from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AdminSplitDateTime
from django.forms import SplitDateTimeField
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import NewsSource, NewsItem


class NewsItemForm(forms.ModelForm):
    class Meta:
        model = NewsItem
        fields = '__all__'


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'source_language', 'keywords_preview',
                    'needs_translation', 'is_active', 'last_fetched_at')
    list_filter = ('source_type', 'source_language', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name', 'url')

    @admin.display(description='Ключевые слова')
    def keywords_preview(self, obj):
        if not obj.keywords:
            return '—'
        kws = [k.strip() for k in obj.keywords.split(',') if k.strip()]
        return ', '.join(kws[:5]) + ('…' if len(kws) > 5 else '')


# ── Admin actions ─────────────────────────────────────────────────────────────

@admin.action(description='✅ Опубликовать + Telegram')
def publish_selected(modeladmin, request, queryset):
    items = list(queryset.filter(status__in=[NewsItem.DRAFT, NewsItem.REJECTED]))
    now = timezone.now()
    ok = 0
    for item in items:
        item.status = NewsItem.PUBLISHED
        if not item.published_at:
            item.published_at = now
        item.save()  # триггерит сигнал auto_send_to_telegram в models.py
        ok += 1
    modeladmin.message_user(request, f'✅ Опубликовано и отправлено в Telegram: {ok}')


@admin.action(description='🗑 Отклонить выбранные')
def reject_selected(modeladmin, request, queryset):
    updated = queryset.exclude(status=NewsItem.REJECTED).update(status=NewsItem.REJECTED)
    modeladmin.message_user(request, f'Отклонено: {updated}')


@admin.action(description='↩️ Вернуть в черновики')
def to_draft(modeladmin, request, queryset):
    updated = queryset.update(status=NewsItem.DRAFT)
    modeladmin.message_user(request, f'Возвращено в черновики: {updated}')


@admin.action(description='🌐 Перевести выбранные')
def translate_selected(modeladmin, request, queryset):
    import subprocess
    import sys
    from django.conf import settings

    ids = list(queryset.values_list('pk', flat=True))
    for pk in ids:
        subprocess.Popen(
            [sys.executable, 'manage.py', 'translate_news', f'--id={pk}', '--force'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=settings.BASE_DIR,
        )
    modeladmin.message_user(request, f'⏳ Перевод запущен в фоне для {len(ids)} новостей — обновите страницу через минуту')


@admin.action(description='📤 Отправить в Telegram')
def send_to_telegram(modeladmin, request, queryset):
    from apps.news.telegram import send_news_item
    ok = fail = skip = 0
    for item in queryset:
        if item.telegram_message_id:
            skip += 1
            continue
        success, result = send_news_item(item)
        if success:
            item.__class__.objects.filter(pk=item.pk).update(telegram_message_id=result)
            ok += 1
        else:
            fail += 1
            modeladmin.message_user(request, f'❌ [{item.pk}] {result}', messages.ERROR)
    parts = []
    if ok:
        parts.append(f'✅ Отправлено: {ok}')
    if skip:
        parts.append(f'⏭ Уже в канале: {skip}')
    if parts:
        modeladmin.message_user(request, ' | '.join(parts))


@admin.action(description='🔁 Переотправить в Telegram (сбросить и отправить заново)')
def resend_to_telegram(modeladmin, request, queryset):
    from apps.news.telegram import send_news_item
    ok = fail = 0
    for item in queryset:
        item.__class__.objects.filter(pk=item.pk).update(telegram_message_id='')
        item.refresh_from_db()
        success, result = send_news_item(item)
        if success:
            item.__class__.objects.filter(pk=item.pk).update(telegram_message_id=result)
            ok += 1
        else:
            fail += 1
            modeladmin.message_user(request, f'❌ [{item.pk}] {result}', messages.ERROR)
    if ok:
        modeladmin.message_user(request, f'✅ Переотправлено: {ok}')


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    form = NewsItemForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'published_at':
            return SplitDateTimeField(
                required=False,
                label='Дата публикации',
                widget=AdminSplitDateTime(),
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    list_display = ('title_short', 'thumb', 'source', 'tag', 'status_badge',
                    'ai_processed', 'is_edited', 'tg_sent', 'fetched_at', 'published_at')
    list_filter = ('status', 'tag', 'ai_processed', 'is_edited', 'source')
    search_fields = ('title', 'slug', 'summary')
    readonly_fields = ('ai_processed', 'ai_model_used', 'telegram_message_id',
                       'source_url', 'fetched_at', 'title_original', 'summary_original')
    date_hierarchy = 'fetched_at'
    ordering = ['-fetched_at']
    actions = [reject_selected, to_draft, translate_selected, resend_to_telegram]
    change_list_template = 'admin/news/newsitem/change_list.html'

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'status', 'tag', 'is_edited'),
        }),
        ('Оригинал', {
            'classes': ('collapse',),
            'fields': ('title_original', 'summary_original'),
        }),
        ('Контент', {
            'fields': ('summary', 'body_md'),
        }),
        ('Медиа', {
            'fields': ('image', 'image_url'),
        }),
        ('Источник и SEO', {
            'fields': ('source', 'source_url', 'ai_processed', 'ai_model_used',
                       'telegram_message_id', 'fetched_at', 'published_at'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Если редактор изменил body_md — помечаем как отредактировано вручную
        if change and 'body_md' in form.changed_data:
            obj.is_edited = True
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('fetch/', self.admin_site.admin_view(self._fetch_view), name='news_newsitem_fetch'),
            path('translate/', self.admin_site.admin_view(self._translate_view), name='news_newsitem_translate'),
            path('logs/', self.admin_site.admin_view(self._logs_view), name='news_newsitem_logs'),
            path('logs/data/', self.admin_site.admin_view(self._logs_data), name='news_newsitem_logs_data'),
        ]
        return custom + urls

    def _log_path(self, name):
        from django.conf import settings
        log_dir = settings.BASE_DIR / 'logs'
        log_dir.mkdir(exist_ok=True)
        return log_dir / f'{name}.log'

    def _run_bg(self, cmd_args, log_name):
        import subprocess, sys
        from django.conf import settings
        log_file = open(self._log_path(log_name), 'w', encoding='utf-8')
        subprocess.Popen(
            [sys.executable, 'manage.py'] + cmd_args,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=settings.BASE_DIR,
        )

    def _fetch_view(self, request):
        self._run_bg(['fetch_news'], 'fetch_news')
        self.message_user(request, '⏳ Парсинг запущен — смотрите лог', messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:news_newsitem_logs'))

    def _translate_view(self, request):
        self._run_bg(['translate_news'], 'translate_news')
        self.message_user(request, '⏳ Перевод запущен — смотрите лог', messages.SUCCESS)
        return HttpResponseRedirect(reverse('admin:news_newsitem_logs'))

    def _logs_view(self, request):
        from django.shortcuts import render
        return render(request, 'admin/news/logs.html', {
            'title': 'Логи фоновых задач',
            'opts': self.model._meta,
        })

    def _logs_data(self, request):
        from django.http import JsonResponse
        result = {}
        for name, label in [
            ('fetch_news', 'Парсинг новостей'),
            ('translate_news', 'Перевод'),
            ('publish_scheduled', 'Публикация в Telegram'),
        ]:
            log_file = self._log_path(name)
            if log_file.exists():
                lines = log_file.read_text(encoding='utf-8', errors='replace').splitlines()
                result[name] = {
                    'label': label,
                    'lines': lines[-100:],  # последние 100 строк
                    'mtime': log_file.stat().st_mtime,
                }
            else:
                result[name] = {'label': label, 'lines': [], 'mtime': 0}
        return JsonResponse(result)

    @admin.display(description='Заголовок')
    def title_short(self, obj):
        return obj.title[:80] + ('…' if len(obj.title) > 80 else '')

    @admin.display(description='Фото')
    def thumb(self, obj):
        url = obj.image.url if obj.image else obj.image_url
        if url:
            return format_html('<img src="{}" style="height:40px;border-radius:4px;">', url)
        return '—'

    @admin.display(description='Статус')
    def status_badge(self, obj):
        colors = {
            NewsItem.DRAFT: '#888',
            NewsItem.PUBLISHED: '#22c55e',
            NewsItem.REJECTED: '#ef4444',
        }
        labels = {
            NewsItem.DRAFT: 'Черновик',
            NewsItem.PUBLISHED: 'Опубликовано',
            NewsItem.REJECTED: 'Отклонено',
        }
        color = colors.get(obj.status, '#888')
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>', color, label
        )

    @admin.display(description='TG')
    def tg_sent(self, obj):
        if obj.telegram_message_id:
            return format_html('<span style="color:{};font-weight:600">✓</span>', '#22c55e')
        return format_html('<span style="color:{}">—</span>', '#ccc')
