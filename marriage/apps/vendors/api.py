from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Vendor
from .serializers import VendorSerializer
class VendorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VendorSerializer
    permission_classes = [AllowAny]
    queryset = Vendor.objects.filter(is_active=True)
    def get_queryset(self):
        qs = super().get_queryset()
        for field in ("category", "city"):
            value = self.request.query_params.get(field)
            if value: qs = qs.filter(**{field: value})
        return qs
