from rest_framework import serializers
from apps.venues.models import Venue
from .models import Booking

class BookingCreateSerializer(serializers.ModelSerializer):
    venue = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.filter(is_active=True))
    guest_count = serializers.IntegerField(min_value=1)

    class Meta:
        model = Booking
        fields = ("id", "venue", "event_date", "slot", "guest_count", "notes", "status", "created_at")
        read_only_fields = ("id", "status", "created_at")
        # Availability and uniqueness are checked in the transactional service,
        # which can return the platform's explicit conflict response.
        validators = []
