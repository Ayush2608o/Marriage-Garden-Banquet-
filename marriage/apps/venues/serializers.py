from rest_framework import serializers
from .models import Venue

class VenueSerializer(serializers.ModelSerializer):
    final_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    class Meta:
        model = Venue
        fields = ("id", "name", "venue_type", "location", "state", "city", "area", "description", "capacity", "starting_price", "discount_percent", "final_price", "image_url", "model_3d", "featured")
