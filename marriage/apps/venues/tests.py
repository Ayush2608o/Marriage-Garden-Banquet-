from decimal import Decimal
import re
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.test import TestCase
from .models import Enquiry, Venue
from .notifications import notify_new_enquiry

class VenuePricingTests(TestCase):
    def test_discount_price_is_calculated(self):
        venue = Venue.objects.create(name="Test Garden", location="Jaipur", description="Test", capacity=400, starting_price=500000, discount_percent=Decimal("12.50"))
        self.assertEqual(venue.final_price, Decimal("437500.00"))

    def test_public_policy_pages_render(self):
        for path in ("/privacy-policy/", "/terms/", "/safety-policy/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_homepage_displays_venue_capacity_pricing_and_enquiry_prefill_data(self):
        venue = Venue.objects.create(
            name="Golden Garden",
            location="Jaipur",
            description="A garden for celebrations.",
            capacity=350,
            starting_price=500000,
            discount_percent=Decimal("10.00"),
        )
        response = self.client.get("/")
        self.assertContains(response, "Up to 350 guests")
        self.assertContains(response, "₹450,000")
        self.assertContains(response, '?venue={}#contact'.format(venue.pk))
        self.assertContains(response, 'name="venue"')
        selected = self.client.get("/", {"venue": venue.pk})
        self.assertContains(selected, 'name="venue" id="enquiry-venue" value="{}"'.format(venue.pk))
        self.assertContains(selected, "Enquiring about Golden Garden")

    def test_enquiry_form_posts_with_csrf_and_fails_safely_for_stale_tokens(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")
        page = client.get("/")
        token = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', page.content).group(1).decode()
        payload = {"name": "CSRF Test", "email": "csrf@example.com", "phone": "+919800000000", "csrfmiddlewaretoken": token}
        self.assertEqual(client.post("/enquire/", payload).status_code, 302)
        stale = client.post("/enquire/", {**payload, "csrfmiddlewaretoken": "stale-token"})
        self.assertEqual(stale.status_code, 403)
        self.assertContains(stale, "Please refresh the page", status_code=403)


class EnquiryTests(TestCase):
    def setUp(self):
        self.payload = {
            "name": "A Couple",
            "email": "couple@example.com",
            "phone": "+91 98765 43210",
            "event_type": Enquiry.EventType.WEDDING,
            "event_date": "2027-12-12",
            "guest_count": "240",
            "notes": "An evening celebration",
        }

    def test_json_submission_persists_enquiry_and_returns_reference(self):
        response = self.client.post(
            "/enquire/",
            self.payload,
            HTTP_ACCEPT="application/json",
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 201)
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.name, "A Couple")
        self.assertEqual(enquiry.email, "couple@example.com")
        self.assertEqual(enquiry.phone, "+91 98765 43210")
        self.assertEqual(enquiry.event_type, Enquiry.EventType.WEDDING)
        self.assertEqual(enquiry.event_date.isoformat(), "2027-12-12")
        self.assertEqual(enquiry.guest_count, 240)
        self.assertEqual(enquiry.notes, "An evening celebration")
        self.assertEqual(enquiry.status, Enquiry.Status.PENDING)
        self.assertEqual(response.json()["reference_id"], enquiry.reference)

    def test_enquiry_can_be_preselected_for_an_active_venue(self):
        venue = Venue.objects.create(
            name="Selected Garden",
            location="Jaipur",
            description="A venue.",
            capacity=300,
            starting_price=400000,
        )
        response = self.client.post(
            "/enquire/",
            {**self.payload, "venue": str(venue.pk)},
            HTTP_ACCEPT="application/json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, 201)
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.venue, venue)
        self.assertEqual(response.json()["venue_id"], venue.pk)

        venue.is_active = False
        venue.save(update_fields=["is_active"])
        rejected = self.client.post(
            "/enquire/",
            {**self.payload, "venue": str(venue.pk)},
            HTTP_ACCEPT="application/json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_invalid_date_email_or_guest_count_returns_validation_error(self):
        for overrides in (
            {"event_date": "next Friday"},
            {"email": "not-an-email"},
            {"guest_count": "10001"},
        ):
            with self.subTest(overrides=overrides):
                response = self.client.post(
                    "/enquire/",
                    {**self.payload, **overrides},
                    HTTP_ACCEPT="application/json",
                    HTTP_HOST="localhost",
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"], "validation_error")
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_owner_can_filter_update_archive_and_delete_enquiries(self):
        matching = Enquiry.objects.create(**self.payload)
        other = Enquiry.objects.create(
            name="Different Couple",
            email="different@example.com",
            phone="+919111111111",
        )
        self.client.force_login(
            get_user_model().objects.create_user(
                username="venue-owner",
                password="test-password-123",
                role="VENUE_OWNER",
            )
        )

        response = self.client.get("/owner/", {"enquiry_q": "A Couple"})
        self.assertContains(response, matching.reference)
        self.assertContains(response, "Print summary")
        self.assertNotContains(response, other.reference)
        self.assertContains(
            self.client.get("/owner/", {"enquiry_q": matching.reference}),
            matching.reference,
        )

        for status in (Enquiry.Status.CONFIRMED, Enquiry.Status.CONTACTED, Enquiry.Status.PENDING):
            self.client.post(
                f"/owner/enquiries/{matching.pk}/manage/",
                {"action": "update_status", "status": status},
            )
            matching.refresh_from_db()
            self.assertEqual(matching.status, status)

        self.client.post(
            f"/owner/enquiries/{matching.pk}/manage/",
            {"action": "archive"},
        )
        matching.refresh_from_db()
        self.assertEqual(matching.status, Enquiry.Status.ARCHIVED)

        self.client.post(
            f"/owner/enquiries/{matching.pk}/manage/",
            {"action": "delete"},
        )
        self.assertFalse(Enquiry.objects.filter(pk=matching.pk).exists())

    def test_owner_dashboard_requires_admin_authentication(self):
        response = self.client.get("/owner/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_owner_can_print_enquiry_summary_but_customer_cannot(self):
        enquiry = Enquiry.objects.create(**self.payload)
        customer = get_user_model().objects.create_user(
            username="summary-customer",
            password="test-password-123",
        )
        self.client.force_login(customer)
        denied = self.client.get(f"/owner/enquiries/{enquiry.pk}/print/")
        self.assertEqual(denied.status_code, 302)

        owner = get_user_model().objects.create_user(
            username="summary-owner",
            password="test-password-123",
            role="VENUE_OWNER",
        )
        self.client.force_login(owner)
        response = self.client.get(f"/owner/enquiries/{enquiry.pk}/print/")
        self.assertContains(response, "Event enquiry summary")
        self.assertContains(response, enquiry.reference)
        self.assertContains(response, "Print / Save as PDF")

    def test_notification_logs_when_email_recipient_is_not_configured(self):
        enquiry = Enquiry.objects.create(**self.payload)
        with self.settings(ENQUIRY_NOTIFICATION_EMAIL=""):
            with self.assertLogs("apps.venues.notifications", level="INFO") as captured:
                notify_new_enquiry(enquiry.pk)
        self.assertIn(enquiry.reference, captured.output[0])

    def test_notification_sends_email_when_configured(self):
        enquiry = Enquiry.objects.create(**self.payload)
        with self.settings(
            ENQUIRY_NOTIFICATION_EMAIL="events@example.com",
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ):
            notify_new_enquiry(enquiry.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(enquiry.reference, mail.outbox[0].subject)
