from django.contrib import admin
from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'noindex', 'sort_order')
    list_filter = ('is_published', 'noindex')
    list_editable = ('is_published',)
    prepopulated_fields = {'slug': ('title',)}
