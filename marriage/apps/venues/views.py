import logging

from django.contrib import messages
from django.db import DatabaseError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import EnquiryForm
from .models import Enquiry, Venue
from .notifications import notify_new_enquiry

logger = logging.getLogger(__name__)


@never_cache
def home(request):
    venues = Venue.objects.filter(is_active=True)[:3]
    venue_param = request.GET.get("venue", "")
    selected_venue = None
    if venue_param.isdigit() and len(venue_param) <= 18:
        selected_venue = Venue.objects.filter(pk=int(venue_param), is_active=True).first()
    return render(
        request,
        "customer/home.html",
        {"venues": venues, "selected_venue": selected_venue},
    )

def policy(request, policy):
    copy = {
        "privacy": ("Privacy Policy", "Information we collect: account name, email, phone and password hash; enquiry and booking event type, dates, guest count and notes; WhatsApp support messages and attachments; vendor business and contact details; and, for staff safety operations, staff contact, shift, driver, vehicle and drop-location details. Passwords are stored using Django's password hashing system.\n\nWhy we use it: to answer enquiries, check availability, manage bookings and payments, arrange vendor and staff services, operate customer support, protect people and prevent fraud, maintain records required for legal or accounting purposes, and meet legal obligations. Marketing messages are optional and require a separate affirmative choice.\n\nSharing and safeguards: data is available only to personnel who need it for their role. Booking details may be shared with selected venues, vendors or staff to deliver requested services. When configured, WhatsApp Cloud API and payment, hosting or storage providers process the data needed to provide those services. Staff home-drop information is restricted to authorized operations admins and the assigned bodyguard; access is logged. We use access controls, secure password hashing, CSRF protection and upload type/size checks.\n\nRetention and your choices: we retain information while needed to provide the service, resolve issues, protect safety, and satisfy applicable legal and accounting requirements, then delete or de-identify it when appropriate. You may request access, correction, erasure, grievance redressal or withdraw consent where processing relies on consent by emailing privacy@royalvenue.in. Withdrawal does not affect processing already lawfully carried out or processing required by law. We will verify the requester before acting.\n\nThis notice applies to Royal Venue's website and booking operations. For questions or grievances, contact privacy@royalvenue.in. Replace this address with the monitored Data Protection contact before launch."),
        "terms": ("Terms of Service", "Venue dates and prices are subject to written confirmation and availability. A booking becomes confirmed only after an authorized Royal Venue representative confirms the terms and any required advance payment. Quotes state their validity period. Customers must provide accurate event information and follow venue safety, capacity and conduct rules. Cancellation, refund, force majeure and dispute terms will be provided in the event-specific agreement. Contact support to request a copy before paying."),
        "safety": ("Staff & Women Safety Policy", "Royal Venue records safety requirements for eligible late-night catering and hospitality shifts. Such shifts require an assigned escort vehicle, identified driver and certified bodyguard or bouncer, and a verified safe-drop timestamp before the shift can be completed in our operations system. Staff may report a safety concern to the duty manager at any time. Home drop details are restricted to authorized admins and the assigned bodyguard, and each recorded access is logged."),
    }
    title, body = copy[policy]
    return render(request, "customer/policy.html", {"title": title, "body": body})


@require_POST
def enquire(request):
    wants_json = (
        "application/json" in request.headers.get("Accept", "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    form = EnquiryForm(request.POST)
    if not form.is_valid():
        if wants_json:
            return JsonResponse({"error": "validation_error", "errors": form.errors.get_json_data()}, status=400)
        messages.error(request, "Please check your enquiry details and try again.")
        return redirect(f"{reverse('home')}#contact")

    try:
        with transaction.atomic():
            enquiry = form.save()
            transaction.on_commit(
                lambda enquiry_id=enquiry.pk: notify_new_enquiry(enquiry_id),
                robust=True,
            )
    except DatabaseError:
        logger.exception("Unable to save a Royal Venue enquiry")
        if wants_json:
            return JsonResponse(
                {"error": "save_failed", "message": "We could not save your enquiry. Please try again."},
                status=503,
            )
        messages.error(request, "We could not save your enquiry. Please try again.")
        return redirect(f"{reverse('home')}#contact")

    confirmation = f"Thank you. Your enquiry reference is {enquiry.reference}."
    if wants_json:
        return JsonResponse(
            {
                "message": confirmation,
                "id": enquiry.pk,
                "reference_id": enquiry.reference,
                "status": enquiry.status,
                "created_at": enquiry.created_at.isoformat(),
                "venue_id": enquiry.venue_id,
            },
            status=201,
        )
    messages.success(request, confirmation)
    return redirect(f"{reverse('home')}#contact")
