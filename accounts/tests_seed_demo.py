"""Tests for the Phase 9C `seed_demo` management command.

These exercise the dry-run rollback, the committed seed, idempotent rerun, the
expected negative-scenario rejections, and demo-only teardown. They never touch
a real Administrator account (the test database has none).
"""

from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from academics.models import College, Course, Curriculum, Program
from finance.models import (
    Adjustment, Assessment, AssessmentVersion, FeeRule, Payment, ScholarshipAward,
)
from finance.services import assessment_balance
from scheduling.models import Room, Section

User = get_user_model()


class SeedDemoDryRunTests(TestCase):
    def test_dry_run_persists_nothing(self):
        out = StringIO()
        call_command("seed_demo", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("DRY-RUN complete", output)
        # Nothing persisted: the test DB had no business rows and still has none.
        self.assertEqual(College.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Section.objects.count(), 0)
        self.assertEqual(User.objects.count(), 0)
        # The report shows work was planned and all negatives rejected as expected.
        self.assertIn("creates=", output)
        self.assertIn("expected-rejections-ok=6", output)
        self.assertIn("rejections-missing=0", output)

    def test_requires_flag_to_run(self):
        with self.assertRaises(Exception):
            call_command("seed_demo", stdout=StringIO())


class SeedDemoCommitTests(TestCase):
    def test_commit_creates_expected_and_is_idempotent(self):
        out = StringIO()
        call_command("seed_demo", "--commit", stdout=out)

        self.assertEqual(College.objects.count(), 5)
        self.assertEqual(Program.objects.count(), 21)
        self.assertEqual(Course.objects.count(), 11)
        self.assertEqual(Curriculum.objects.count(), 1)
        self.assertEqual(Section.objects.count(), 15)  # 13 main/sem2 + 2 historical
        self.assertEqual(Room.objects.count(), 6)       # normalized rooms from section codes
        self.assertEqual(FeeRule.objects.count(), 8)    # 7 active + 1 inactive (conflict demo)
        # 14 confirmed main-term assessments + 1 historical prior-term (scenario 10)
        self.assertEqual(Assessment.objects.count(), 15)
        self.assertEqual(AssessmentVersion.objects.count(), 15)  # 14 v1 + S13 v2 revision
        self.assertEqual(Payment.objects.count(), 7)    # scenarios 2,3,4,5,6,11,12
        self.assertEqual(ScholarshipAward.objects.count(), 2)  # approved + pending
        self.assertEqual(Adjustment.objects.count(), 2)        # credit + reversal
        self.assertEqual(User.objects.filter(username__startswith="demo.").count(), 25)

        # Fee-rule-computed balances (DEMO figures):
        a1 = Assessment.objects.get(enrollment__student__student_number="2026-0001")
        a6 = Assessment.objects.get(enrollment__student__student_number="2026-0006",
                                    enrollment__term__academic_year="2026-2027")
        a7 = Assessment.objects.get(enrollment__student__student_number="2026-0007",
                                    enrollment__term__academic_year="2026-2027")
        self.assertEqual(assessment_balance(assessment=a1), Decimal("9650.00"))  # unpaid
        self.assertEqual(assessment_balance(assessment=a6), Decimal("2950.00"))  # 5950 - 3000
        self.assertEqual(assessment_balance(assessment=a7), Decimal("0.00"))     # fully paid

        # Rerun is idempotent: no new rows, every negative still rejects.
        out2 = StringIO()
        call_command("seed_demo", "--commit", stdout=out2)
        self.assertIn("creates=0", out2.getvalue())
        self.assertIn("expected-rejections-ok=6", out2.getvalue())
        self.assertEqual(College.objects.count(), 5)
        self.assertEqual(Section.objects.count(), 15)
        self.assertEqual(Assessment.objects.count(), 15)
        self.assertEqual(Payment.objects.count(), 7)

    def test_teardown_removes_only_demo_data(self):
        call_command("seed_demo", "--commit", stdout=StringIO())
        self.assertEqual(College.objects.count(), 5)

        out = StringIO()
        call_command("seed_demo", "--teardown", "--confirm", stdout=out)
        self.assertIn("Teardown complete", out.getvalue())
        self.assertEqual(College.objects.count(), 0)
        self.assertEqual(Program.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Section.objects.count(), 0)
        self.assertEqual(Room.objects.count(), 0)
        self.assertEqual(FeeRule.objects.count(), 0)
        self.assertEqual(Assessment.objects.count(), 0)
        self.assertEqual(AssessmentVersion.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(ScholarshipAward.objects.count(), 0)
        self.assertEqual(Adjustment.objects.count(), 0)
        self.assertEqual(User.objects.filter(username__startswith="demo.").count(), 0)
