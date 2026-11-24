from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

class StaffMember(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        ON_DUTY = "ON_DUTY", "On duty"
        DROP_IN_PROGRESS = "DROP_IN_PROGRESS", "Drop in progress"
        COMPLETED = "COMPLETED", "Completed"
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="staff_profile")
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=80)
    is_female = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    home_drop_location = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return f"{self.full_name} — {self.role}"

class StaffShift(models.Model):
    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="shifts")
    booking = models.ForeignKey("bookings.Booking", on_delete=models.PROTECT, related_name="staff_shifts")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    requires_safety_drop = models.BooleanField(default=False)
    escort_vehicle_number = models.CharField(max_length=32, blank=True)
    driver_name = models.CharField(max_length=120, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    bodyguard_name = models.CharField(max_length=120, blank=True)
    safely_dropped_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="assigned_staff_shifts")
    bodyguard_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="protected_staff_shifts")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ("starts_at",)
        indexes = [models.Index(fields=["staff", "starts_at", "ends_at"])]
    def clean(self):
        if self.ends_at <= self.starts_at: raise ValidationError("Shift end must be after start.")
        if self.staff_id and self.staff.is_female and any(word in self.staff.role.lower() for word in ("catering", "hospitality")):
            self.requires_safety_drop = True
        if self.safely_dropped_at and self.requires_safety_drop and not all([self.escort_vehicle_number, self.driver_name, self.driver_phone, self.bodyguard_name]):
            raise ValidationError("Vehicle, driver and certified bodyguard details are required before safe-drop verification.")
    def __str__(self): return f"{self.staff} on {self.starts_at:%Y-%m-%d %H:%M}"

class EmployeeAttendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LEAVE = "LEAVE", "On leave"
    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="attendance_records")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    note = models.CharField(max_length=240, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="recorded_attendance")
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ("staff__full_name",)
        constraints = [models.UniqueConstraint(fields=["staff", "date"], name="unique_staff_attendance_per_day")]
    def __str__(self): return f"{self.staff} · {self.date} · {self.get_status_display()}"
