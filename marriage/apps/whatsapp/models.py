from django.conf import settings
from django.db import models
from apps.venues.validators import validate_upload_extension

# Threads opened from the customer's "Messages" page use this subject, so staff can tell them apart.
ACCOUNT_CHAT_SUBJECT = "Account chat"

class WhatsAppThread(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        URGENT = "URGENT", "Urgent"
        CLOSED = "CLOSED", "Closed"
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="whatsapp_threads")
    customer_name = models.CharField(max_length=120, blank=True)
    customer_phone = models.CharField(max_length=24, db_index=True)
    subject = models.CharField(max_length=180, blank=True)
    ticket_status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN, db_index=True)
    is_urgent = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "WhatsApp thread"
        verbose_name_plural = "WhatsApp threads"
    def __str__(self): return f"{self.customer_name or self.customer_phone} — {self.subject or 'Support'}"

class WhatsAppMessage(models.Model):
    class Sender(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        ADMIN = "ADMIN", "Admin"
        BOT = "BOT", "Bot"
    thread = models.ForeignKey(WhatsAppThread, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=10, choices=Sender.choices)
    message_text = models.TextField(blank=True)
    media_attachment = models.FileField(upload_to="whatsapp/media/", blank=True, validators=[validate_upload_extension])
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    provider_message_id = models.CharField(max_length=120, blank=True, db_index=True)
    class Meta: ordering = ("timestamp",)
    def __str__(self): return f"{self.sender_type}: {self.message_text[:60]}"
