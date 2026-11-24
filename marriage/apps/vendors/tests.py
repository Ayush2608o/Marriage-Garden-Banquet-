from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Vendor

class VendorPrivacyTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(name="Aarav Photo", category="PHOTOGRAPHER", city="Jaipur", phone="+919812345678", whatsapp_number="+919812345678", starting_price=50000)

    def test_public_phone_numbers_are_masked(self):
        data = self.client.get("/api/vendors/").json()[0]
        self.assertNotEqual(data["phone"], self.vendor.phone)
        self.assertTrue(data["phone"].endswith("5678"))

    def test_owner_can_see_vendor_contact(self):
        owner = get_user_model().objects.create_user(username="owner", password="test-password-123", role="VENUE_OWNER")
        self.client.force_login(owner)
        data = self.client.get("/api/vendors/").json()[0]
        self.assertEqual(data["phone"], self.vendor.phone)
