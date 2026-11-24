from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from .forms import CustomerSignUpForm

class CustomerLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        requested = self.get_redirect_url()
        if requested:
            return requested
        user = self.request.user
        if user.is_superuser or user.role in {"VENUE_OWNER", "SUPERADMIN"}:
            return "/owner/"
        return "/"

def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = CustomerSignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your customer account is ready. Sign in to continue.")
        return redirect("login")
    return render(request, "accounts/signup.html", {"form": form})

@require_POST
def signout(request):
    logout(request)
    messages.success(request, "You are signed out.")
    return redirect("home")

@login_required
def customer_dashboard(request):
    if request.user.is_superuser or request.user.role in {"VENUE_OWNER", "SUPERADMIN"}:
        return redirect("owner-dashboard")
    from apps.bookings.models import Booking
    bookings = Booking.objects.filter(customer=request.user).select_related("venue").order_by("-created_at")
    return render(request, "accounts/customer_dashboard.html", {"bookings": bookings})
