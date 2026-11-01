"""Custom Django AdminSite enforcing application role policy."""

from django.contrib.admin import AdminSite

from accounts.models import User


class ADSAdminSite(AdminSite):
    site_header = "ADS Enrollment System Administration"
    site_title = "ADS Admin"
    index_title = "Administration"

    def has_permission(self, request):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if not getattr(user, "is_staff", False):
            return False
        if getattr(user, "role", None) != User.Role.ADMINISTRATOR:
            return False
        # Do not rely on is_superuser as a bypass; Django model permissions still apply.
        return True


ads_admin_site = ADSAdminSite(name="ads_admin")
