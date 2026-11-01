"""Atomic account and profile services for Registrar-managed people.

Each public service owns its transaction. Callers must not wrap these in
another atomic block in order to make them safe; a direct call is enough.
``IntegrityError`` is deliberately not caught here. It propagates after the
transaction has rolled back so views can present a readable form error.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from academics.models import Instructor, Student

CONFLICT_ERROR = (
    "This record could not be saved because it conflicts with existing data. "
    "Please review the values and try again."
)

_USER_FIELDS = frozenset(
    {
        "username",
        "first_name",
        "last_name",
        "middle_name",
        "email",
        "phone",
        "address",
    }
)
_STUDENT_PROFILE_FIELDS = frozenset(
    {"student_number", "curriculum", "year_level"}
)
_INSTRUCTOR_PROFILE_FIELDS = frozenset({"employee_number"})


def _validated_user_fields(user_fields, *, allow_username):
    fields = dict(user_fields or {})
    unknown = set(fields) - _USER_FIELDS
    if unknown:
        raise ValidationError(
            "One or more submitted fields cannot be changed through this service."
        )
    if not allow_username and "username" in fields:
        raise ValidationError("The username is managed separately.")
    return fields


def _validated_profile_fields(profile_fields, allowed):
    fields = dict(profile_fields or {})
    unknown = set(fields) - allowed
    if unknown:
        raise ValidationError(
            "One or more submitted fields cannot be changed through this service."
        )
    return fields


def create_student_account(
    *,
    username,
    password,
    student_number,
    curriculum,
    year_level,
    **user_fields,
):
    """Create a student user and profile together, or not at all."""
    fields = _validated_user_fields(user_fields, allow_username=False)
    with transaction.atomic():
        user = User(username=username, role=User.Role.STUDENT, **fields)
        validate_password(password, user=user)
        user.set_password(password)
        user.save()
        student = Student(
            user=user,
            student_number=student_number,
            curriculum=curriculum,
            year_level=year_level,
        )
        student.save()
    return student


def create_instructor_account(
    *,
    username,
    password,
    employee_number,
    **user_fields,
):
    """Create an instructor user and profile together, or not at all."""
    fields = _validated_user_fields(user_fields, allow_username=False)
    with transaction.atomic():
        user = User(username=username, role=User.Role.INSTRUCTOR, **fields)
        validate_password(password, user=user)
        user.set_password(password)
        user.save()
        instructor = Instructor(user=user, employee_number=employee_number)
        instructor.save()
    return instructor


def update_student_profile(
    student,
    *,
    user_fields=None,
    profile_fields=None,
    password=None,
):
    """Update a student's linked user and profile in one transaction."""
    fields = _validated_user_fields(user_fields, allow_username=True)
    profile_data = _validated_profile_fields(
        profile_fields, _STUDENT_PROFILE_FIELDS
    )
    with transaction.atomic():
        profile = Student.objects.select_for_update().get(pk=student.pk)
        user = User.objects.select_for_update().get(pk=profile.user_id)
        if user.role != User.Role.STUDENT:
            raise ValidationError("The linked user is not a student account.")
        if Instructor.objects.filter(user_id=user.pk).exists():
            raise ValidationError(
                "A user cannot have both a student and an instructor profile."
            )
        for name, value in fields.items():
            setattr(user, name, value)
        if password:
            validate_password(password, user=user)
            user.set_password(password)
        for name, value in profile_data.items():
            setattr(profile, name, value)
        user.save()
        profile.save()
    return profile


def update_instructor_profile(
    instructor,
    *,
    user_fields=None,
    profile_fields=None,
    password=None,
):
    """Update an instructor's linked user and profile in one transaction."""
    fields = _validated_user_fields(user_fields, allow_username=True)
    profile_data = _validated_profile_fields(
        profile_fields, _INSTRUCTOR_PROFILE_FIELDS
    )
    with transaction.atomic():
        profile = Instructor.objects.select_for_update().get(pk=instructor.pk)
        user = User.objects.select_for_update().get(pk=profile.user_id)
        if user.role != User.Role.INSTRUCTOR:
            raise ValidationError("The linked user is not an instructor account.")
        if Student.objects.filter(user_id=user.pk).exists():
            raise ValidationError(
                "A user cannot have both a student and an instructor profile."
            )
        for name, value in fields.items():
            setattr(user, name, value)
        if password:
            validate_password(password, user=user)
            user.set_password(password)
        for name, value in profile_data.items():
            setattr(profile, name, value)
        user.save()
        profile.save()
    return profile
