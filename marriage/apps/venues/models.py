from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.db import models
from .validators import validate_upload_extension


class Venue(models.Model):
    """A wedding space presented in the public venue collection."""

    name = models.CharField(max_length=120)
    class VenueType(models.TextChoices):
        GARDEN = "GARDEN", "Marriage garden"
        RESORT = "RESORT", "Wedding resort"
        COMPLEX = "COMPLEX", "Multi-complex halls"
        DUPLEX = "DUPLEX", "Duplex banquet"
        HALL = "HALL", "Single hall"
    venue_type = models.CharField(max_length=16, choices=VenueType.choices, default=VenueType.GARDEN)
    location = models.CharField(max_length=160)
    state = models.CharField(max_length=100, blank=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    area = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.TextField()
    capacity = models.PositiveIntegerField(default=250)
    starting_price = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    model_3d = models.FileField(upload_to="venues/models/", blank=True, validators=[FileExtensionValidator(["glb"]), validate_upload_extension])
    image_url = models.URLField(blank=True)
    featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-featured", "name")

    def __str__(self) -> str:
        return self.name

    @property
    def final_price(self):
        from decimal import Decimal
        return (Decimal(self.starting_price) * (Decimal(100) - self.discount_percent) / Decimal(100)).quantize(Decimal("0.01"))


class Enquiry(models.Model):
    """A couple's request for a personal wedding consultation."""

    class EventType(models.TextChoices):
        WEDDING = "wedding", "Wedding celebration"
        RECEPTION = "reception", "Reception"
        ENGAGEMENT = "engagement", "Engagement"
        OTHER = "other", "Another occasion"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CONTACTED = "contacted", "Contacted"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=24)
    venue = models.ForeignKey(
        Venue,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="enquiries",
    )
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.WEDDING)
    event_date = models.DateField(blank=True, null=True)
    guest_count = models.PositiveIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(10000)])
    notes = models.TextField(blank=True, max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "enquiries"

    def __str__(self) -> str:
        return f"{self.name} · {self.get_event_type_display()}"

    @property
    def reference(self):
        return f"RV-{self.pk:06d}"
