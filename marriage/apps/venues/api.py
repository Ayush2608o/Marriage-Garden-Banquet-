from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Venue
from .serializers import VenueSerializer
class VenueViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VenueSerializer
    permission_classes = [AllowAny]
    queryset = Venue.objects.filter(is_active=True)
    def get_queryset(self):
        qs = super().get_queryset()
        for field in ("state", "city", "area", "venue_type"):
            value = self.request.query_params.get(field)
            if value: qs = qs.filter(**{field: value})
        return qs
