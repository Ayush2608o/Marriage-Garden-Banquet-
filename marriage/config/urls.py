from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.venues import views
from apps.venues.api import VenueViewSet
from apps.vendors.api import VendorViewSet
from apps.staff.api import StaffDirectoryViewSet
from apps.bookings.api import AvailabilityView, BookingCreateView
from apps.quotations.views import download_quotation
from apps.whatsapp import views as whatsapp
from apps.whatsapp import customer_views as chat
from apps.staff.views import sensitive_shift_details
from apps.accounts.views import CustomerLoginView, customer_dashboard, signup, signout
from apps.bookings.owner_views import (
    owner_dashboard,
    decide_booking,
    manage_enquiry,
    record_attendance,
    print_enquiry_summary,
    print_booking_summary,
)

router = DefaultRouter()
router.register("venues", VenueViewSet, basename="venue")
router.register("vendors", VendorViewSet, basename="vendor")
router.register("staff", StaffDirectoryViewSet, basename="staff-directory")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("enquire/", views.enquire, name="enquire"),
    path("signin/", CustomerLoginView.as_view(), name="login"),
    path("signup/", signup, name="signup"),
    path("signout/", signout, name="signout"),
    path("account/", customer_dashboard, name="customer-dashboard"),
    path("account/messages/", chat.messages_page, name="customer-messages"),
    path("account/messages/feed/", chat.messages_feed, name="customer-messages-feed"),
    path("account/messages/send/", chat.messages_send, name="customer-messages-send"),
    path("owner/", owner_dashboard, name="owner-dashboard"),
    path("owner/enquiries/<int:enquiry_id>/print/", print_enquiry_summary, name="owner-print-enquiry"),
    path("owner/bookings/<int:booking_id>/print/", print_booking_summary, name="owner-print-booking"),
    path("owner/bookings/<int:booking_id>/decision/", decide_booking, name="booking-decision"),
    path("owner/enquiries/<int:enquiry_id>/manage/", manage_enquiry, name="enquiry-manage"),
    path("owner/attendance/", record_attendance, name="record-attendance"),
    path("owner/whatsapp/", whatsapp.inbox, name="whatsapp-inbox"),
    path("owner/whatsapp/threads/", whatsapp.thread_list, name="whatsapp-thread-list"),
    path("owner/whatsapp/<int:thread_id>/messages/", whatsapp.thread_messages, name="whatsapp-messages"),
    path("owner/whatsapp/<int:thread_id>/reply/", whatsapp.reply, name="whatsapp-reply"),
    path("api/whatsapp/threads/", whatsapp.create_thread, name="whatsapp-create-thread"),
    path("api/whatsapp/threads/current/", whatsapp.current_support_thread, name="whatsapp-current-thread"),
    path("api/whatsapp/threads/<int:thread_id>/messages/", whatsapp.public_thread_messages, name="whatsapp-public-messages"),
    path("api/whatsapp/threads/<int:thread_id>/send/", whatsapp.public_thread_send, name="whatsapp-public-send"),
    path("api/whatsapp/webhook/", whatsapp.webhook, name="whatsapp-webhook"),
    path("api/staff/shifts/<int:shift_id>/safety-details/", sensitive_shift_details, name="staff-safety-details"),
    path("api/", include(router.urls)),
    path("api/availability/", AvailabilityView.as_view(), name="availability"),
    path("api/bookings/", BookingCreateView.as_view(), name="booking-create"),
    path("quotations/<int:quotation_id>/pdf/", download_quotation, name="quotation-pdf"),
    path("privacy-policy/", views.policy, {"policy": "privacy"}, name="privacy-policy"),
    path("terms/", views.policy, {"policy": "terms"}, name="terms"),
    path("safety-policy/", views.policy, {"policy": "safety"}, name="safety-policy"),
]
