"""Idempotent demo records for local development: python database/seed_data.py"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from apps.venues.models import Venue, Enquiry
from apps.bookings.models import Booking
from apps.customers.models import CustomerProfile
from apps.vendors.models import Vendor
from apps.staff.models import StaffMember
from apps.whatsapp.models import WhatsAppThread, WhatsAppMessage
from apps.accounts.rbac import sync_owner_role

User = get_user_model()
owner, _ = User.objects.get_or_create(username="venueowner", defaults={"email": "owner@royalvenue.in", "role": "VENUE_OWNER", "phone": "+919800000001", "is_staff": True})
if not owner.has_usable_password(): owner.set_password("RoyalVenueDemo2026!"); owner.save()
owner.role = "VENUE_OWNER"; owner.is_staff = True; owner.save(update_fields=["role", "is_staff"])
sync_owner_role()

venues = [
    {"name": "The Marigold Garden", "venue_type": "GARDEN", "location": "Jaipur, Rajasthan", "state": "Rajasthan", "city": "Jaipur", "area": "Tonk Road", "description": "Open-air garden for traditional celebrations.", "capacity": 800, "starting_price": 450000, "discount_percent": 8, "featured": True},
    {"name": "Lakeview Wedding Resort", "venue_type": "RESORT", "location": "Udaipur, Rajasthan", "state": "Rajasthan", "city": "Udaipur", "area": "Fateh Sagar", "description": "A destination resort with event lawns and guest rooms.", "capacity": 500, "starting_price": 750000, "discount_percent": 5},
    {"name": "The Courtyard Banquet", "venue_type": "DUPLEX", "location": "Indore, Madhya Pradesh", "state": "Madhya Pradesh", "city": "Indore", "area": "Vijay Nagar", "description": "A contemporary duplex banquet hall.", "capacity": 350, "starting_price": 225000, "discount_percent": 0},
]
for row in venues: Venue.objects.update_or_create(name=row["name"], defaults=row)

vendors = [
    {"name": "Aarav Weddings Photography", "category": "PHOTOGRAPHER", "description": "Candid wedding and portrait photography.", "city": "Jaipur", "phone": "+919812345601", "whatsapp_number": "+919812345601", "starting_price": 65000, "years_experience": 9, "verified": True},
    {"name": "Sur Sagar Events", "category": "DJ", "description": "DJ, sound and lighting packages.", "city": "Jaipur", "phone": "+919812345602", "whatsapp_number": "+919812345602", "starting_price": 35000, "years_experience": 7, "verified": True},
    {"name": "Raj Rasoi Caterers", "category": "CATERING", "description": "Rajasthani and multi-cuisine wedding catering.", "city": "Jaipur", "phone": "+919812345603", "whatsapp_number": "+919812345603", "starting_price": 850, "years_experience": 14, "verified": True},
    {"name": "Shree Ganesh Wedding Cards", "category": "PRINTER", "description": "Custom printed and boxed wedding invitations.", "city": "Jaipur", "phone": "+919812345604", "whatsapp_number": "+919812345604", "starting_price": 35, "years_experience": 12},
    {"name": "Bharat Celebration Supplies", "category": "WHOLESALE", "description": "Bulk celebration and kirana supplies.", "city": "Jaipur", "phone": "+919812345605", "whatsapp_number": "+919812345605", "starting_price": 10000, "years_experience": 18},
]
for row in vendors: Vendor.objects.update_or_create(name=row["name"], defaults=row)

for name, role, phone, female in [("Meera Sharma", "Catering", "+919800000101", True), ("Kavita Joshi", "Hospitality", "+919800000102", True), ("Rohan Singh", "Catering", "+919800000103", False)]:
    StaffMember.objects.get_or_create(full_name=name, defaults={"role": role, "phone": phone, "is_female": female})

if not Enquiry.objects.filter(email="ananya.shah@example.in").exists():
    Enquiry.objects.create(name="Ananya Shah", email="ananya.shah@example.in", phone="+919900001111", event_type="wedding", guest_count=350, message="Looking for a December wedding date.")
customer, _ = User.objects.get_or_create(username="ananya.shah", defaults={"first_name": "Ananya", "last_name": "Shah", "email": "ananya.shah@example.in", "phone": "+919900001111", "role": "CUSTOMER"})
if not customer.has_usable_password(): customer.set_unusable_password(); customer.save(update_fields=["password"])
CustomerProfile.objects.get_or_create(user=customer, defaults={"city": "Jaipur"})
garden = Venue.objects.get(name="The Marigold Garden")
Booking.objects.update_or_create(customer=customer, venue=garden, event_date="2026-12-12", slot="EVENING", defaults={"guest_count": 350, "notes": "DEMO SAMPLE — December wedding request. Prefers an outdoor ceremony and vegetarian catering.", "status": Booking.Status.REQUESTED, "is_demo": True})
thread, created = WhatsAppThread.objects.get_or_create(customer_phone="+919900001111", subject="Venue availability", defaults={"customer_name": "Ananya Shah", "is_urgent": True})
if created:
    WhatsAppMessage.objects.create(thread=thread, sender_type="CUSTOMER", message_text="Hello, is The Marigold Garden available for 12 December?")
    WhatsAppMessage.objects.create(thread=thread, sender_type="BOT", message_text="Thanks for contacting Royal Venue. Our team will confirm availability shortly.")
print("Royal Venue demo data is ready.")
