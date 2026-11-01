"""Reusable authorization helpers for the ADS Enrollment System.

Authentication and role authorization are kept separate. These helpers
do not infer permissions from is_staff or is_superuser.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from accounts.models import User
from academics.models import Instructor, Student


def get_dashboard_url(user):
    """Return the named URL for the user's role dashboard.

    Unauthenticated and inactive users have no dashboard; callers are
    expected to send them to the login page.
    """
    if not user.is_authenticated or not getattr(user, "is_active", False):
        return "login"
    role = getattr(user, "role", None)
    if role == User.Role.STUDENT:
        return "student_dashboard"
    if role == User.Role.INSTRUCTOR:
        return "instructor_dashboard"
    if role == User.Role.CASHIER:
        return "cashier_dashboard"
    if role == User.Role.REGISTRAR:
        return "registrar_dashboard"
    if role == User.Role.ADMINISTRATOR:
        return "administrator_dashboard"
    return "login"


def role_required(*roles, login_url=None):
    """Require authentication and that the user has one of the allowed roles.

    Anonymous users are redirected to login. Authenticated users without
    the required role receive a 403 (PermissionDenied).
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(), login_url=login_url
                )
            if not user.is_active:
                raise PermissionDenied
            user_role = getattr(user, "role", None)
            if user_role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


class RoleRequiredMixin:
    """Mixin for class-based views requiring specific roles.

    The check order matches :func:`role_required`: anonymous users are sent
    to login, inactive authenticated users receive ``PermissionDenied``, and
    active users with the wrong role receive ``PermissionDenied``.
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not user.is_active:
            raise PermissionDenied
        user_role = getattr(user, "role", None)
        if user_role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class RegistrarRequiredMixin(RoleRequiredMixin):
    """Registrar-only access for academic and people write operations."""

    allowed_roles = (User.Role.REGISTRAR,)


class RegistrarReadOnlyMixin(RoleRequiredMixin):
    """Read access for Registrars and Administrators.

    Write views must use :class:`RegistrarRequiredMixin`; this mixin is for
    list and detail screens only so Administrators remain read-only.
    """

    allowed_roles = (User.Role.REGISTRAR, User.Role.ADMINISTRATOR)


def get_student_for_user(user):
    """Return the Student instance for the active authenticated user, or None."""
    if not user or not user.is_authenticated or not user.is_active:
        return None
    try:
        return Student.objects.select_related("user", "curriculum").get(user=user)
    except Student.DoesNotExist:
        return None


def is_student_owner(user, student_obj):
    """Check if the active user owns the given student record."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if student_obj is None:
        return False
    if getattr(student_obj, "user_id", None) is not None:
        return student_obj.user_id == user.pk
    if hasattr(student_obj, "user"):
        try:
            return student_obj.user_id == user.pk
        except Exception:
            return False
    return False


def get_instructor_for_user(user):
    """Return the Instructor instance for the active authenticated user, or None."""
    if not user or not user.is_authenticated or not user.is_active:
        return None
    try:
        return Instructor.objects.select_related("user").get(user=user)
    except Instructor.DoesNotExist:
        return None


def get_assigned_sections(instructor):
    """Return sections assigned to the instructor (if instructor exists)."""
    if instructor is None:
        return []
    from scheduling.models import Section

    return Section.objects.filter(instructor=instructor).select_related(
        "course", "term", "instructor"
    )


def is_instructor_assigned(user, section):
    """Check if the instructor user is assigned to the given section."""
    instructor = get_instructor_for_user(user)
    if instructor is None or section is None:
        return False
    section_instructor_id = getattr(section, "instructor_id", None)
    if section_instructor_id is not None:
        return section_instructor_id == instructor.pk
    if hasattr(section, "instructor"):
        try:
            return getattr(section.instructor, "pk") == instructor.pk
        except Exception:
            return False
    return False
