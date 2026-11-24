from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.customers.models import CustomerProfile
from .rbac import sync_owner_role

class AdminRoleTests(TestCase):
    def test_venue_owner_sees_operations_models(self):
        owner = get_user_model().objects.create_user(username="owner", password="test-password-123", role="VENUE_OWNER", is_staff=True)
        sync_owner_role()
        self.client.force_login(owner)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Venues")
        self.assertContains(response, "Bookings")
        self.assertContains(response, "WhatsApp threads")
        self.assertContains(response, "Open WhatsApp Messenger Inbox")
        enquiries = self.client.get("/admin/venues/enquiry/")
        self.assertEqual(enquiries.status_code, 200)
        thread_list = self.client.get("/admin/whatsapp/whatsappthread/")
        self.assertContains(thread_list, "Open WhatsApp Messenger Inbox")
        self.assertEqual(self.client.get("/admin/whatsapp/whatsappthread/add/").status_code, 403)

    def test_non_owner_staff_role_cannot_enter_admin(self):
        staff = get_user_model().objects.create_user(username="staff", password="test-password-123", role="STAFF", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.assertNotEqual(self.client.get("/owner/").status_code, 200)
        self.assertNotEqual(self.client.get("/owner/whatsapp/").status_code, 200)

    def test_customer_can_sign_up_and_sign_in(self):
        response = self.client.post("/signup/", {"username": "newcustomer", "email": "new@example.com", "phone": "+919876543210", "password1": "Mango!Garden2026-Unique", "password2": "Mango!Garden2026-Unique", "marketing_consent": "on"})
        self.assertRedirects(response, "/signin/")
        user = get_user_model().objects.get(username="newcustomer")
        self.assertEqual(user.role, "CUSTOMER")
        self.assertTrue(CustomerProfile.objects.get(user=user).marketing_consent)
        login = self.client.post("/signin/", {"username": "newcustomer", "password": "Mango!Garden2026-Unique"})
        self.assertRedirects(login, "/")
        self.assertContains(self.client.get("/"), "Sign out")
        self.assertEqual(self.client.get("/account/").status_code, 200)

    def test_home_has_customer_and_admin_signin_links(self):
        response = self.client.get("/")
        self.assertContains(response, "/signin/")
        self.assertContains(response, "/signup/")
        self.assertContains(response, "/admin/login/")
