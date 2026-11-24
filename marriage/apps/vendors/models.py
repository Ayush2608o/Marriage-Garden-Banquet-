from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from apps.venues.validators import validate_upload_extension

class Vendor(models.Model):
    class Category(models.TextChoices):
        PHOTOGRAPHER = "PHOTOGRAPHER", "Photographer"
        DJ = "DJ", "DJ & sound"
        CATERING = "CATERING", "Catering contractor"
        WHOLESALE = "WHOLESALE", "Wholesale / kirana"
        PRINTER = "PRINTER", "Wedding card printer"
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="vendor_profiles")
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=24, choices=Category.choices, db_index=True)
    description = models.TextField(blank=True)
    city = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    starting_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    years_experience = models.PositiveSmallIntegerField(default=0)
    verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name} ({self.get_category_display()})"

class VendorPortfolioImage(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="portfolio")
    image = models.FileField(upload_to="vendors/portfolio/", validators=[validate_upload_extension])
    caption = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
