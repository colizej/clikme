from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Tag, Article, ArticleFAQ, ArticleImage


# ── Markdown widget (EasyMDE via CDN) ────────────────────────────────────────

class MarkdownTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {})['class'] = 'easymde-field'
        super().__init__(*args, **kwargs)


class ArticleForm(forms.ModelForm):
    content_md = forms.CharField(
        widget=MarkdownTextarea(attrs={'rows': 30}),
        required=False,
        label='Контент (Markdown)',
    )

    class Meta:
        model = Article
        fields = '__all__'


# ── Inlines ───────────────────────────────────────────────────────────────────

class FAQInline(admin.TabularInline):
    model = ArticleFAQ
    extra = 1
    fields = ('order', 'question', 'answer')


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1
    fields = ('number', 'image', 'image_preview', 'alt', 'title', 'caption')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;border-radius:6px;">'
                '<br><code style="font-size:11px;background:#f3f4f6;padding:2px 6px;'
                'border-radius:4px;color:#e85d26">[image{}]</code>',
                obj.image.url, obj.number,
            )
        from django.utils.safestring import mark_safe
        return mark_safe('<span style="color:#aaa;font-size:11px">Нет изображения</span>')
    image_preview.short_description = 'Превью / шорткод'


# ── Admins ────────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    form = ArticleForm
    inlines = [ArticleImageInline]

    list_display = ('title', 'category', 'is_published', 'is_featured', 'published_at', 'views_count')
    list_filter = ('is_published', 'is_featured', 'noindex', 'category')
    list_editable = ('is_published', 'is_featured')
    search_fields = ('title', 'slug', 'meta_keywords')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    filter_horizontal = ('tags',)
    date_hierarchy = 'published_at'
    readonly_fields = ('views_count', 'content')

    def save_related(self, request, form, formsets, change):
        """Перерендеривает content после сохранения инлайн-изображений."""
        super().save_related(request, form, formsets, change)
        obj = form.instance
        obj.render_content()
        Article.objects.filter(pk=obj.pk).update(content=obj.content)

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'slug', 'subtitle', 'category', 'tags', 'image', 'image_alt'),
        }),
        ('Контент', {
            'fields': ('short_description', 'content_md'),
            'description': (
                'Пишите в <strong>Markdown</strong>. '
                'Вставляйте изображения через <code>[image1]</code>, <code>[image2]</code> и т.д. '
                '(добавьте картинки в блоке «Изображения» ниже). '
                'HTML генерируется автоматически при сохранении.'
            ),
        }),
        ('Сгенерированный HTML (readonly)', {
            'fields': ('content',),
            'classes': ('collapse',),
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords', 'noindex'),
            'classes': ('collapse',),
            'description': (
                '<b>meta_title</b> — до 60 символов. '
                '<b>meta_description</b> — до 160 символов. '
                '<b>meta_keywords</b> — через запятую.'
            ),
        }),
        ('Публикация', {
            'fields': ('is_published', 'is_featured', 'published_at', 'author', 'views_count'),
        }),
    )

    class Media:
        css = {
            'all': [
                'https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.css',
                'css/admin-markdown.css',
            ],
        }
        js = [
            'https://cdn.jsdelivr.net/npm/easymde/dist/easymde.min.js',
            'js/admin_md.js',
        ]

