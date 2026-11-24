from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from apps.audit_logs.models import AccessLog
from .models import StaffShift

@require_GET
def sensitive_shift_details(request, shift_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "authentication required"}, status=401)
    shift = get_object_or_404(StaffShift.objects.select_related("staff", "bodyguard_user"), pk=shift_id)
    permitted = request.user.is_staff or request.user.is_superuser or shift.bodyguard_user_id == request.user.pk
    if not permitted:
        return JsonResponse({"error": "forbidden"}, status=403)
    AccessLog.objects.create(actor=request.user, action="VIEW_STAFF_SAFETY_DETAILS", object_type="StaffShift", object_id=str(shift.pk), ip_address=request.META.get("REMOTE_ADDR"))
    return JsonResponse({"staff_name": shift.staff.full_name, "staff_phone": shift.staff.phone, "home_drop_location": shift.staff.home_drop_location, "escort_vehicle_number": shift.escort_vehicle_number, "driver_name": shift.driver_name, "driver_phone": shift.driver_phone, "bodyguard_name": shift.bodyguard_name, "safely_dropped_at": shift.safely_dropped_at})
