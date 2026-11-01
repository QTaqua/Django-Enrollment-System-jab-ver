from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user.

    Extends ``AbstractUser`` so Django's authentication and admin work
    unchanged.  Personal names and contact details live here so that the
    ``student`` and ``instructor`` profiles do not duplicate them.
    ``role`` is the coarse-grained label used for authorisation decisions.
    """

    class Role(models.TextChoices):
        ADMINISTRATOR = "ADMINISTRATOR", "Administrator"
        REGISTRAR = "REGISTRAR", "Registrar"
        CASHIER = "CASHIER", "Cashier"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"
        STUDENT = "STUDENT", "Student"

    middle_name = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    class Meta:
        db_table = "app_user"
        ordering = ["username"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.get_username()
