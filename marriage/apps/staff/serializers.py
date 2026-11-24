from rest_framework import serializers
from .models import StaffMember
class StaffPublicSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    class Meta:
        model = StaffMember
        fields = ("id", "full_name", "role", "status", "phone")
    def get_phone(self, obj):
        request = self.context.get("request")
        if request and (request.user.is_staff or request.user.role in {"VENUE_OWNER", "SUPERADMIN"}): return obj.phone
        return "••••" + obj.phone[-4:]
