from django.conf import settings

def whatsapp_settings(request):
    return {"whatsapp_fallback_number": settings.WHATSAPP_FALLBACK_NUMBER}


def customer_chat(request):
    """Unread team replies for the signed-in customer (badge next to "Messages")."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated or user.is_superuser or user.role != "CUSTOMER":
        return {}
    from apps.whatsapp.models import WhatsAppMessage

    unread = WhatsAppMessage.objects.filter(
        thread__customer=user,
        sender_type__in=("ADMIN", "BOT"),
        is_read=False,
    ).count()
    return {"chat_unread": unread}
