from django.db import transaction
from django.utils import timezone
from .models import StaffMember, StaffShift

@transaction.atomic
def reserve_staff(*, staff_id, booking, starts_at, ends_at, assigned_by=None):
    staff = StaffMember.objects.select_for_update().get(pk=staff_id, is_active=True)
    conflict = StaffShift.objects.filter(staff=staff, starts_at__lt=ends_at, ends_at__gt=starts_at).exists()
    if staff.status != StaffMember.Status.AVAILABLE or conflict:
        raise ValueError("Staff member is not available for this shift.")
    shift = StaffShift(staff=staff, booking=booking, starts_at=starts_at, ends_at=ends_at, assigned_by=assigned_by)
    shift.full_clean()
    shift.save()
    staff.status = StaffMember.Status.RESERVED
    staff.save(update_fields=["status"])
    return shift

@transaction.atomic
def complete_shift(shift_id):
    shift = StaffShift.objects.select_for_update().select_related("staff").get(pk=shift_id)
    shift.full_clean()
    if shift.requires_safety_drop and shift.safely_dropped_at is None:
        raise ValueError("Mark the staff member safely dropped and complete safety details first.")
    shift.staff.status = StaffMember.Status.COMPLETED
    shift.staff.save(update_fields=["status"])
    return shift
