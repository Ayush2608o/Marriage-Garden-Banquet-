from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.venues.models import Venue
from .models import Booking
from .services import create_booking

class BookingApiTests(TestCase):
    def setUp(self):
        self.customer = get_user_model().objects.create_user(username="customer", password="test-password-123")
        self.venue = Venue.objects.create(name="Test Venue", location="Jaipur", description="Test", capacity=300, starting_price=250000)

    def test_availability_changes_after_booking(self):
        params = {"venue": self.venue.pk, "date": "2027-02-10", "slot": "EVENING"}
        self.assertIs(self.client.get("/api/availability/", params).json()["available"], True)
        create_booking(venue_id=self.venue.pk, customer=self.customer, event_date=date(2027, 2, 10), slot="EVENING", guest_count=200)
        self.assertIs(self.client.get("/api/availability/", params).json()["available"], False)

    def test_booking_requires_login_and_conflicting_slot_returns_409(self):
        payload = {"venue": self.venue.pk, "event_date": "2027-02-10", "slot": "EVENING", "guest_count": 200}
        self.assertEqual(self.client.post("/api/bookings/", payload).status_code, 403)
        self.client.force_login(self.customer)
        created = self.client.post("/api/bookings/", payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["notes"], "")
        self.assertEqual(self.client.post("/api/bookings/", payload).status_code, 409)

    def test_booking_rejects_over_capacity_and_inactive_venues_with_client_errors(self):
        self.client.force_login(self.customer)
        payload = {"venue": self.venue.pk, "event_date": "2027-02-10", "slot": "EVENING", "guest_count": 301}
        over_capacity = self.client.post("/api/bookings/", payload)
        self.assertEqual(over_capacity.status_code, 400)
        self.assertEqual(over_capacity.json()["error"], "validation_error")

        self.venue.is_active = False
        self.venue.save(update_fields=["is_active"])
        inactive = self.client.post("/api/bookings/", payload)
        self.assertEqual(inactive.status_code, 400)
        self.assertIn("venue", inactive.json())

    def test_cancelled_slot_can_be_rebooked(self):
        booking = create_booking(venue_id=self.venue.pk, customer=self.customer, event_date=date(2027, 2, 10), slot="EVENING", guest_count=200)
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        next_booking = create_booking(venue_id=self.venue.pk, customer=self.customer, event_date=date(2027, 2, 10), slot="EVENING", guest_count=200)
        self.assertNotEqual(booking.pk, next_booking.pk)

    def test_owner_can_accept_within_capacity_and_reject_over_capacity(self):
        owner = get_user_model().objects.create_user(username="owner", password="test-password-123", role="VENUE_OWNER")
        accepted = Booking.objects.create(customer=self.customer, venue=self.venue, event_date=date(2027, 3, 1), guest_count=250)
        too_large = Booking.objects.create(customer=self.customer, venue=self.venue, event_date=date(2027, 3, 2), guest_count=350)
        self.client.force_login(owner)
        dashboard = self.client.get("/owner/")
        self.assertContains(dashboard, "Events")
        self.assertContains(dashboard, "Customer history")
        self.assertContains(dashboard, "Print details")
        self.client.post(f"/owner/bookings/{accepted.pk}/decision/", {"action": "ACCEPT", "decision_note": "Capacity checked"})
        accepted.refresh_from_db()
        self.assertEqual(accepted.status, Booking.Status.CONFIRMED)
        self.client.post(f"/owner/bookings/{too_large.pk}/decision/", {"action": "ACCEPT"})
        too_large.refresh_from_db()
        self.assertEqual(too_large.status, Booking.Status.REQUESTED)
        self.client.post(f"/owner/bookings/{too_large.pk}/decision/", {"action": "REJECT", "decision_note": "Guest count exceeds venue capacity"})
        too_large.refresh_from_db()
        self.assertEqual(too_large.status, Booking.Status.DECLINED)
        self.assertEqual(too_large.decision_note, "Guest count exceeds venue capacity")

    def test_owner_can_print_booking_details(self):
        booking = Booking.objects.create(
            customer=self.customer,
            venue=self.venue,
            event_date=date(2027, 3, 5),
            guest_count=250,
        )
        owner = get_user_model().objects.create_user(
            username="print-owner",
            password="test-password-123",
            role="VENUE_OWNER",
        )
        self.client.force_login(owner)
        response = self.client.get(f"/owner/bookings/{booking.pk}/print/")
        self.assertContains(response, "Booking details")
        self.assertContains(response, self.venue.name)
        self.assertContains(response, "not an invoice")

    def test_declined_booking_releases_the_venue_slot(self):
        booking = Booking.objects.create(customer=self.customer, venue=self.venue, event_date=date(2027, 3, 3), slot="EVENING", guest_count=150, status=Booking.Status.DECLINED)
        next_booking = create_booking(venue_id=self.venue.pk, customer=self.customer, event_date=booking.event_date, slot=booking.slot, guest_count=150)
        self.assertNotEqual(booking.pk, next_booking.pk)
