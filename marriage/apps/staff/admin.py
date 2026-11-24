from django.contrib import admin
from apps.audit_logs.models import AccessLog
from .models import EmployeeAttendance, StaffMember, StaffShift

class SensitiveAccessAdmin(admin.ModelAdmin):
    def log_access(self, request, obj=None):
        AccessLog.objects.create(actor=request.user, action="VIEW_STAFF_SAFETY_DETAILS" if obj else "VIEW_STAFF_CONTACT_LIST", object_type=self.model.__name__, object_id=str(obj.pk) if obj else "list", ip_address=request.META.get("REMOTE_ADDR"))
    def changelist_view(self, request, extra_context=None):
        self.log_access(request)
        return super().changelist_view(request, extra_context)
    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj: self.log_access(request, obj)
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(StaffMember)
class StaffMemberAdmin(SensitiveAccessAdmin):
    list_display = ("full_name", "role", "status", "is_female", "is_active")
    list_filter = ("status", "role", "is_female")
    search_fields = ("full_name", "phone")
@admin.register(StaffShift)
class StaffShiftAdmin(SensitiveAccessAdmin):
    list_display = ("staff", "booking", "starts_at", "ends_at", "requires_safety_drop", "safely_dropped_at")
    list_filter = ("requires_safety_drop", "starts_at")

@admin.register(EmployeeAttendance)
class EmployeeAttendanceAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "status", "note", "recorded_by", "updated_at")
    list_filter = ("date", "status")
    search_fields = ("staff__full_name", "staff__role")
