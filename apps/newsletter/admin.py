from django.contrib import admin
from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'subscribed_at', 'consent_given_at')
    list_filter = ('is_active',)
    search_fields = ('email',)
    readonly_fields = ('token', 'subscribed_at', 'consent_given_at', 'ip_address')
