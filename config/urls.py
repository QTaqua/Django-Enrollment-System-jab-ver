"""
URL configuration for config project.
"""
from django.contrib.auth import logout
from django.urls import include, path
from django.shortcuts import redirect

from accounts.permissions import get_dashboard_url
from accounts import admin_site

ads_admin_site = admin_site.ads_admin_site


def home_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_active:
            return redirect(get_dashboard_url(request.user))
        logout(request)
    return redirect("login")


urlpatterns = [
    path("", home_redirect, name="home"),
    path("admin/", ads_admin_site.urls),
    path("", include("accounts.urls")),
    path("academics/", include("academics.urls")),
    path("sections/", include("scheduling.urls")),
    path("people/", include("accounts.people_urls")),
    path("", include("enrollment.urls")),
]
