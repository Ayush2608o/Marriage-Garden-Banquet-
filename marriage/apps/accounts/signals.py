from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from .rbac import sync_owner_role

@receiver(post_migrate)
def configure_role_groups(sender, **kwargs):
    sync_owner_role()

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_owner_group(sender, instance, **kwargs):
    group = Group.objects.filter(name="Venue Owners").first()
    if not group or not instance.pk:
        return
    if instance.role == "VENUE_OWNER":
        instance.groups.add(group)
    else:
        instance.groups.remove(group)
