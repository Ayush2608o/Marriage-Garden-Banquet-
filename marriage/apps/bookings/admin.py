from django.contrib import admin
from .models import Booking
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("venue", "customer", "event_date", "slot", "guest_count", "status", "is_demo")
    list_filter = ("status", "event_date", "slot", "is_demo")
    search_fields = ("venue__name", "customer__username", "customer__phone")
    readonly_fields = ("created_at", "updated_at")
