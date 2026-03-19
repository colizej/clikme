from django.contrib import admin
from .models import NewsSource, NewsItem


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'source_language', 'needs_translation', 'is_active', 'last_fetched_at')
    list_filter = ('source_type', 'source_language', 'is_active', 'needs_translation')
    list_editable = ('is_active',)


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'status', 'ai_processed', 'telegram_message_id', 'published_at')
    list_filter = ('status', 'ai_processed', 'source')
    list_editable = ('status',)
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('ai_processed', 'ai_model_used', 'telegram_message_id', 'source_url')
    date_hierarchy = 'published_at'
