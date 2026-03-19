from django.contrib import admin
from .models import Category, Tag, Article


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
    list_display = ('title', 'category', 'author', 'is_published', 'is_featured', 'published_at', 'views_count')
    list_filter = ('is_published', 'is_featured', 'noindex', 'category')
    list_editable = ('is_published', 'is_featured')
    search_fields = ('title', 'slug', 'meta_keywords')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)
    filter_horizontal = ('tags',)
    date_hierarchy = 'published_at'
    readonly_fields = ('views_count',)
