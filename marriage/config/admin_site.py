from django.contrib.admin import AdminSite

class RoyalVenueAdminSite(AdminSite):
    site_header = "Royal Venue Operations"
    site_title = "Royal Venue Admin"
    index_title = "Manage venues, bookings and support"
    index_template = "admin/owner_index.html"

    def has_permission(self, request):
        user = request.user
        return bool(user.is_active and user.is_staff and (user.is_superuser or user.role in {"SUPERADMIN", "VENUE_OWNER"}))

    def each_context(self, request):
        context = super().each_context(request)
        if request.user.is_authenticated and request.user.is_staff:
            from apps.whatsapp.models import WhatsAppMessage

            context["unread_customer_messages"] = WhatsAppMessage.objects.filter(
                sender_type=WhatsAppMessage.Sender.CUSTOMER,
                is_read=False,
            ).count()
        return context

    def index(self, request, extra_context=None):
        from apps.venues.models import Venue
        from apps.whatsapp.models import WhatsAppThread

        context = {
            "open_support_conversations": WhatsAppThread.objects.exclude(
                ticket_status=WhatsAppThread.Status.CLOSED
            ).count(),
            "active_venues": Venue.objects.filter(is_active=True).count(),
        }
        context.update(extra_context or {})
        return super().index(request, context)
