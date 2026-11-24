from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from apps.venues.models import Venue

class Booking(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        QUOTED = "QUOTED", "Quoted"
        CONFIRMED = "CONFIRMED", "Confirmed"
        DECLINED = "DECLINED", "Declined"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    venue = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="bookings")
    event_date = models.DateField(db_index=True)
    slot = models.CharField(max_length=32, default="FULL_DAY")
    guest_count = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    notes = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    is_demo = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["venue", "event_date", "slot"], condition=~Q(status__in=["CANCELLED", "DECLINED"]), name="unique_active_venue_slot")]
        ordering = ("-created_at",)
    def clean(self):
        if self.guest_count and self.venue_id and self.guest_count > self.venue.capacity:
            raise ValidationError({"guest_count": "Guest count exceeds this venue's stated capacity."})
    def __str__(self): return f"{self.venue} · {self.event_date} ({self.get_status_display()})"
