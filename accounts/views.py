from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import User
from accounts.permissions import (
    get_dashboard_url,
    get_instructor_for_user,
    get_student_for_user,
    role_required,
)


class RoleAwareLoginView(LoginView):
    """Login view that routes authenticated users to their role dashboard.

    A stale authenticated session for an inactive account is logged out
    before the login form is rendered, preventing a redirect loop between
    the login page and a dashboard the account may not access.
    """

    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_active:
            logout(request)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to and redirect_to != self.request.path:
            return redirect_to
        return reverse(get_dashboard_url(self.request.user))


@login_required
def dashboard(request):
    """Role-aware dashboard dispatcher."""
    if not request.user.is_active:
        logout(request)
        return redirect("login")
    return redirect(get_dashboard_url(request.user))


@role_required(User.Role.STUDENT)
def student_dashboard(request):
    student = get_student_for_user(request.user)
    return render(
        request,
        "accounts/dashboards/student.html",
        {"student": student},
    )


@role_required(User.Role.INSTRUCTOR)
def instructor_dashboard(request):
    instructor = get_instructor_for_user(request.user)
    return render(
        request,
        "accounts/dashboards/instructor.html",
        {"instructor": instructor},
    )


@role_required(User.Role.CASHIER)
def cashier_dashboard(request):
    return render(request, "accounts/dashboards/cashier.html")


@role_required(User.Role.REGISTRAR)
def registrar_dashboard(request):
    return render(request, "accounts/dashboards/registrar.html")


@role_required(User.Role.ADMINISTRATOR)
def administrator_dashboard(request):
    return render(request, "accounts/dashboards/administrator.html")
