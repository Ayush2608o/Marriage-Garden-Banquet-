from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

OWNER_ACCESS = {
    "venues": {"venue": ("view", "add", "change", "delete"), "enquiry": ("view", "add", "change")},
    "vendors": {"vendor": ("view", "add", "change", "delete"), "vendorportfolioimage": ("view", "add", "change", "delete")},
    "staff": {"staffmember": ("view", "add", "change"), "staffshift": ("view", "add", "change"), "employeeattendance": ("view", "add", "change")},
    "bookings": {"booking": ("view", "add", "change")},
    "quotations": {"quotation": ("view", "add", "change")},
    "payments": {"payment": ("view", "add", "change")},
    "whatsapp": {"whatsappthread": ("view", "add", "change"), "whatsappmessage": ("view", "add", "change")},
    "customers": {"customerprofile": ("view",)},
    "audit_logs": {"accesslog": ("view",)},
}

def sync_owner_role():
    group, _ = Group.objects.get_or_create(name="Venue Owners")
    permissions = []
    for app_label, models in OWNER_ACCESS.items():
        for model_name, actions in models.items():
            model = apps.get_model(app_label, model_name)
            content_type = ContentType.objects.get_for_model(model)
            permissions.extend(Permission.objects.filter(content_type=content_type, codename__in=[f"{action}_{model_name}" for action in actions]))
    group.permissions.set(permissions)
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(role="VENUE_OWNER").iterator():
        user.groups.add(group)
    return group
