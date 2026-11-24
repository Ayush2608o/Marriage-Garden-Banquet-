import json
import hashlib
import hmac
import re
import urllib.error
import urllib.request
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from .models import ACCOUNT_CHAT_SUBJECT, WhatsAppThread, WhatsAppMessage

PUBLIC_SUPPORT_SESSION_KEY = "website_support_thread_id"
PUBLIC_SUPPORT_MAX_MESSAGES_PER_MINUTE = 20

def can_manage(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in {"VENUE_OWNER", "SUPERADMIN"}
    )


def parse_json_object(request):
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def valid_phone(phone):
    digits = re.sub(r"\D", "", phone)
    return bool(
        re.fullmatch(r"\+?[0-9][0-9\s().-]{6,23}", phone)
        and 7 <= len(digits) <= 15
    )


@user_passes_test(can_manage)
def inbox(request):
    page = inbox_page(request)
    return render(
        request,
        "owner/whatsapp_inbox.html",
        {"threads": page.object_list, "thread_page": page},
    )


@user_passes_test(can_manage)
@require_GET
def thread_list(request):
    page = inbox_page(request)
    return JsonResponse(
        {
            "threads": [
                {
                    "id": thread.id,
                    "name": thread.customer_name or thread.customer_phone,
                    "phone": thread.customer_phone,
                    "subject": thread.subject or "Support",
                    "unread_count": thread.unread_count,
                    "urgent": thread.is_urgent,
                    "status": thread.ticket_status,
                }
                for thread in page.object_list
            ],
            "page": page.number,
            "num_pages": page.paginator.num_pages,
            "has_previous": page.has_previous(),
            "has_next": page.has_next(),
        }
    )


def inbox_page(request):
    threads = WhatsAppThread.objects.annotate(
        unread_count=Count(
            "messages",
            filter=Q(
                messages__sender_type=WhatsAppMessage.Sender.CUSTOMER,
                messages__is_read=False,
            ),
        )
    ).order_by("-is_urgent", "-unread_count", "-updated_at", "-pk")
    return Paginator(threads, 40).get_page(request.GET.get("page"))

@user_passes_test(can_manage)
def dashboard(request):
    from apps.bookings.models import Booking
    from apps.venues.models import Venue
    from apps.vendors.models import Vendor
    return render(request, "owner/dashboard.html", {"bookings": Booking.objects.count(), "pending_bookings": Booking.objects.filter(status="REQUESTED").count(), "venues": Venue.objects.filter(is_active=True).count(), "vendors": Vendor.objects.filter(is_active=True).count(), "unread": WhatsAppMessage.objects.filter(sender_type="CUSTOMER", is_read=False).count()})

@require_GET
def thread_messages(request, thread_id):
    thread = get_object_or_404(WhatsAppThread, pk=thread_id)
    if not can_manage(request.user) and (not request.user.is_authenticated or thread.customer_id != request.user.pk):
        return JsonResponse({"error": "forbidden"}, status=403)
    if can_manage(request.user):
        thread.messages.filter(sender_type="CUSTOMER", is_read=False).update(is_read=True)
    messages = list(thread.messages.values("id", "sender_type", "message_text", "timestamp", "is_read"))
    return JsonResponse({"thread": {"id": thread.id, "name": thread.customer_name or "Customer", "status": thread.ticket_status, "urgent": thread.is_urgent}, "messages": messages})


def public_support_thread(request, thread_id=None):
    stored_id = request.session.get(PUBLIC_SUPPORT_SESSION_KEY)
    if thread_id is None:
        thread_id = stored_id
    if not thread_id or stored_id != thread_id:
        return None
    thread = WhatsAppThread.objects.filter(pk=thread_id).first()
    if thread is None:
        request.session.pop(PUBLIC_SUPPORT_SESSION_KEY, None)
    return thread


@require_GET
def current_support_thread(request):
    thread = public_support_thread(request)
    return JsonResponse({"thread_id": thread.pk if thread else None})


@require_GET
def public_thread_messages(request, thread_id):
    thread = public_support_thread(request, thread_id)
    if thread is None:
        return JsonResponse({"error": "conversation not found"}, status=404)
    thread.messages.filter(
        sender_type__in=(WhatsAppMessage.Sender.ADMIN, WhatsAppMessage.Sender.BOT),
        is_read=False,
    ).update(is_read=True)
    messages = list(
        thread.messages.order_by("id")
        .values("id", "sender_type", "message_text", "timestamp")[:500]
    )
    return JsonResponse({"messages": messages})


@require_POST
def public_thread_send(request, thread_id):
    thread = public_support_thread(request, thread_id)
    if thread is None:
        return JsonResponse({"error": "conversation not found"}, status=404)
    data = parse_json_object(request)
    if data is None:
        return JsonResponse({"error": "request body must be a JSON object"}, status=400)
    text = data.get("message", "")
    if not isinstance(text, str):
        return JsonResponse({"error": "message must be text"}, status=400)
    text = text.strip()
    if not text:
        return JsonResponse({"error": "message is required"}, status=400)
    if len(text) > 4000:
        return JsonResponse({"error": "message exceeds 4000 characters"}, status=400)
    recent_count = thread.messages.filter(
        sender_type=WhatsAppMessage.Sender.CUSTOMER,
        timestamp__gte=timezone.now() - timedelta(minutes=1),
    ).count()
    if recent_count >= PUBLIC_SUPPORT_MAX_MESSAGES_PER_MINUTE:
        return JsonResponse({"error": "You're sending messages too fast. Please wait a moment."}, status=429)

    with transaction.atomic():
        WhatsAppMessage.objects.create(
            thread=thread,
            sender_type=WhatsAppMessage.Sender.CUSTOMER,
            message_text=text,
        )
        if thread.ticket_status == WhatsAppThread.Status.CLOSED:
            thread.ticket_status = WhatsAppThread.Status.OPEN
        thread.save(update_fields=["ticket_status", "updated_at"])
    return JsonResponse({"ok": True}, status=201)


@require_POST
def create_thread(request):
    data = parse_json_object(request)
    if data is None:
        return JsonResponse({"error": "request body must be a JSON object"}, status=400)
    text = data.get("message", "")
    name = data.get("name", "")
    phone = data.get("phone", "")
    subject = data.get("subject", "Website support")
    if not all(isinstance(value, str) for value in (text, name, phone, subject)):
        return JsonResponse({"error": "message, name, phone, and subject must be text"}, status=400)
    text = text.strip()
    name = name.strip()
    phone = phone.strip()
    subject = subject.strip()
    if request.user.is_authenticated: phone = phone or request.user.phone
    if not text or not phone:
        return JsonResponse({"error": "message and phone are required"}, status=400)
    if len(text) > 4000 or len(name) > 120 or len(subject) > 180 or len(phone) > 24:
        return JsonResponse({"error": "one or more fields exceed their maximum length"}, status=400)
    if not valid_phone(phone):
        return JsonResponse({"error": "enter a valid phone number"}, status=400)
    with transaction.atomic():
        thread = public_support_thread(request)
        if thread:
            recent_count = thread.messages.filter(
                sender_type=WhatsAppMessage.Sender.CUSTOMER,
                timestamp__gte=timezone.now() - timedelta(minutes=1),
            ).count()
            if recent_count >= PUBLIC_SUPPORT_MAX_MESSAGES_PER_MINUTE:
                return JsonResponse({"error": "You're sending messages too fast. Please wait a moment."}, status=429)
        if thread is None:
            thread = WhatsAppThread.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                customer_name=name,
                customer_phone=phone,
                subject=subject,
            )
            request.session[PUBLIC_SUPPORT_SESSION_KEY] = thread.pk
        else:
            thread.customer_name = name or thread.customer_name
            thread.customer_phone = phone
            thread.save(update_fields=["customer_name", "customer_phone", "updated_at"])
        WhatsAppMessage.objects.create(
            thread=thread,
            sender_type=WhatsAppMessage.Sender.CUSTOMER,
            message_text=text,
        )
    return JsonResponse({"thread_id": thread.id}, status=201)


@require_POST
def reply(request, thread_id):
    if not can_manage(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)
    thread = get_object_or_404(WhatsAppThread, pk=thread_id)
    data = parse_json_object(request)
    if data is None:
        return JsonResponse({"error": "request body must be a JSON object"}, status=400)
    text = data.get("message", "")
    if not isinstance(text, str):
        return JsonResponse({"error": "message must be text"}, status=400)
    text = text.strip()
    if not text:
        return JsonResponse({"error": "message is required"}, status=400)
    if len(text) > 4000:
        return JsonResponse({"error": "message exceeds 4000 characters"}, status=400)
    message = WhatsAppMessage.objects.create(thread=thread, sender_type=WhatsAppMessage.Sender.ADMIN, message_text=text)
    thread.updated_at = timezone.now(); thread.save(update_fields=["updated_at"])
    sent = False
    recipient_number = re.sub(r"\D", "", thread.customer_phone)
    provider_configured = bool(
        settings.WHATSAPP_ACCESS_TOKEN
        and settings.WHATSAPP_PHONE_NUMBER_ID
        and valid_phone(thread.customer_phone)
        and thread.subject != ACCOUNT_CHAT_SUBJECT  # in-site chat: the customer reads replies on the website
    )
    if provider_configured:
        payload = json.dumps({"messaging_product": "whatsapp", "to": recipient_number, "type": "text", "text": {"body": text}}).encode()
        req = urllib.request.Request(f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages", data=payload, headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as response: sent = 200 <= response.status < 300
        except (urllib.error.URLError, TimeoutError): sent = False
    return JsonResponse({"id": message.id, "sent_to_whatsapp": sent, "provider_configured": provider_configured})

@csrf_exempt
def webhook(request):
    if request.method == "GET":
        if request.GET.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN and settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(request.GET.get("hub.challenge", ""), content_type="text/plain")
        return HttpResponse("verification failed", status=403)
    if request.method != "POST": return HttpResponse(status=405)
    if settings.WHATSAPP_APP_SECRET:
        supplied = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(settings.WHATSAPP_APP_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected): return HttpResponse("invalid signature", status=403)
    payload = parse_json_object(request)
    if payload is None:
        return JsonResponse({"error": "request body must be a JSON object"}, status=400)
    entries = payload.get("entry", [])
    if not isinstance(entries, list):
        return JsonResponse({"error": "entry must be a list"}, status=400)
    incoming_messages = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("changes", []), list):
            return JsonResponse({"error": "entry changes must be a list"}, status=400)
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or not isinstance(change.get("value", {}), dict):
                return JsonResponse({"error": "change value must be an object"}, status=400)
            value = change.get("value", {})
            inbound_messages = value.get("messages", [])
            if not isinstance(inbound_messages, list):
                return JsonResponse({"error": "messages must be a list"}, status=400)
            for inbound in inbound_messages:
                if not isinstance(inbound, dict):
                    return JsonResponse({"error": "each message must be an object"}, status=400)
                phone = inbound.get("from", "")
                text = inbound.get("text")
                provider_id = inbound.get("id", "")
                if not isinstance(phone, str) or not valid_phone(phone) or len(phone) > 24:
                    return JsonResponse({"error": "message contains an invalid sender number"}, status=400)
                if text is not None and not isinstance(text, dict):
                    return JsonResponse({"error": "message text must be an object"}, status=400)
                message_text = text.get("body", "[Media message]") if text else "[Media message]"
                if not isinstance(message_text, str) or len(message_text) > 4000:
                    return JsonResponse({"error": "message body is invalid"}, status=400)
                if not isinstance(provider_id, str) or len(provider_id) > 120:
                    return JsonResponse({"error": "provider message ID is invalid"}, status=400)
                incoming_messages.append((phone, message_text, provider_id))

    with transaction.atomic():
        for phone, message_text, provider_id in incoming_messages:
            thread = (
                WhatsAppThread.objects.filter(
                    customer_phone=phone,
                    ticket_status=WhatsAppThread.Status.OPEN,
                )
                .order_by("-updated_at")
                .first()
            )
            if thread is None:
                thread = WhatsAppThread.objects.create(
                    customer_phone=phone,
                    customer_name="WhatsApp customer",
                )
            if provider_id:
                WhatsAppMessage.objects.get_or_create(provider_message_id=provider_id, defaults={"thread": thread, "sender_type": WhatsAppMessage.Sender.CUSTOMER, "message_text": message_text})
            else:
                WhatsAppMessage.objects.create(thread=thread, sender_type=WhatsAppMessage.Sender.CUSTOMER, message_text=message_text)
            thread.updated_at = timezone.now()
            thread.save(update_fields=["updated_at"])
    return JsonResponse({"ok": True})
