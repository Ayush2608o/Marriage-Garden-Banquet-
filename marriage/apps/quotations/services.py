from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def quotation_pdf(quotation):
    out = BytesIO(); pdf = canvas.Canvas(out, pagesize=A4)
    pdf.setTitle(f"Royal Venue quotation {quotation.pk}")
    pdf.setFont("Helvetica-Bold", 20); pdf.drawString(52, 790, "ROYAL VENUE")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(52, 754, f"Quotation #{quotation.pk} — {quotation.created_at:%d %b %Y}")
    pdf.drawString(52, 724, f"Venue: {quotation.booking.venue.name}")
    pdf.drawString(52, 702, f"Event date: {quotation.booking.event_date} | Slot: {quotation.booking.slot}")
    pdf.drawString(52, 660, f"Subtotal: INR {quotation.subtotal:,.2f}")
    pdf.drawString(52, 638, f"Discount: INR {quotation.discount:,.2f}")
    pdf.drawString(52, 616, f"Tax: INR {quotation.tax:,.2f}")
    pdf.setFont("Helvetica-Bold", 14); pdf.drawString(52, 580, f"Total: INR {quotation.total:,.2f}")
    pdf.save(); return out.getvalue()
