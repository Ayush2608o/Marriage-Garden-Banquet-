from django.contrib import admin

from .models import Enquiry, Venue


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "capacity", "starting_price", "featured", "is_active")
    list_filter = ("is_active", "featured", "location")
    search_fields = ("name", "location", "description")


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("reference", "name", "venue", "event_type", "event_date", "phone", "created_at", "status")
    list_filter = ("status", "event_type", "venue", "created_at")
    search_fields = ("name", "email", "phone", "notes", "venue__name")
    readonly_fields = ("created_at",)
    list_editable = ("status",)
