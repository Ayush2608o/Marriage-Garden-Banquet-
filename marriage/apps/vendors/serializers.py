from rest_framework import serializers
from .models import Vendor

def mask_phone(number):
    digits = "".join(c for c in number if c.isdigit())
    return ("+" + digits[:-4] + "••••" + digits[-4:]) if len(digits) > 4 else "••••"

class VendorSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()
    class Meta:
        model = Vendor
        fields = ("id", "name", "category", "description", "city", "phone", "whatsapp_number", "starting_price", "years_experience", "verified")
    def get_phone(self, obj):
        request = self.context.get("request")
        return obj.phone if request and request.user.is_authenticated and (request.user.is_staff or request.user.role in {"VENUE_OWNER", "SUPERADMIN"}) else mask_phone(obj.phone)
    def get_whatsapp_number(self, obj):
        request = self.context.get("request")
        return obj.whatsapp_number if request and request.user.is_authenticated and (request.user.is_staff or request.user.role in {"VENUE_OWNER", "SUPERADMIN"}) else mask_phone(obj.whatsapp_number)
