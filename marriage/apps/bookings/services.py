from django.db import IntegrityError, transaction
from apps.venues.models import Venue
from .models import Booking

@transaction.atomic
def create_booking(*, venue_id, customer, event_date, slot="FULL_DAY", guest_count, notes=""):
    venue = Venue.objects.select_for_update().get(pk=venue_id, is_active=True)
    if Booking.objects.filter(venue=venue, event_date=event_date, slot=slot).exclude(status__in=[Booking.Status.CANCELLED, Booking.Status.DECLINED]).exists():
        raise ValueError("That venue and date slot is already reserved.")
    booking = Booking(venue=venue, customer=customer, event_date=event_date, slot=slot, guest_count=guest_count, notes=notes)
    booking.full_clean()
    try: booking.save()
    except IntegrityError as exc: raise ValueError("That venue and date slot is already reserved.") from exc
    return booking
