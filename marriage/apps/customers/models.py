from django.conf import settings
from django.db import models

class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile")
    city = models.CharField(max_length=100, blank=True)
    marketing_consent = models.BooleanField(default=False)
    consent_updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Customer profile: {self.user}"
