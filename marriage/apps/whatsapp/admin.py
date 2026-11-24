from django.contrib import admin
from .models import WhatsAppThread, WhatsAppMessage
class MessageInline(admin.TabularInline):
    model = WhatsAppMessage
    extra = 0
    readonly_fields = ("timestamp",)
@admin.register(WhatsAppThread)
class ThreadAdmin(admin.ModelAdmin):
    change_list_template = "admin/whatsapp/thread_changelist.html"
    list_display = ("customer_name", "customer_phone", "subject", "ticket_status", "is_urgent", "updated_at")
    list_filter = ("ticket_status", "is_urgent")
    search_fields = ("customer_name", "customer_phone", "subject")
    inlines = [MessageInline]
    def has_add_permission(self, request): return False
