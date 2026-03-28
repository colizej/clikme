from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Partner, AdSlot, AdUnit, AdClick


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(AdSlot)
class AdSlotAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'page_type', 'position', 'is_active', 'order']
    list_filter = ['page_type', 'is_active']
    search_fields = ['name', 'slug']
    ordering = ['page_type', 'order', 'name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AdUnit)
class AdUnitAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'partner', 'ad_type', 'slot', 
        'target_display', 'priority', 'is_active', 'impressions_count'
    ]
    list_filter = ['ad_type', 'slot', 'partner', 'is_active', 'is_permanent']
    search_fields = ['name', 'partner__name', 'target_article__title']
    readonly_fields = ['impressions_count', 'clicks_count', 'created_at', 'updated_at']
    autocomplete_fields = ['slot', 'target_article', 'target_news', 'target_categories']
    ordering = ['-priority', '-created_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('partner', 'name', 'ad_type', 'slot', 'is_active')
        }),
        ('Таргетинг', {
            'fields': ('target_article', 'target_news'),
            'description': 'Оставьте пустым для показа на всех страницах указанного типа. Конкретная страница имеет приоритет над "всеми".'
        }),
        ('Widget', {
            'fields': ('widget_code', 'widget_width', 'widget_height'),
            'classes': ('collapse',),
        }),
        ('Баннер статичный', {
            'fields': ('image', 'link'),
            'classes': ('collapse',),
        }),
        ('HTML/JS код (динамические баннеры)', {
            'fields': ('html_code',),
            'description': 'Google Ads, Yandex, и т.д.',
            'classes': ('collapse',),
        }),
        ('Текстовая ссылка', {
            'fields': ('text',),
            'classes': ('collapse',),
        }),
        ('Контент', {
            'fields': ('intro_text',)
        }),
        ('Период показа', {
            'fields': ('is_permanent', 'start_date', 'end_date')
        }),
        ('Приоритет и лимиты', {
            'fields': ('priority', 'max_impressions', 'target_categories')
        }),
        ('Статистика', {
            'fields': ('impressions_count', 'clicks_count'),
            'classes': ('collapse',),
        }),
    )
    
    def target_display(self, obj):
        if obj.target_article:
            return f"Статья: {obj.target_article.title[:30]}..."
        if obj.target_news:
            return f"Новость: {obj.target_news.title[:30]}..."
        return "Все страницы"
    target_display.short_description = "Показывать в"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('partner', 'slot')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.slot:
            existing = AdUnit.objects.filter(
                slot=obj.slot,
                is_active=True
            ).exclude(pk=obj.pk).exists()
            if existing:
                from django.contrib import messages
                messages.warning(request, 
                    f'Внимание: позиция "{obj.slot.name}" уже занята другим активным объявлением!')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['occupied_slots'] = self._get_occupied_slots()
        return super().change_view(request, object_id, form_url, extra_context)
    
    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['occupied_slots'] = self._get_occupied_slots()
        return super().add_view(request, form_url, extra_context)
    
    def _get_occupied_slots(self):
        return list(AdUnit.objects.filter(
            is_active=True, 
            slot__isnull=False
        ).values_list('slot_id', flat=True))


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
