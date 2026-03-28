from django.contrib import admin
from django.utils.html import format_html
from .models import Partner, AdSlot, AdUnit, AdClick, ArticleAdPlacement


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(AdSlot)
class AdSlotAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'slot_type', 'is_active', 'order']
    list_filter = ['slot_type', 'is_active']
    search_fields = ['name', 'slug']
    ordering = ['order', 'name']


@admin.register(AdUnit)
class AdUnitAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'partner', 'ad_type', 'slot_type', 
        'priority', 'is_active', 'impressions_count', 'clicks_count'
    ]
    list_filter = ['ad_type', 'slot_type', 'partner', 'is_active', 'is_permanent']
    search_fields = ['name', 'partner__name']
    readonly_fields = ['impressions_count', 'clicks_count', 'created_at', 'updated_at']
    ordering = ['-priority', '-created_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('partner', 'name', 'ad_type', 'slot_type', 'is_active')
        }),
        ('Widget', {
            'fields': ('widget_code', 'widget_width', 'widget_height'),
            'classes': ('collapse',),
        }),
        ('Баннер', {
            'fields': ('image',),
            'classes': ('collapse',),
        }),
        ('Текстовая ссылка', {
            'fields': ('text',),
            'classes': ('collapse',),
        }),
        ('Ссылка (для баннера и текста)', {
            'fields': ('link',),
            'classes': ('collapse',),
        }),
        ('Контент', {
            'fields': ('intro_text',)
        }),
        ('Период показа', {
            'fields': ('is_permanent', 'start_date', 'end_date')
        }),
        ('Приоритет и лимиты', {
            'fields': ('priority', 'max_impressions')
        }),
        ('Статистика', {
            'fields': ('impressions_count', 'clicks_count'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('partner')


@admin.register(ArticleAdPlacement)
class ArticleAdPlacementAdmin(admin.ModelAdmin):
    list_display = ['article', 'slot', 'ad_unit', 'position', 'is_active', 'order']
    list_filter = ['slot', 'is_active', 'position']
    search_fields = ['article__title', 'slot__name']
    autocomplete_fields = ['article', 'slot', 'ad_unit']
    ordering = ['article', 'order']


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    list_display = ['ad_unit', 'article', 'ip_address', 'created_at']
    list_filter = ['created_at', 'ad_unit__partner']
    search_fields = ['ad_unit__name', 'ip_address']
    readonly_fields = ['ad_unit', 'article', 'ip_address', 'user_agent', 'referer', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
