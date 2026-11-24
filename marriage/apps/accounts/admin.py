from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class RoyalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Royal Venue", {"fields": ("role", "phone")}),)
    list_display = ("username", "email", "role", "phone", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
