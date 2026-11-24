from django.contrib.admin.apps import AdminConfig

class RoyalVenueAdminConfig(AdminConfig):
    default_site = "config.admin_site.RoyalVenueAdminSite"
