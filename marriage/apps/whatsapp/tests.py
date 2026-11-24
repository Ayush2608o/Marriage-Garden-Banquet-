from django.contrib.auth import get_user_model
from django.test import Client, TestCase
import json
import re
from unittest.mock import MagicMock, patch
from .models import WhatsAppMessage, WhatsAppThread

class WhatsAppAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(username="customer", password="test-password-123", phone="+919900001111")
        self.owner = User.objects.create_user(username="owner", password="test-password-123", role="VENUE_OWNER", is_staff=True)
        self.thread = WhatsAppThread.objects.create(customer=self.customer, customer_phone=self.customer.phone, customer_name="Customer")
        WhatsAppMessage.objects.create(thread=self.thread, sender_type="CUSTOMER", message_text="Need venue availability")

    def test_owner_can_open_inbox_and_mark_customer_messages_read(self):
        self.client.force_login(self.owner)
        inbox = self.client.get("/owner/whatsapp/")
        self.assertEqual(inbox.status_code, 200)
        self.assertContains(inbox, "Customer Chat Inbox")
        response = self.client.get(f"/owner/whatsapp/{self.thread.pk}/messages/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["messages"][0]["message_text"], "Need venue availability")
        self.assertTrue(response.json()["messages"][0]["is_read"])
        self.assertTrue(self.thread.messages.get().is_read)

    def test_customer_only_sees_own_thread(self):
        other = get_user_model().objects.create_user(username="other", password="test-password-123")
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/owner/whatsapp/{self.thread.pk}/messages/").status_code, 403)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(f"/owner/whatsapp/{self.thread.pk}/messages/").status_code, 200)

    def test_anonymous_customer_can_create_support_thread(self):
        response = self.client.post("/api/whatsapp/threads/", data={"name": "Guest", "phone": "+919988776655", "message": "Hello"}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(WhatsAppThread.objects.filter(customer_phone="+919988776655").exists())

    def test_website_message_appears_in_admin_inbox_and_dashboard(self):
        response = self.client.post(
            "/api/whatsapp/threads/",
            data={"name": "Website guest", "phone": "+919988776655", "message": "Please call me"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        self.client.force_login(self.owner)
        inbox = self.client.get("/owner/whatsapp/")
        self.assertContains(inbox, "Website guest")
        self.assertContains(inbox, "Page 1 of 1")

        thread_list = self.client.get("/owner/whatsapp/threads/").json()["threads"]
        guest_thread = next(thread for thread in thread_list if thread["phone"] == "+919988776655")
        self.assertEqual(guest_thread["unread_count"], 1)
        self.assertEqual(guest_thread["subject"], "Website support")

        dashboard = self.client.get("/admin/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Unread customer messages")
        self.assertContains(dashboard, "Open customer inbox")

    def test_admin_inbox_paginates_all_conversations(self):
        for index in range(41):
            WhatsAppThread.objects.create(customer_phone=f"+91990000{index:04d}")

        self.client.force_login(self.owner)
        self.assertEqual(self.client.post("/owner/whatsapp/threads/").status_code, 405)
        first_page = self.client.get("/owner/whatsapp/threads/").json()
        second_page = self.client.get("/owner/whatsapp/threads/?page=2").json()
        self.assertEqual(len(first_page["threads"]), 40)
        self.assertTrue(first_page["has_next"])
        self.assertFalse(second_page["has_next"])
        self.assertEqual(len(first_page["threads"]) + len(second_page["threads"]), 42)

    def test_support_thread_rejects_non_object_and_invalid_phone_payloads(self):
        non_object = self.client.post("/api/whatsapp/threads/", data="[]", content_type="application/json")
        self.assertEqual(non_object.status_code, 400)
        invalid_phone = self.client.post(
            "/api/whatsapp/threads/",
            data={"name": "Guest", "phone": "not a phone", "message": "Hello"},
            content_type="application/json",
        )
        self.assertEqual(invalid_phone.status_code, 400)

    def test_webhook_rejects_invalid_shapes_and_deduplicates_messages(self):
        invalid = self.client.post("/api/whatsapp/webhook/", data="[]", content_type="application/json")
        self.assertEqual(invalid.status_code, 400)
        invalid_entries = self.client.post(
            "/api/whatsapp/webhook/",
            data='{"entry":"invalid"}',
            content_type="application/json",
        )
        self.assertEqual(invalid_entries.status_code, 400)

        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "919900002222",
                            "id": "wamid-test-audit",
                            "text": {"body": "Please call me"},
                        }]
                    }
                }]
            }]
        }
        for _ in range(2):
            response = self.client.post(
                "/api/whatsapp/webhook/",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(
            WhatsAppMessage.objects.filter(provider_message_id="wamid-test-audit").count(),
            1,
        )

    def test_reply_api_returns_json_403_for_non_admins(self):
        response = self.client.post(
            f"/owner/whatsapp/{self.thread.pk}/reply/",
            data='{"message":"Hello"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "forbidden")

    def test_public_widget_is_an_in_site_chat(self):
        response = self.client.get("/")
        self.assertContains(response, "Chat with us")
        self.assertContains(response, "support-chat.js")
        self.assertNotContains(response, 'id="support-wa"')

    def test_website_guest_and_owner_can_exchange_chat_messages(self):
        created = self.client.post(
            "/api/whatsapp/threads/",
            data={"name": "Website guest", "phone": "+919988776655", "message": "Hello admin"},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        thread_id = created.json()["thread_id"]

        self.assertEqual(self.client.get("/api/whatsapp/threads/current/").json()["thread_id"], thread_id)
        owner = Client()
        owner.force_login(self.owner)
        owner.get(f"/owner/whatsapp/{thread_id}/messages/")
        reply = owner.post(
            f"/owner/whatsapp/{thread_id}/reply/",
            data={"message": "Hello, how can we help?"},
            content_type="application/json",
        )
        self.assertEqual(reply.status_code, 200)

        messages = self.client.get(f"/api/whatsapp/threads/{thread_id}/messages/")
        self.assertEqual(messages.status_code, 200)
        self.assertEqual(
            [message["message_text"] for message in messages.json()["messages"]],
            ["Hello admin", "Hello, how can we help?"],
        )
        self.assertTrue(
            WhatsAppMessage.objects.filter(
                thread_id=thread_id,
                sender_type="ADMIN",
                is_read=True,
            ).exists()
        )

        sent = self.client.post(
            f"/api/whatsapp/threads/{thread_id}/send/",
            data={"message": "We need a wedding venue."},
            content_type="application/json",
        )
        self.assertEqual(sent.status_code, 201)
        self.assertTrue(
            WhatsAppMessage.objects.filter(
                thread_id=thread_id,
                sender_type="CUSTOMER",
                message_text="We need a wedding venue.",
            ).exists()
        )
        self.assertEqual(
            owner.get("/owner/whatsapp/threads/").json()["threads"][0]["unread_count"],
            1,
        )

    def test_public_chat_is_bound_to_the_visitors_browser_session(self):
        created = self.client.post(
            "/api/whatsapp/threads/",
            data={"name": "Website guest", "phone": "+919988776655", "message": "Private message"},
            content_type="application/json",
        )
        thread_id = created.json()["thread_id"]

        other_visitor = Client()
        self.assertEqual(
            other_visitor.get(f"/api/whatsapp/threads/{thread_id}/messages/").status_code,
            404,
        )
        self.assertEqual(
            other_visitor.post(
                f"/api/whatsapp/threads/{thread_id}/send/",
                data={"message": "This must not be delivered"},
                content_type="application/json",
            ).status_code,
            404,
        )

    def test_owner_reply_endpoint_accepts_csrf_token_from_inbox(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST="localhost")
        client.force_login(self.owner)
        page = client.get("/owner/whatsapp/")
        token = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', page.content).group(1).decode()
        response = client.post(f"/owner/whatsapp/{self.thread.pk}/reply/", data='{"message":"We will check the date."}', content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.thread.messages.filter(sender_type="ADMIN", message_text="We will check the date.").exists())

    def test_owner_reply_normalizes_phone_for_whatsapp_cloud_api(self):
        response_mock = MagicMock()
        response_mock.status = 200
        response_mock.__enter__.return_value = response_mock
        self.client.force_login(self.owner)
        with self.settings(WHATSAPP_ACCESS_TOKEN="test-token", WHATSAPP_PHONE_NUMBER_ID="test-number-id"):
            with patch("apps.whatsapp.views.urllib.request.urlopen", return_value=response_mock) as urlopen:
                response = self.client.post(
                    f"/owner/whatsapp/{self.thread.pk}/reply/",
                    data='{"message":"We will check the date."}',
                    content_type="application/json",
                )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["provider_configured"])
        self.assertTrue(response.json()["sent_to_whatsapp"])
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data)["to"], "919900001111")


class CustomerChatTests(TestCase):
    """The customer-facing "Messages" page (/account/messages/)."""

    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(
            username="priya", first_name="Priya", password="test-password-123", phone="+919900001111"
        )
        self.other = User.objects.create_user(username="other", password="test-password-123", phone="+919900002222")
        self.owner = User.objects.create_user(username="owner", password="test-password-123", role="VENUE_OWNER", is_staff=True)

    def send(self, text="Hello team", **extra):
        return self.client.post(
            "/account/messages/send/", data={"message": text, **extra}, content_type="application/json"
        )

    def test_page_requires_customer_login_and_owners_go_to_inbox(self):
        response = self.client.get("/account/messages/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/signin/", response["Location"])

        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get("/account/messages/"), "/owner/whatsapp/", fetch_redirect_response=False)

        self.client.force_login(self.customer)
        page = self.client.get("/account/messages/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'id="chat-form"')
        self.assertEqual(page.context["initial"]["first_name"], "Priya")
        # opening the page must not create an empty conversation
        self.assertFalse(WhatsAppThread.objects.filter(customer=self.customer).exists())

    def test_sending_creates_thread_that_the_owner_can_see_and_answer(self):
        self.client.force_login(self.customer)
        response = self.send("Is 14 Feb free?")
        self.assertEqual(response.status_code, 201)
        thread = WhatsAppThread.objects.get(customer=self.customer)
        self.assertEqual(thread.subject, "Account chat")
        self.assertEqual(thread.customer_phone, "+919900001111")
        self.assertEqual(thread.customer_name, "Priya")
        self.assertEqual(thread.messages.get().sender_type, "CUSTOMER")

        # owner sees it in the existing inbox, opens it (→ blue ticks) and replies
        owner = Client()
        owner.force_login(self.owner)
        self.assertContains(owner.get("/owner/whatsapp/"), "Priya")
        owner.get(f"/owner/whatsapp/{thread.pk}/messages/")
        owner.post(f"/owner/whatsapp/{thread.pk}/reply/", data={"message": "Yes, it is free!"}, content_type="application/json")

        feed = self.client.get("/account/messages/feed/?after=0&seen=1").json()
        self.assertEqual([m["from"] for m in feed["messages"]], ["me", "team"])
        self.assertEqual(feed["messages"][1]["text"], "Yes, it is free!")
        self.assertEqual(feed["read_through"], feed["messages"][0]["id"])

    def test_validation_and_non_object_bodies(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.send("   ").status_code, 400)
        self.assertEqual(self.send("x" * 4001).status_code, 400)
        self.assertEqual(
            self.client.post("/account/messages/send/", data="[]", content_type="application/json").status_code, 400
        )
        self.assertEqual(self.client.get("/account/messages/send/").status_code, 405)
        self.assertEqual(WhatsAppMessage.objects.count(), 0)

    def test_retrying_the_same_client_id_does_not_duplicate(self):
        self.client.force_login(self.customer)
        first = self.send("Once only", client_id="abc123").json()["message"]
        again = self.send("Once only", client_id="abc123").json()["message"]
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(first["cid"], "abc123")
        self.assertEqual(WhatsAppMessage.objects.count(), 1)

    def test_feed_only_returns_new_messages_and_marks_team_replies_read(self):
        self.client.force_login(self.customer)
        self.send("Hi")
        thread = WhatsAppThread.objects.get(customer=self.customer)
        reply = WhatsAppMessage.objects.create(thread=thread, sender_type="ADMIN", message_text="Hello Priya")
        mine = thread.messages.filter(sender_type="CUSTOMER").get()

        feed = self.client.get(f"/account/messages/feed/?after={mine.id}").json()
        self.assertEqual([m["id"] for m in feed["messages"]], [reply.id])
        reply.refresh_from_db()
        self.assertFalse(reply.is_read)  # tab not marked visible → still unread

        self.client.get(f"/account/messages/feed/?after={mine.id}&seen=1")
        reply.refresh_from_db()
        self.assertTrue(reply.is_read)

    def test_customers_cannot_read_each_others_chat(self):
        self.client.force_login(self.customer)
        self.send("private question")
        other = Client()
        other.force_login(self.other)
        self.assertEqual(other.get("/account/messages/feed/?after=0").json()["messages"], [])
        self.assertEqual(other.get("/account/messages/").context["initial"]["messages"], [])

    def test_anonymous_api_calls_get_401_json_not_a_redirect(self):
        self.assertEqual(self.client.get("/account/messages/feed/").status_code, 401)
        self.assertEqual(self.send().status_code, 401)

    def test_new_message_reopens_a_closed_conversation(self):
        self.client.force_login(self.customer)
        self.send("first")
        WhatsAppThread.objects.update(ticket_status="CLOSED")
        self.send("one more thing")
        self.assertEqual(WhatsAppThread.objects.get().ticket_status, "OPEN")

    def test_rate_limit(self):
        self.client.force_login(self.customer)
        for i in range(20):
            self.assertEqual(self.send(f"m{i}").status_code, 201)
        self.assertEqual(self.send("too many").status_code, 429)

    def test_unread_team_replies_show_as_badge_and_divider_then_clear(self):
        self.client.force_login(self.customer)
        self.send("hello")
        thread = WhatsAppThread.objects.get(customer=self.customer)
        WhatsAppMessage.objects.create(thread=thread, sender_type="ADMIN", message_text="Reply 1")
        WhatsAppMessage.objects.create(thread=thread, sender_type="ADMIN", message_text="Reply 2")

        home = self.client.get("/")
        self.assertEqual(home.context["chat_unread"], 2)
        self.assertContains(home, "nav-badge")

        page = self.client.get("/account/messages/")
        self.assertIsNotNone(page.context["initial"]["first_unread_id"])
        self.assertEqual(self.client.get("/").context["chat_unread"], 0)

    def test_owner_replies_in_account_chat_are_not_forwarded_to_whatsapp(self):
        self.client.force_login(self.customer)
        self.send("hello")
        thread = WhatsAppThread.objects.get(customer=self.customer)
        owner = Client()
        owner.force_login(self.owner)
        with self.settings(WHATSAPP_ACCESS_TOKEN="token", WHATSAPP_PHONE_NUMBER_ID="123"), patch(
            "apps.whatsapp.views.urllib.request.urlopen"
        ) as urlopen:
            response = owner.post(
                f"/owner/whatsapp/{thread.pk}/reply/", data={"message": "Hi!"}, content_type="application/json"
            )
        self.assertEqual(response.status_code, 200)
        urlopen.assert_not_called()
        self.assertFalse(response.json()["provider_configured"])
