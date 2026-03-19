from django.contrib import admin
from .models import Vendor, Product


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'city', 'telephone', 'is_active', 'approved')
    list_filter = ('is_active', 'approved', 'city')
    list_editable = ('is_active', 'approved')
    search_fields = ('display_name', 'slug', 'telephone')
    prepopulated_fields = {'slug': ('display_name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'vendor', 'price', 'is_active')
    list_filter = ('is_active', 'vendor')
    list_editable = ('is_active',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('vendor',)
