from django.db import models


class Section(models.Model):
    """An offering of a course in a term, taught by one instructor.

    A section carries a single weekly schedule and a free-text room label.
    There is no separate room or section-meeting table in the simplified
    design.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(
        "academics.Course", on_delete=models.PROTECT, db_column="course_id"
    )
    term = models.ForeignKey(
        "academics.AcademicTerm", on_delete=models.PROTECT, db_column="term_id"
    )
    instructor = models.ForeignKey(
        "academics.Instructor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="instructor_id",
    )
    section_code = models.CharField(max_length=20)
    capacity = models.IntegerField()
    room_code = models.CharField(max_length=30, blank=True)
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices, null=True, blank=True
    )
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    class Meta:
        db_table = "section"
        ordering = ["term_id", "course_id", "section_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "term", "section_code"],
                name="uq_section_course_term_code",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name="ck_section_capacity_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(start_time__isnull=True)
                    | models.Q(end_time__isnull=True)
                    | models.Q(end_time__gt=models.F("start_time"))
                ),
                name="ck_section_time_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(day_of_week__isnull=True)
                    | models.Q(day_of_week__gte=0, day_of_week__lte=6)
                ),
                name="ck_section_day_of_week_range",
            ),
        ]

    def __str__(self):
        return f"{self.course.course_code} {self.section_code} ({self.term})"
