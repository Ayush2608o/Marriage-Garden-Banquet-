from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or request.user.is_staff or getattr(obj, "owner_id", None) == request.user.pk

class IsOwnerOrStaff(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.role in {"VENUE_OWNER", "SUPERADMIN"})

class IsStaffRole(BasePermission):
    allowed_roles = set()
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_superuser or request.user.role in self.allowed_roles)
