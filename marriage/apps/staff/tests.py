from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from apps.audit_logs.models import AccessLog
from apps.bookings.models import Booking
from apps.venues.models import Venue
from .models import EmployeeAttendance, StaffMember
from .services import complete_shift, reserve_staff

class StaffSafetyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="owner", password="test-password-123", role="VENUE_OWNER", is_staff=True)
        self.bodyguard = User.objects.create_user(username="guard", password="test-password-123", role="STAFF")
        customer = User.objects.create_user(username="customer", password="test-password-123")
        venue = Venue.objects.create(name="Test Venue", location="Jaipur", description="Test", capacity=300, starting_price=250000)
        self.booking = Booking.objects.create(customer=customer, venue=venue, event_date=timezone.localdate() + timedelta(days=5), guest_count=100)
        self.staff = StaffMember.objects.create(full_name="Meera Sharma", phone="+919800001111", role="Catering", is_female=True, home_drop_location="Private address")

    def test_female_catering_shift_requires_safe_drop_before_completion(self):
        starts = timezone.now() + timedelta(days=5)
        shift = reserve_staff(staff_id=self.staff.pk, booking=self.booking, starts_at=starts, ends_at=starts + timedelta(hours=8), assigned_by=self.owner)
        self.assertTrue(shift.requires_safety_drop)
        with self.assertRaises(ValueError): complete_shift(shift.pk)
        shift.escort_vehicle_number = "RJ14 AB 1234"
        shift.driver_name = "Driver Example"
        shift.driver_phone = "+919800001122"
        shift.bodyguard_name = "Certified Guard"
        shift.bodyguard_user = self.bodyguard
        shift.safely_dropped_at = timezone.now()
        shift.save()
        self.assertEqual(complete_shift(shift.pk).staff.status, StaffMember.Status.COMPLETED)

    def test_only_admin_or_assigned_bodyguard_can_read_drop_details_and_access_is_logged(self):
        starts = timezone.now() + timedelta(days=5)
        shift = reserve_staff(staff_id=self.staff.pk, booking=self.booking, starts_at=starts, ends_at=starts + timedelta(hours=8), assigned_by=self.owner)
        shift.bodyguard_user = self.bodyguard
        shift.save(update_fields=["bodyguard_user"])
        url = f"/api/staff/shifts/{shift.pk}/safety-details/"
        unauthorized = get_user_model().objects.create_user(username="unauthorized", password="test-password-123")
        self.client.force_login(unauthorized)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.bodyguard)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["home_drop_location"], "Private address")
        self.assertEqual(AccessLog.objects.filter(action="VIEW_STAFF_SAFETY_DETAILS", actor=self.bodyguard).count(), 1)

    def test_owner_marks_employee_absent_from_dashboard(self):
        self.client.force_login(self.owner)
        today = timezone.localdate()
        response = self.client.post("/owner/attendance/", {"staff_id": self.staff.pk, "date": today.isoformat(), "status": "ABSENT", "note": "Called in sick"})
        self.assertEqual(response.status_code, 302)
        record = EmployeeAttendance.objects.get(staff=self.staff, date=today)
        self.assertEqual(record.status, EmployeeAttendance.Status.ABSENT)
        self.assertEqual(record.note, "Called in sick")
