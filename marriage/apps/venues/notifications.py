import logging
import smtplib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail

from .models import Enquiry

logger = logging.getLogger(__name__)


def notify_new_enquiry(enquiry_id):
    enquiry = Enquiry.objects.get(pk=enquiry_id)
    logger.info(
        "New Royal Venue enquiry %s: %s, event date %s",
        enquiry.reference,
        enquiry.get_event_type_display(),
        enquiry.event_date or "not specified",
    )
    recipient = settings.ENQUIRY_NOTIFICATION_EMAIL
    if not recipient:
        return

    try:
        send_mail(
            subject=f"New event enquiry {enquiry.reference}",
            message=(
                f"Name: {enquiry.name}\nEmail: {enquiry.email}\nPhone: {enquiry.phone}\n"
                f"Venue: {enquiry.venue.name if enquiry.venue_id else 'Not specified'}\n"
                f"Event: {enquiry.get_event_type_display()}\nDate: {enquiry.event_date or 'Not specified'}\n"
                f"Guests: {enquiry.guest_count or 'Not specified'}\nNotes: {enquiry.notes or 'None'}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except (ImproperlyConfigured, OSError, smtplib.SMTPException, ValueError):
        logger.exception("Could not email notification for enquiry %s", enquiry.reference)
