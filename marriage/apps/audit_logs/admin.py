from django.contrib import admin
from .models import AccessLog
@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "object_type", "object_id", "ip_address", "created_at")
    list_filter = ("action", "object_type", "created_at")
    readonly_fields = tuple(f.name for f in AccessLog._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
