from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.staff.models import EmployeeAttendance, StaffMember
from apps.venues.models import Enquiry
from .models import Booking

def is_venue_owner(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in {"VENUE_OWNER", "SUPERADMIN"}
    )

def can_view_enquiry_summaries(user):
    return is_venue_owner(user) or user.has_perm("venues.view_enquiry")

def can_view_booking_summaries(user):
    return is_venue_owner(user) or user.has_perm("bookings.view_booking")

@user_passes_test(is_venue_owner)
def owner_dashboard(request):
    selected_date = timezone.localdate()
    date_param = request.GET.get("date", "")
    if date_param:
        try: selected_date = date.fromisoformat(date_param)
        except ValueError: messages.error(request, "Choose a valid attendance date.")
    bookings = list(Booking.objects.select_related("venue", "customer").order_by("-created_at")[:100])
    pending_bookings = Booking.objects.filter(status__in=[Booking.Status.REQUESTED, Booking.Status.QUOTED]).count()
    customer_ids = {booking.customer_id for booking in bookings}
    counts = dict(Booking.objects.filter(customer_id__in=customer_ids).values("customer_id").annotate(total=Count("id")).values_list("customer_id", "total")) if customer_ids else {}
    history = {}
    for row in Booking.objects.filter(customer_id__in=customer_ids).select_related("venue").order_by("-event_date"):
        history.setdefault(row.customer_id, []).append(row)
    for booking in bookings:
        booking.customer_booking_count = counts.get(booking.customer_id, 0)
        booking.customer_history_items = history.get(booking.customer_id, [])
        booking.awaiting_decision = booking.status in {Booking.Status.REQUESTED, Booking.Status.QUOTED}
        booking.capacity_ok = booking.guest_count <= booking.venue.capacity
        booking.remaining_capacity = max(0, booking.venue.capacity - booking.guest_count)
        booking.over_capacity_by = max(0, booking.guest_count - booking.venue.capacity)
    enquiry_query = request.GET.get("enquiry_q", "").strip()[:120]
    enquiry_status = request.GET.get("enquiry_status", "")
    enquiries = Enquiry.objects.select_related("venue")
    if enquiry_query:
        enquiry_search = (
            Q(name__icontains=enquiry_query)
            | Q(email__icontains=enquiry_query)
            | Q(phone__icontains=enquiry_query)
            | Q(event_type__icontains=enquiry_query)
            | Q(notes__icontains=enquiry_query)
            | Q(venue__name__icontains=enquiry_query)
        )
        reference_number = enquiry_query.upper().removeprefix("RV-")
        if reference_number.isdigit() and len(reference_number) <= 18:
            enquiry_search |= Q(pk=int(reference_number))
        enquiries = enquiries.filter(enquiry_search)
    if enquiry_status in Enquiry.Status.values:
        enquiries = enquiries.filter(status=enquiry_status)
    enquiry_page = Paginator(enquiries.order_by("-created_at"), 25).get_page(
        request.GET.get("enquiry_page", 1)
    )
    employees = list(StaffMember.objects.filter(is_active=True).order_by("full_name"))
    attendance = {record.staff_id: record for record in EmployeeAttendance.objects.filter(date=selected_date, staff_id__in=[item.pk for item in employees])}
    for employee in employees:
        employee.today_attendance = attendance.get(employee.pk)
    from apps.venues.models import Venue
    from apps.vendors.models import Vendor
    from apps.whatsapp.models import WhatsAppMessage
    return render(request, "owner/dashboard.html", {
        "bookings": bookings,
        "enquiries": enquiry_page,
        "enquiry_query": enquiry_query,
        "enquiry_status": enquiry_status,
        "enquiry_status_choices": Enquiry.Status.choices,
        "employees": employees,
        "selected_date": selected_date,
        "pending_bookings": pending_bookings,
        "venues": Venue.objects.filter(is_active=True).count(),
        "vendors": Vendor.objects.filter(is_active=True).count(),
        "staff_count": len(employees),
        "available_staff": StaffMember.objects.filter(is_active=True, status=StaffMember.Status.AVAILABLE).count(),
        "unread": WhatsAppMessage.objects.filter(sender_type="CUSTOMER", is_read=False).count(),
    })

@user_passes_test(can_view_enquiry_summaries)
def print_enquiry_summary(request, enquiry_id):
    enquiry = get_object_or_404(
        Enquiry.objects.select_related("venue"),
        pk=enquiry_id,
    )
    return render(
        request,
        "owner/print_summary.html",
        {"enquiry": enquiry, "summary_title": "Event enquiry summary"},
    )

@user_passes_test(can_view_booking_summaries)
def print_booking_summary(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("venue", "customer"),
        pk=booking_id,
    )
    return render(
        request,
        "owner/print_summary.html",
        {"booking": booking, "summary_title": "Booking details"},
    )

@require_POST
@user_passes_test(is_venue_owner)
def decide_booking(request, booking_id):
    action = request.POST.get("action", "").upper()
    note = request.POST.get("decision_note", "").strip()[:2000]
    with transaction.atomic():
        booking = get_object_or_404(Booking.objects.select_for_update().select_related("venue"), pk=booking_id)
        if booking.status not in {Booking.Status.REQUESTED, Booking.Status.QUOTED}:
            messages.error(request, "This event has already been reviewed.")
        elif action == "ACCEPT":
            if not booking.venue.is_active or booking.guest_count > booking.venue.capacity:
                messages.error(request, f"Cannot accept: guest count ({booking.guest_count}) exceeds current venue capacity ({booking.venue.capacity}).")
            else:
                booking.status = Booking.Status.CONFIRMED
                booking.decision_note = note
                booking.save(update_fields=["status", "decision_note", "updated_at"])
                messages.success(request, f"Event at {booking.venue.name} accepted.")
        elif action == "REJECT":
            if not note:
                messages.error(request, "Add a short reason before rejecting this event.")
            else:
                booking.status = Booking.Status.DECLINED
                booking.decision_note = note
                booking.save(update_fields=["status", "decision_note", "updated_at"])
                messages.success(request, f"Event at {booking.venue.name} rejected and the date slot released.")
        else:
            messages.error(request, "Choose accept or reject.")
    return redirect("owner-dashboard")


@require_POST
@user_passes_test(is_venue_owner)
def manage_enquiry(request, enquiry_id):
    enquiry = get_object_or_404(Enquiry, pk=enquiry_id)
    action = request.POST.get("action", "")
    if action == "delete":
        reference = enquiry.reference
        enquiry.delete()
        messages.success(request, f"Enquiry {reference} deleted.")
    elif action == "archive":
        enquiry.status = Enquiry.Status.ARCHIVED
        enquiry.save(update_fields=["status"])
        messages.success(request, f"Enquiry {enquiry.reference} archived.")
    elif action == "update_status":
        status = request.POST.get("status", "")
        if status not in Enquiry.Status.values:
            messages.error(request, "Choose a valid enquiry status.")
        else:
            enquiry.status = status
            enquiry.save(update_fields=["status"])
            messages.success(request, f"Enquiry {enquiry.reference} updated.")
    else:
        messages.error(request, "Choose a valid enquiry action.")
    return redirect("owner-dashboard")


@require_POST
@user_passes_test(is_venue_owner)
def record_attendance(request):
    try:
        attendance_date = date.fromisoformat(request.POST.get("date", ""))
        staff_id = int(request.POST.get("staff_id", ""))
    except (TypeError, ValueError):
        messages.error(request, "Choose a valid employee and date.")
        return redirect("owner-dashboard")
    status = request.POST.get("status", "")
    if status not in EmployeeAttendance.Status.values:
        messages.error(request, "Choose Present, Absent or Leave.")
        return redirect(f"{reverse('owner-dashboard')}?date={attendance_date.isoformat()}")
    employee = get_object_or_404(StaffMember, pk=staff_id, is_active=True)
    EmployeeAttendance.objects.update_or_create(staff=employee, date=attendance_date, defaults={"status": status, "note": request.POST.get("note", "").strip()[:240], "recorded_by": request.user})
    messages.success(request, f"{employee.full_name}: {EmployeeAttendance.Status(status).label} recorded for {attendance_date:%d %b %Y}.")
    return redirect(f"{reverse('owner-dashboard')}?date={attendance_date.isoformat()}")
