from django.contrib import admin
from .models import Vendor, VendorPortfolioImage
class PortfolioInline(admin.TabularInline):
    model = VendorPortfolioImage
    extra = 0
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "city", "starting_price", "verified", "is_active")
    list_filter = ("category", "city", "verified", "is_active")
    search_fields = ("name", "city", "phone")
    inlines = [PortfolioInline]
