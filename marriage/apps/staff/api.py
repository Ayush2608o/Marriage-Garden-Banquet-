from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import StaffMember
from .serializers import StaffPublicSerializer

class StaffDirectoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StaffPublicSerializer
    permission_classes = [AllowAny]
    queryset = StaffMember.objects.filter(is_active=True)
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("role"): qs = qs.filter(role__icontains=self.request.query_params["role"])
        if self.request.query_params.get("available") == "true": qs = qs.filter(status=StaffMember.Status.AVAILABLE)
        return qs
