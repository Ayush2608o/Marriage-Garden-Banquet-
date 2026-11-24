"""Customer ↔ Royal Venue team chat (the "Messages" page in a customer's account).

It reuses the WhatsApp thread/message tables, so everything a customer writes here
shows up in the owner inbox at /owner/whatsapp/, and the owner's replies appear
here live (the page polls /account/messages/feed/).
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import ACCOUNT_CHAT_SUBJECT, WhatsAppMessage, WhatsAppThread
from .views import can_manage, parse_json_object

MAX_LENGTH = 4000
MAX_MESSAGES_PER_MINUTE = 20
INITIAL_MESSAGES = 500
TEAM_SENDERS = (WhatsAppMessage.Sender.ADMIN, WhatsAppMessage.Sender.BOT)


def is_customer(user):
    return user.is_authenticated and not can_manage(user) and user.role == "CUSTOMER"


def get_thread(user):
    return (
        WhatsAppThread.objects.filter(customer=user, subject=ACCOUNT_CHAT_SUBJECT)
        .order_by("id")
        .first()
    )


def serialize(message):
    return {
        "id": message.id,
        "from": "me" if message.sender_type == WhatsAppMessage.Sender.CUSTOMER else "team",
        "text": message.message_text,
        "ts": message.timestamp.isoformat(),
        "read": message.is_read,
        # lets the page match its own optimistic bubble to the saved message
        "cid": message.provider_message_id[4:] if message.provider_message_id.startswith("web:") else "",
    }


def read_through(thread):
    """Highest id of the customer's own messages that the team has opened (blue ticks)."""
    return (
        thread.messages.filter(sender_type=WhatsAppMessage.Sender.CUSTOMER, is_read=True)
        .aggregate(top=Max("id"))["top"]
        or 0
    )


def json_login_required(view):
    """Like login_required, but answers API calls with 401 JSON instead of redirecting to a login page."""

    def wrapper(request, *args, **kwargs):
        if not is_customer(request.user):
            return JsonResponse({"error": "sign in required"}, status=401)
        return view(request, *args, **kwargs)

    wrapper.__name__ = view.__name__
    return wrapper


@login_required(login_url="login")
def messages_page(request):
    user = request.user
    if can_manage(user):
        return redirect("whatsapp-inbox")
    if user.role != "CUSTOMER":
        return redirect("home")

    thread = get_thread(user)
    messages, first_unread, through = [], None, 0
    if thread:
        recent = list(thread.messages.order_by("-id")[:INITIAL_MESSAGES])
        recent.reverse()
        messages = [serialize(m) for m in recent]
        unread = [m.id for m in recent if m.sender_type in TEAM_SENDERS and not m.is_read]
        first_unread = unread[0] if unread else None
        through = read_through(thread)
        # opening the chat = the customer has seen the team's replies
        thread.messages.filter(sender_type__in=TEAM_SENDERS, is_read=False).update(is_read=True)

    initial = {
        "messages": messages,
        "read_through": through,
        "first_unread_id": first_unread,
        "first_name": user.first_name or user.get_username(),
        "max_length": MAX_LENGTH,
    }
    return render(request, "customer/messages.html", {"initial": initial})


@require_GET
@json_login_required
def messages_feed(request):
    thread = get_thread(request.user)
    if thread is None:
        return JsonResponse({"messages": [], "read_through": 0})
    try:
        after = max(0, int(request.GET.get("after", 0)))
    except (TypeError, ValueError):
        after = 0

    fresh = list(thread.messages.filter(id__gt=after).order_by("id")[:200])
    if request.GET.get("seen") == "1":  # only when the tab is actually visible
        thread.messages.filter(sender_type__in=TEAM_SENDERS, is_read=False).update(is_read=True)
    response = JsonResponse({"messages": [serialize(m) for m in fresh], "read_through": read_through(thread)})
    response["Cache-Control"] = "no-store"
    return response


@require_POST
@json_login_required
def messages_send(request):
    user = request.user
    data = parse_json_object(request)
    if data is None:
        return JsonResponse({"error": "request body must be a JSON object"}, status=400)
    text = data.get("message", "")
    client_id = data.get("client_id", "")
    if not isinstance(text, str) or not isinstance(client_id, str):
        return JsonResponse({"error": "message must be text"}, status=400)
    text = text.strip()
    client_id = client_id.strip()[:60]
    if not text:
        return JsonResponse({"error": "Type a message first."}, status=400)
    if len(text) > MAX_LENGTH:
        return JsonResponse({"error": f"Messages can be up to {MAX_LENGTH} characters."}, status=400)

    recent = WhatsAppMessage.objects.filter(
        thread__customer=user,
        sender_type=WhatsAppMessage.Sender.CUSTOMER,
        timestamp__gte=timezone.now() - timedelta(minutes=1),
    ).count()
    if recent >= MAX_MESSAGES_PER_MINUTE:
        return JsonResponse({"error": "You're sending messages too fast. Please wait a moment."}, status=429)

    provider_id = f"web:{client_id}" if client_id else ""
    with transaction.atomic():
        thread = get_thread(user)
        if thread is None:
            thread = WhatsAppThread.objects.create(
                customer=user,
                customer_name=user.get_full_name() or user.get_username(),
                customer_phone=user.phone,
                subject=ACCOUNT_CHAT_SUBJECT,
            )
        elif provider_id:
            # a retry of a message that already went through (reply got lost) must not duplicate
            existing = thread.messages.filter(provider_message_id=provider_id).first()
            if existing:
                return JsonResponse({"message": serialize(existing)})

        message = WhatsAppMessage.objects.create(
            thread=thread,
            sender_type=WhatsAppMessage.Sender.CUSTOMER,
            message_text=text,
            provider_message_id=provider_id,
        )
        if thread.ticket_status == WhatsAppThread.Status.CLOSED:
            thread.ticket_status = WhatsAppThread.Status.OPEN  # a new message reopens the conversation
            thread.save(update_fields=["ticket_status", "updated_at"])
        else:
            thread.save(update_fields=["updated_at"])
    return JsonResponse({"message": serialize(message)}, status=201)
