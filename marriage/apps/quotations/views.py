from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.quotations.models import Quotation
from .services import quotation_pdf

@login_required
def download_quotation(request, quotation_id):
    quotation = get_object_or_404(Quotation.objects.select_related("booking", "booking__customer", "booking__venue"), pk=quotation_id)
    if not (request.user.is_staff or request.user.is_superuser or quotation.booking.customer_id == request.user.pk):
        return HttpResponseForbidden("Not permitted")
    response = HttpResponse(quotation_pdf(quotation), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="royal-venue-quotation-{quotation.pk}.pdf"'
    return response
