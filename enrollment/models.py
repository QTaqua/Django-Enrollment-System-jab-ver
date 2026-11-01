from decimal import Decimal

from django.db import models
from django.utils import timezone

# PSU 1.00-5.00 grading scale.  INC and DRP are represented by
# ``EnrollmentDetail.result_status``, never by a numeric grade.
PSU_GRADE_VALUES = [
    Decimal("1.00"),
    Decimal("1.25"),
    Decimal("1.50"),
    Decimal("1.75"),
    Decimal("2.00"),
    Decimal("2.25"),
    Decimal("2.50"),
    Decimal("2.75"),
    Decimal("3.00"),
    Decimal("4.00"),
    Decimal("5.00"),
]


class Enrollment(models.Model):
    """One student's enrollment for one academic term."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        "academics.Student", on_delete=models.PROTECT, db_column="student_id"
    )
    term = models.ForeignKey(
        "academics.AcademicTerm",
        on_delete=models.PROTECT,
        db_column="term_id",
    )
    enrollment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    class Meta:
        db_table = "enrollment"
        ordering = ["-enrollment_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "term"],
                name="uq_enrollment_student_term",
            ),
        ]

    def __str__(self):
        return f"{self.student.student_number} - {self.term}"


class EnrollmentDetail(models.Model):
    """One section added to an enrollment, with its final result.

    The course is derived from ``section.course``; no redundant course column
    is stored.  The separate ``student_course_result`` table from the original
    design is folded in here.
    """

    class Status(models.TextChoices):
        ENROLLED = "ENROLLED", "Enrolled"
        DROPPED = "DROPPED", "Dropped"
        COMPLETED = "COMPLETED", "Completed"

    class ResultStatus(models.TextChoices):
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"
        INCOMPLETE = "INCOMPLETE", "Incomplete"
        DROPPED = "DROPPED", "Dropped"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    id = models.AutoField(primary_key=True)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="details",
        db_column="enrollment_id",
    )
    section = models.ForeignKey(
        "scheduling.Section",
        on_delete=models.PROTECT,
        related_name="enrollment_details",
        db_column="section_id",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ENROLLED
    )
    enrolled_at = models.DateTimeField(default=timezone.now)
    final_grade = models.DecimalField(
        max_digits=4, decimal_places=2, null=True, blank=True
    )
    result_status = models.CharField(
        max_length=20,
        choices=ResultStatus.choices,
        null=True,
        blank=True,
    )
    recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "enrollment_detail"
        ordering = ["enrollment_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "section"],
                name="uq_enrollment_detail_section",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(final_grade__isnull=True)
                    | models.Q(final_grade__in=PSU_GRADE_VALUES)
                ),
                name="ck_enrollment_detail_psu_grade",
            ),
        ]

    @property
    def course(self):
        """Course for this detail, derived through the section."""
        return self.section.course

    def __str__(self):
        return f"{self.enrollment} -> {self.section}"
