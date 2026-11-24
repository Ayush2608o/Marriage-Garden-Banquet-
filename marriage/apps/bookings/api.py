from datetime import date
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from apps.venues.models import Venue
from .models import Booking
from .serializers import BookingCreateSerializer
from .services import create_booking

class AvailabilityView(APIView):
    permission_classes = []
    def get(self, request):
        try:
            venue_id = int(request.query_params["venue"])
            event_date = date.fromisoformat(request.query_params["date"])
            slot = request.query_params.get("slot", "FULL_DAY")
        except (KeyError, ValueError): return JsonResponse({"error": "venue and ISO date are required"}, status=400)
        if not Venue.objects.filter(pk=venue_id, is_active=True).exists(): return JsonResponse({"error": "venue not found"}, status=404)
        reserved = Booking.objects.filter(venue_id=venue_id, event_date=event_date, slot=slot).exclude(status__in=[Booking.Status.CANCELLED, Booking.Status.DECLINED]).exists()
        return JsonResponse({"venue": venue_id, "date": event_date.isoformat(), "slot": slot, "available": not reserved})

class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            fields = serializer.validated_data
            booking = create_booking(venue_id=fields["venue"].pk, customer=request.user, event_date=fields["event_date"], slot=fields["slot"], guest_count=fields["guest_count"], notes=fields.get("notes", ""))
        except ValueError as exc:
            return JsonResponse({"error": str(exc)}, status=409)
        except ValidationError as exc:
            errors = getattr(exc, "message_dict", {"__all__": exc.messages})
            return JsonResponse({"error": "validation_error", "errors": errors}, status=400)
        except Venue.DoesNotExist:
            return JsonResponse({"error": "venue_not_found"}, status=404)
        return JsonResponse(BookingCreateSerializer(booking).data, status=status.HTTP_201_CREATED)
