"""Seed the HTU demonstration dataset (Phase 9C).

Implements the approved Phase 9B blueprint as a safe, repeatable, nine-stage
seeder for the disposable test database. Everything written here is **fictional
demonstration data** except the HTU college and program *names*, which are
publicly sourced. No official HTU curriculum, course, fee, or person is
represented; all amounts are demonstration amounts, not official HTU fees.

Usage:
    python manage.py seed_demo --dry-run   # preview only; rolls back, persists nothing
    python manage.py seed_demo             # persistent seed (requires --commit)
    python manage.py seed_demo --commit     # persistent seed
    python manage.py seed_demo --teardown            # preview demo-data deletion
    python manage.py seed_demo --teardown --confirm  # delete demo data (reverse order)

Design notes (verified against the live models/services, not just the blueprint):
* Rule-bearing operations use the existing services -- ``scheduling.services.
  create_section`` and ``enrollment.services.create_enrollment /
  enroll_in_section / confirm_enrollment`` -- so demo data obeys the same
  validation as production use.
* Direct ORM is used only where no service exists: the academic catalog, terms,
  users/profiles, historical graded ``EnrollmentDetail`` rows (no grading service
  and ``create_enrollment`` rejects the closed historical term), and
  ``finance.Assessment`` creation (no create/finalize service). Payments use
  ``finance.services.record_payment``.
* Idempotency uses each model's natural unique key. Identity and historical rows
  are create-only (never overwritten, passwords never reset); only descriptive,
  non-key fields may be updated on rerun, and never on a section that already has
  enrollment details. A conflicting natural key stops the run with an explanation.
* ``--dry-run`` runs every stage inside one ``transaction.atomic()`` and raises a
  sentinel caught *outside* the block, forcing a rollback. Service ``atomic``
  blocks become nested savepoints and roll back with the outer transaction. The
  services perform database work only (no email/file/cache/external calls), so a
  rollback fully neutralizes a dry run.
"""

from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import (
    AcademicTerm,
    College,
    Course,
    CoursePrerequisite,
    Curriculum,
    CurriculumCourse,
    Instructor,
    Program,
    Student,
)
from enrollment.models import Enrollment, EnrollmentDetail
from enrollment.services import (
    confirm_enrollment,
    create_enrollment,
    enroll_in_section,
)
from finance.models import (
    Adjustment,
    Assessment,
    AssessmentLine,
    AssessmentVersion,
    FeeRule,
    Payment,
    PaymentAllocation,
    ScholarshipAward,
)
from finance.services import (
    approve_adjustment,
    approve_scholarship,
    assessment_balance,
    create_adjustment,
    create_draft_assessment,
    create_scholarship,
    finalize_assessment,
    record_payment,
    reverse_payment,
    revise_assessment,
)
from scheduling.models import Room, Section
from scheduling.services import create_section

User = get_user_model()

# --- demo markers (used for identification and teardown) -------------------
DEMO_USERNAME_PREFIX = "demo."
DEMO_STUDENT_PREFIX = "2026-"
DEMO_RECEIPT_PREFIX = "DEMO-OR-"
DEMO_CURRICULUM_CODE = "SIM-BSIT-2026"
DEMO_ASSESSMENT_REMARK = "DEMO - not official HTU tuition"
DEMO_PASSWORD = "HtuDemo!2026"  # demonstration accounts only; never printed/reset

# --- verified HTU catalog (college and program *names* are publicly sourced) ---
COLLEGES = [
    ("CBACHM", "College of Business, Accountancy, and Hospitality Management"),
    ("CEA", "College of Education and Arts"),
    ("CET", "College of Engineering and Technology"),
    ("CNHS", "College of Nursing and Health Sciences"),
    ("CCJE", "College of Criminal Justice Education"),
]
# One Program row per published program/major combination. This is an
# application modeling convenience -- the schema has no major/specialization
# entity -- and is NOT a faithful representation of HTU's institutional
# structure (these are specializations within single degree programs).
PROGRAMS = [
    ("CBACHM", "BSA", "Bachelor of Science in Accountancy"),
    ("CBACHM", "BSBA-MM", "BS Business Administration Major in Marketing Management"),
    ("CBACHM", "BSBA-HRM", "BS Business Administration Major in Human Resource Management"),
    ("CBACHM", "BSHM", "Bachelor of Science in Hospitality Management"),
    ("CEA", "ABPOLSCI", "Bachelor of Arts Major in Political Science"),
    ("CEA", "BEED", "Bachelor of Elementary Education"),
    ("CEA", "BSED-FIL", "Bachelor of Secondary Education Major in Filipino"),
    ("CEA", "BSED-ENG", "Bachelor of Secondary Education Major in English"),
    ("CEA", "BSED-MATH", "Bachelor of Secondary Education Major in Mathematics"),
    ("CEA", "BSED-RE", "Bachelor of Secondary Education Major in Religious Education"),
    ("CEA", "BSED-VE", "Bachelor of Secondary Education Major in Values Education"),
    ("CET", "BSCE-CEM", "BS Civil Engineering Major in Construction Engineering Management"),
    ("CET", "BSCE-GEO", "BS Civil Engineering Major in Geotechnical Engineering"),
    ("CET", "BSCE-STR", "BS Civil Engineering Major in Structural Engineering"),
    ("CET", "BSCE-WRE", "BS Civil Engineering Major in Water Resource Engineering"),
    ("CET", "BSGE", "Bachelor of Science in Geodetic Engineering"),
    ("CET", "BSCPE", "Bachelor of Science in Computer Engineering"),
    ("CET", "BSIT", "Bachelor of Science in Information Technology"),
    ("CNHS", "BSN", "Bachelor of Science in Nursing"),
    ("CNHS", "BSBIO-MB", "Bachelor of Science in Biology Major in Medical Biology"),
    ("CCJE", "BSCRIM", "Bachelor of Science in Criminology"),
]

# --- simulation BSIT curriculum (fictional; SIM- prefixed) -----------------
_CAT = CurriculumCourse.Category
# code, title, units, category, year_level, recommended_semester
COURSES = [
    ("SIM-IT101", "Introduction to Computing", "3.0", _CAT.CORE, 1, 1),
    ("SIM-CS101", "Computer Programming 1", "3.0", _CAT.CORE, 1, 1),
    ("SIM-GE101", "Mathematics in the Modern World", "3.0", _CAT.GENERAL_EDUCATION, 1, 1),
    ("SIM-GE102", "Purposive Communication", "3.0", _CAT.GENERAL_EDUCATION, 1, 1),
    ("SIM-PE101", "Physical Education 1", "2.0", _CAT.PHYSICAL_EDUCATION, 1, 1),
    ("SIM-NSTP101", "NSTP 1", "3.0", _CAT.NSTP, 1, 1),
    ("SIM-CS102", "Computer Programming 2", "3.0", _CAT.CORE, 1, 2),
    ("SIM-IT102", "Discrete Structures", "3.0", _CAT.CORE, 1, 2),
    ("SIM-CS201", "Data Structures and Algorithms", "3.0", _CAT.MAJOR, 2, 1),
    ("SIM-IT201", "Web Systems and Technologies", "3.0", _CAT.MAJOR, 2, 1),
    ("SIM-IT202", "Database Management Systems", "3.0", _CAT.MAJOR, 2, 1),
]
PREREQS = [
    ("SIM-CS102", "SIM-CS101"),
    ("SIM-IT102", "SIM-GE101"),
    ("SIM-CS201", "SIM-CS102"),
    ("SIM-IT201", "SIM-CS102"),
    ("SIM-IT202", "SIM-IT102"),
]

# --- academic terms --------------------------------------------------------
HIST_YEAR, HIST_SEM = "2025-2026", 2
MAIN_YEAR, MAIN_SEM = "2026-2027", 1
SEM2_YEAR, SEM2_SEM = "2026-2027", 2
TERMS = [
    (HIST_YEAR, HIST_SEM, date(2026, 1, 5), date(2026, 5, 15), False),
    (MAIN_YEAR, MAIN_SEM, date(2026, 8, 10), date(2026, 12, 18), True),
    (SEM2_YEAR, SEM2_SEM, date(2027, 1, 5), date(2027, 5, 14), False),
]

_DOW = Section.DayOfWeek
# key, course_code, instr#, term-key, day, start, end, room, capacity, status
MAIN_SECTIONS = [
    ("IT101-A", "SIM-IT101", 1, "main", _DOW.MONDAY, time(8, 0), time(9, 30), "TECH-201", 30, Section.Status.OPEN),
    ("CS101-A", "SIM-CS101", 2, "main", _DOW.MONDAY, time(10, 0), time(11, 30), "LAB-A", 30, Section.Status.OPEN),
    ("GE101-A", "SIM-GE101", 3, "main", _DOW.TUESDAY, time(8, 0), time(9, 30), "MAIN-101", 40, Section.Status.OPEN),
    ("GE102-A", "SIM-GE102", 3, "main", _DOW.WEDNESDAY, time(8, 0), time(9, 30), "MAIN-101", 40, Section.Status.OPEN),
    ("PE101-A", "SIM-PE101", 4, "main", _DOW.FRIDAY, time(8, 0), time(9, 30), "MAIN-102", 40, Section.Status.OPEN),
    ("NSTP101-A", "SIM-NSTP101", 4, "main", _DOW.FRIDAY, time(10, 0), time(11, 30), "MAIN-102", 40, Section.Status.OPEN),
    ("CS101-B", "SIM-CS101", 2, "main", _DOW.THURSDAY, time(10, 0), time(11, 30), "LAB-A", 2, Section.Status.OPEN),
    ("CS201-A", "SIM-CS201", 2, "main", _DOW.MONDAY, time(13, 0), time(14, 30), "LAB-B", 30, Section.Status.OPEN),
    ("IT201-A", "SIM-IT201", 1, "main", _DOW.MONDAY, time(13, 0), time(14, 30), "LAB-A", 30, Section.Status.OPEN),
    ("IT202-A", "SIM-IT202", 5, "main", _DOW.TUESDAY, time(13, 0), time(14, 30), "TECH-202", 30, Section.Status.OPEN),
    ("CS102-C", "SIM-CS102", 2, "main", _DOW.WEDNESDAY, time(10, 0), time(11, 30), "LAB-A", 30, Section.Status.CLOSED),
    ("IT101-TBA", "SIM-IT101", 1, "main", None, None, None, "", 30, Section.Status.OPEN),
    ("CS102-S2", "SIM-CS102", 2, "sem2", _DOW.TUESDAY, time(8, 0), time(9, 30), "LAB-A", 30, Section.Status.OPEN),
]
HIST_SECTIONS = [
    ("CS102-H", "SIM-CS102", 2, _DOW.MONDAY, time(8, 0), time(9, 30), "LAB-A", 40),
    ("IT102-H", "SIM-IT102", 1, _DOW.TUESDAY, time(8, 0), time(9, 30), "LAB-A", 40),
]

# --- DEMO fee rules (fictional; clearly NOT official HTU fees) --------------
# name, category, scope, course_code, program_code, computation, amount, active
# Demonstrates category stacking (tuition + misc + library + registration + lab)
# and COURSE > PROGRAM > GENERAL tuition precedence. The last rule is INACTIVE;
# activating it alongside the general misc rule makes finalization fail (a live
# conflict), which is why it ships disabled.
FEE_RULES = [
    ("[DEMO] Tuition — general (per unit)", "TUITION", "GENERAL", None, None, "PER_UNIT", "500", True),
    ("[DEMO] Tuition — BSIT program rate (per unit)", "TUITION", "PROGRAM", None, "BSIT", "PER_UNIT", "450", True),
    ("[DEMO] Tuition premium — Data Structures (per unit)", "TUITION", "COURSE", "SIM-CS201", None, "PER_UNIT", "600", True),
    ("[DEMO] Miscellaneous fee (fixed)", "MISCELLANEOUS", "GENERAL", None, None, "FIXED", "1500", True),
    ("[DEMO] Library fee (fixed)", "LIBRARY", "GENERAL", None, None, "FIXED", "300", True),
    ("[DEMO] Registration fee (fixed)", "REGISTRATION", "GENERAL", None, None, "FIXED", "200", True),
    ("[DEMO] Computer laboratory fee — Database Mgmt (fixed)", "LABORATORY", "COURSE", "SIM-IT202", None, "FIXED", "800", True),
    ("[DEMO] Conflicting miscellaneous rule (INACTIVE — activate to see finalization blocked)", "MISCELLANEOUS", "GENERAL", None, None, "FIXED", "1800", False),
]


class _DryRunRollback(Exception):
    """Raised at the end of a dry run to force the outer transaction to roll back."""


class SeedConflict(CommandError):
    """A natural key already exists with values that conflict with the blueprint."""


class _Report:
    def __init__(self):
        self.actions = {"create": 0, "update": 0, "skip": 0}
        self.lines = []
        self.conflicts = []
        self.rejections_ok = []
        self.rejections_missing = []

    def record(self, action, label, detail=""):
        self.actions[action] += 1
        self.lines.append(f"  [{action.upper():6}] {label}{(' - ' + detail) if detail else ''}")

    def rejection_ok(self, label, message):
        self.rejections_ok.append(f"  [REJECT-OK] {label}: {message}")

    def rejection_missing(self, label):
        self.rejections_missing.append(f"  [REJECT-MISSING] {label}: expected a ValidationError but none was raised")


class Command(BaseCommand):
    help = "Seed the HTU demonstration dataset (Phase 9C). Dry-run by default-safe."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Preview all actions inside a transaction and roll back; persist nothing.")
        parser.add_argument("--commit", action="store_true",
                            help="Persist the seed. Required for a real (non-dry) population run.")
        parser.add_argument("--teardown", action="store_true",
                            help="Preview (or with --confirm, execute) reverse-order deletion of demo data.")
        parser.add_argument("--confirm", action="store_true",
                            help="With --teardown, actually delete the demo data.")

    # -- entry point --------------------------------------------------------
    def handle(self, *args, **opts):
        if opts["teardown"]:
            return self._teardown(confirm=opts["confirm"])

        dry_run = opts["dry_run"]
        if not dry_run and not opts["commit"]:
            raise CommandError(
                "Refusing to seed persistently without a flag. Use --dry-run to "
                "preview safely, or --commit to actually populate the database."
            )

        report = _Report()
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"seed_demo: {'DRY-RUN (no changes will persist)' if dry_run else 'COMMIT (changes will persist)'}"
        ))
        try:
            with transaction.atomic():
                ctx = {}
                self._stage1_catalog(report, ctx)
                self._stage2_terms(report, ctx)
                self._stage3_accounts(report, ctx)
                self._stage4_history(report, ctx)
                self._stage5_sections(report, ctx)
                self._stage6_enrollments(report, ctx)
                self._stage7_finance(report, ctx)
                self._stage8_verify(report, ctx)
                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN complete: outer transaction rolled back; nothing was persisted."
            ))

        self._print_report(report)
        if report.rejections_missing:
            raise CommandError("One or more negative scenarios did not raise as expected (see report).")

    # -- Stage 1: catalog ---------------------------------------------------
    def _stage1_catalog(self, report, ctx):
        self.stdout.write("Stage 1: catalog")
        ctx["colleges"] = {}
        for code, name in COLLEGES:
            ctx["colleges"][code] = self._ensure(
                report, College, {"college_code": code},
                create={"name": name, "is_active": True},
                updatable={"name": name, "is_active": True},
                label=f"College {code}",
            )
        ctx["programs"] = {}
        for college_code, code, name in PROGRAMS:
            ctx["programs"][code] = self._ensure(
                report, Program, {"program_code": code},
                create={"college": ctx["colleges"][college_code], "name": name, "is_active": True},
                updatable={"name": name, "is_active": True},
                immutable={"college_id": ctx["colleges"][college_code].pk},
                label=f"Program {code}",
            )
        ctx["courses"] = {}
        for code, title, units, _cat, _yr, _sem in COURSES:
            ctx["courses"][code] = self._ensure(
                report, Course, {"course_code": code},
                create={"title": title, "units": Decimal(units), "is_active": True},
                updatable={"title": title, "units": Decimal(units), "is_active": True},
                label=f"Course {code}",
            )
        bsit = ctx["programs"]["BSIT"]
        ctx["curriculum"] = self._ensure(
            report, Curriculum,
            {"program": bsit, "curriculum_code": DEMO_CURRICULUM_CODE},
            create={"effective_year": 2026, "is_active": True},
            updatable={"effective_year": 2026, "is_active": True},
            label=f"Curriculum {DEMO_CURRICULUM_CODE}",
        )
        for code, _title, _units, cat, yr, sem in COURSES:
            self._ensure(
                report, CurriculumCourse,
                {"curriculum": ctx["curriculum"], "course": ctx["courses"][code]},
                create={"year_level": yr, "recommended_semester": sem, "course_category": cat},
                updatable={"year_level": yr, "recommended_semester": sem, "course_category": cat},
                label=f"CurriculumCourse {DEMO_CURRICULUM_CODE}/{code}",
            )
        for course_code, prereq_code in PREREQS:
            self._ensure(
                report, CoursePrerequisite,
                {"course": ctx["courses"][course_code],
                 "prerequisite_course": ctx["courses"][prereq_code]},
                create={}, updatable={},
                label=f"Prereq {course_code} needs {prereq_code}",
            )
        self._ensure_fee_rules(report, ctx)

    def _ensure_fee_rules(self, report, ctx):
        for name, cat, scope, course_code, program_code, comp, amount, active in FEE_RULES:
            if FeeRule.objects.filter(name=name).exists():
                report.record("skip", f"FeeRule {name}")
                continue
            FeeRule.objects.create(
                name=name, category=cat, scope=scope,
                course=ctx["courses"].get(course_code) if course_code else None,
                program=ctx["programs"].get(program_code) if program_code else None,
                computation=comp, amount=Decimal(amount), is_active=active, is_demo=True,
            )
            report.record("create", f"FeeRule {name}")

    # -- Stage 2: terms -----------------------------------------------------
    def _stage2_terms(self, report, ctx):
        self.stdout.write("Stage 2: academic terms")
        ctx["terms"] = {}
        keymap = {(HIST_YEAR, HIST_SEM): "hist", (MAIN_YEAR, MAIN_SEM): "main", (SEM2_YEAR, SEM2_SEM): "sem2"}
        for year, sem, start, end, is_open in TERMS:
            term = self._ensure(
                report, AcademicTerm,
                {"academic_year": year, "semester_number": sem},
                create={"start_date": start, "end_date": end, "enrollment_open": is_open},
                updatable={"start_date": start, "end_date": end, "enrollment_open": is_open},
                label=f"AcademicTerm {year} S{sem}",
            )
            ctx["terms"][keymap[(year, sem)]] = term

    # -- Stage 3: accounts & profiles --------------------------------------
    def _stage3_accounts(self, report, ctx):
        self.stdout.write("Stage 3: demo accounts and profiles")
        ctx["instructors"] = {}
        for i in range(1, 6):
            user = self._ensure_user(report, f"{DEMO_USERNAME_PREFIX}instr{i}",
                                     role=User.Role.INSTRUCTOR,
                                     first=f"Instructor{i}", last="Demo")
            ctx["instructors"][i] = self._ensure(
                report, Instructor, {"user": user},
                create={"employee_number": f"EMP-I-{i:04d}"},
                updatable={}, label=f"Instructor EMP-I-{i:04d}",
            )
        for i in range(1, 3):
            self._ensure_user(report, f"{DEMO_USERNAME_PREFIX}registrar{i}",
                              role=User.Role.REGISTRAR, first=f"Registrar{i}", last="Demo")
        ctx["cashiers"] = []
        for i in range(1, 3):
            ctx["cashiers"].append(self._ensure_user(
                report, f"{DEMO_USERNAME_PREFIX}cashier{i}",
                role=User.Role.CASHIER, first=f"Cashier{i}", last="Demo"))
        # A demo administrator (app role only, is_staff=False) used as the
        # finance approver for separation of duties, and for live demo logins
        # without touching the real superuser. Not a Django /admin/ account.
        ctx["admin"] = self._ensure_user(
            report, f"{DEMO_USERNAME_PREFIX}admin1",
            role=User.Role.ADMINISTRATOR, first="Administrator1", last="Demo")

        # Students S01..S15. Year levels: S01-05=1, S06-12=2, S13-15=1. S15 inactive.
        ctx["students"] = {}
        for n in range(1, 16):
            year_level = 2 if 6 <= n <= 12 else 1
            is_active = not (n == 15)
            user = self._ensure_user(
                report, f"{DEMO_USERNAME_PREFIX}stud{n:02d}",
                role=User.Role.STUDENT, first=f"Student{n:02d}", last="Demo",
                is_active=is_active)
            ctx["students"][n] = self._ensure(
                report, Student, {"student_number": f"{DEMO_STUDENT_PREFIX}{n:04d}"},
                create={"user": user, "curriculum": ctx["curriculum"], "year_level": year_level},
                updatable={"year_level": year_level},
                immutable={"user_id": user.pk, "curriculum_id": ctx["curriculum"].pk},
                label=f"Student {DEMO_STUDENT_PREFIX}{n:04d}",
            )

    # -- Stage 4: historical prerequisite records (direct ORM) --------------
    def _stage4_history(self, report, ctx):
        self.stdout.write("Stage 4: historical prerequisite records (direct ORM)")
        hist = ctx["terms"]["hist"]
        ctx["hist_sections"] = {}
        for code, course_code, instr_no, day, start, end, room, cap in HIST_SECTIONS:
            ctx["hist_sections"][code] = self._ensure_section(
                report, code, ctx["courses"][course_code], hist,
                ctx["instructors"][instr_no], day, start, end, room, cap,
                Section.Status.OPEN)
        # Students who must satisfy a year-2 prerequisite: S06-S10 and S12.
        # S11 is deliberately omitted so its CS201 attempt fails the prereq check.
        for n in list(range(6, 11)) + [12]:
            student = ctx["students"][n]
            enr = Enrollment.objects.filter(student=student, term=hist).first()
            if enr is None:
                enr = Enrollment.objects.create(
                    student=student, term=hist, status=Enrollment.Status.CONFIRMED)
                report.record("create", f"Historical Enrollment {student.student_number}")
            else:
                report.record("skip", f"Historical Enrollment {student.student_number}")
            for sec_code in ("CS102-H", "IT102-H"):
                sec = ctx["hist_sections"][sec_code]
                if not EnrollmentDetail.objects.filter(enrollment=enr, section=sec).exists():
                    EnrollmentDetail.objects.create(
                        enrollment=enr, section=sec,
                        status=EnrollmentDetail.Status.COMPLETED,
                        result_status=EnrollmentDetail.ResultStatus.PASSED,
                        final_grade=Decimal("2.00"),
                        recorded_at=timezone.now())
                    report.record("create", f"Historical PASS {student.student_number}/{sec_code} (grade 2.00)")
                else:
                    report.record("skip", f"Historical PASS {student.student_number}/{sec_code}")

    # -- Stage 5: main-term sections (via create_section service) -----------
    def _stage5_sections(self, report, ctx):
        self.stdout.write("Stage 5: main-term sections (service: create_section)")
        ctx["sections"] = {}
        for key, course_code, instr_no, term_key, day, start, end, room, cap, status in MAIN_SECTIONS:
            ctx["sections"][key] = self._ensure_section(
                report, key, ctx["courses"][course_code], ctx["terms"][term_key],
                ctx["instructors"][instr_no], day, start, end, room, cap, status)

    # -- Stage 6: main-term enrollments (services + expected rejections) ----
    def _stage6_enrollments(self, report, ctx):
        self.stdout.write("Stage 6: main-term enrollments (services: create_enrollment/enroll_in_section/confirm)")
        main = ctx["terms"]["main"]
        sem2 = ctx["terms"]["sem2"]
        S = ctx["students"]
        sec = ctx["sections"]
        yr1_common = ["IT101-A", "GE101-A", "GE102-A", "PE101-A", "NSTP101-A"]

        # Happy path first-years. S01-S03 take CS101-A; S04,S05 fill CS101-B (cap 2).
        for n in (1, 2, 3):
            self._svc_enroll(report, S[n], main, [sec["CS101-A"]] + [sec[c] for c in yr1_common], confirm=True)
        for n in (4, 5):
            self._svc_enroll(report, S[n], main, [sec["CS101-B"]] + [sec[c] for c in yr1_common], confirm=True)

        # Continuing students with passed prerequisites: CS201-A + IT202-A (no overlap).
        for n in range(6, 11):
            self._svc_enroll(report, S[n], main, [sec["CS201-A"], sec["IT202-A"]], confirm=True)

        # Scenario 3: S11 (no passed CS102) -> CS201-A rejected (prerequisite).
        enr11 = self._svc_enroll(report, S[11], main, [], confirm=False)
        self._expect_rejection(report, "S11 prerequisite not satisfied (CS201-A)",
                               lambda: enroll_in_section(enrollment=enr11, section=sec["CS201-A"]))
        # leave S11 with a valid enrollment via a no-prereq course
        self._svc_enroll(report, S[11], main, [sec["GE101-A"]], confirm=True)

        # Scenario 4: S12 adds CS201-A (ok), then IT201-A -> schedule conflict.
        enr12 = self._svc_enroll(report, S[12], main, [sec["CS201-A"]], confirm=False)
        self._expect_rejection(report, "S12 student schedule conflict (IT201-A vs CS201-A)",
                               lambda: enroll_in_section(enrollment=enr12, section=sec["IT201-A"]))
        if enr12.status == Enrollment.Status.DRAFT:
            confirm_enrollment(enrollment=enr12)
            report.record("update", f"Confirm Enrollment {S[12].student_number}")

        # Scenario 5: S13 draft with common courses, then CS101-B (full) -> capacity.
        enr13 = self._svc_enroll(report, S[13], main, [sec[c] for c in yr1_common], confirm=False)
        self._expect_rejection(report, "S13 full section (CS101-B capacity 2)",
                               lambda: enroll_in_section(enrollment=enr13, section=sec["CS101-B"]))
        if enr13.status == Enrollment.Status.DRAFT:
            if not EnrollmentDetail.objects.filter(enrollment=enr13, section=sec["CS101-A"]).exists():
                enroll_in_section(enrollment=enr13, section=sec["CS101-A"])
                report.record("create", f"EnrollmentDetail {S[13].student_number}/CS101-A")
            confirm_enrollment(enrollment=enr13)
            report.record("update", f"Confirm Enrollment {S[13].student_number}")
        else:
            report.record("skip", f"Enrollment {S[13].student_number} (already confirmed)")

        # Scenario 1/7: S14 valid confirmed enrollment (existing-enrollment subject).
        self._svc_enroll(report, S[14], main, [sec["CS101-A"]] + [sec[c] for c in yr1_common], confirm=True)
        # Scenario 7: second create in same term -> rejected (unique student+term).
        self._expect_rejection(report, "S14 existing enrollment same term",
                               lambda: create_enrollment(student=S[14], term=main))
        # Scenario 6: create enrollment in closed Sem 2 -> rejected (enrollment_open=False).
        self._expect_rejection(report, "S14 closed-term enrollment (AY2026-2027 Sem 2)",
                               lambda: create_enrollment(student=S[14], term=sem2))

        # Scenario 10: S15 inactive account -> create_enrollment rejected.
        self._expect_rejection(report, "S15 inactive student account",
                               lambda: create_enrollment(student=S[15], term=main))

        ctx["main"] = main

    # -- Stage 7: finance (versioned assessments, payments, scenarios) ------
    def _stage7_finance(self, report, ctx):
        self.stdout.write("Stage 7: finance (versioned assessments, payments, 12 scenarios)")
        main = ctx["main"]
        cashier = ctx["cashiers"][0]
        approver = ctx["admin"]
        S = ctx["students"]
        R = DEMO_RECEIPT_PREFIX

        def finalize_for(n):
            enr = Enrollment.objects.get(student=S[n], term=main, status=Enrollment.Status.CONFIRMED)
            a = create_draft_assessment(enrollment=enr, by=cashier)
            cv = a.current_version
            if cv is not None and cv.status == AssessmentVersion.Status.DRAFT:
                finalize_assessment(assessment=a, by=approver)
                a.refresh_from_db()
                report.record("create", f"Assessment finalized {S[n].student_number} (total {a.total_amount})")
            else:
                report.record("skip", f"Assessment {S[n].student_number}")
            return a

        def pay_once(a, receipt, amount, method, status=Payment.Status.RECEIVED):
            if Payment.objects.filter(receipt_number=receipt).exists():
                report.record("skip", f"Payment {receipt}")
                return None
            p = record_payment(assessment=a, received_by=cashier, receipt_number=receipt,
                               amount=Decimal(amount), method=method, status=status)
            report.record("create", f"Payment {receipt} {amount} {method} {status}")
            return p

        # Finalized assessments for every confirmed main-term enrollment (S01..S14).
        assess = {n: finalize_for(n) for n in range(1, 15)}
        ctx["assess"] = assess

        # 1 Unpaid (S01): finalized, no payment.
        # 2 Partially paid (S06). Guarded so a pre-existing legacy S06 (disposable DB) is preserved.
        if not assess[6].payments.exists():
            pay_once(assess[6], f"{R}0201", "3000.00", Payment.Method.CASH)
        # 3 Fully paid (S07): pay exactly the current balance.
        if not assess[7].payments.exists():
            bal7 = assessment_balance(assessment=assess[7])
            if bal7 > 0:
                pay_once(assess[7], f"{R}0202", str(bal7), Payment.Method.BANK_TRANSFER)
        # 4 Pending payment (S02): must not reduce balance.
        pay_once(assess[2], f"{R}0203", "2000.00", Payment.Method.CASH, status=Payment.Status.PENDING)
        # 5 Cancelled payment (S03): must not reduce balance.
        pay_once(assess[3], f"{R}0204", "1000.00", Payment.Method.CASH, status=Payment.Status.CANCELLED)
        # 6 Reversed payment with adjustment trail (S08).
        pay_once(assess[8], f"{R}0205", "2000.00", Payment.Method.E_WALLET)
        rev = Payment.objects.filter(receipt_number=f"{R}0205", status=Payment.Status.RECEIVED).first()
        if rev is not None:
            reverse_payment(payment=rev, by=approver, reason="DEMO payment reversal")
            report.record("update", f"Reverse payment {R}0205")
        # 7 Approved scholarship (S09).
        self._ensure_scholarship(report, S[9], assess[9], "DemoFund Foundation (DEMO)", "2000.00",
                                 cashier, approver, approve=True)
        # 8 Pending scholarship (S10).
        self._ensure_scholarship(report, S[10], assess[10], "DemoFund Pending Grant (DEMO)", "1500.00",
                                 cashier, approver, approve=False)
        # 9 Approved student credit (S04).
        self._ensure_credit(report, assess[4], "500.00", cashier, approver, approve=True)
        # 11 Overpayment retained as unallocated (S05).
        if not assess[5].payments.exists():
            bal5 = assessment_balance(assessment=assess[5])
            pay_once(assess[5], f"{R}0206", str(bal5 + Decimal("350.00")), Payment.Method.CASH)
        # 12 Revision with preserved old version + allocation (S13).
        self._ensure_revision(report, assess[13], f"{R}0207", cashier, approver)
        # 10 Outstanding previous-term balance (S12 historical; direct ORM, unpaid).
        self._ensure_prior_term_balance(report, ctx, S[12])

    def _ensure_scholarship(self, report, student, assessment, sponsor, amount, cashier, approver, *, approve):
        sch = ScholarshipAward.objects.filter(student=student, sponsor=sponsor).first()
        if sch is None:
            sch = create_scholarship(student=student, sponsor=sponsor, amount=Decimal(amount),
                                     by=cashier, assessment=assessment, is_demo=True)
            report.record("create", f"Scholarship {sponsor} {student.student_number}")
        else:
            report.record("skip", f"Scholarship {sponsor} {student.student_number}")
        if approve and sch.status == ScholarshipAward.Status.PENDING:
            approve_scholarship(scholarship=sch, by=approver)
            report.record("update", f"Approve scholarship {sponsor}")

    def _ensure_credit(self, report, assessment, amount, cashier, approver, *, approve):
        adj = Adjustment.objects.filter(
            assessment=assessment, adjustment_type=Adjustment.Type.CREDIT).first()
        if adj is None:
            adj = create_adjustment(adjustment_type=Adjustment.Type.CREDIT, amount=Decimal(amount),
                                    reason="DEMO goodwill credit", by=cashier,
                                    assessment=assessment, version=assessment.current_version)
            report.record("create", f"Credit {assessment.enrollment.student.student_number}")
        else:
            report.record("skip", f"Credit {assessment.enrollment.student.student_number}")
        if approve and adj.status == Adjustment.Status.PENDING:
            approve_adjustment(adjustment=adj, by=approver)
            report.record("update", "Approve credit")

    def _ensure_revision(self, report, assessment, receipt, cashier, approver):
        if assessment.versions.count() >= 2:
            report.record("skip", f"Revision {assessment.enrollment.student.student_number}")
            return
        if not Payment.objects.filter(receipt_number=receipt).exists():
            record_payment(assessment=assessment, received_by=cashier, receipt_number=receipt,
                           amount=Decimal("4000.00"), method=Payment.Method.CASH)
            report.record("create", f"Payment {receipt} 4000.00 CASH")
        revise_assessment(assessment=assessment, by=approver, reason="DEMO revision (fees re-reviewed)")
        finalize_assessment(assessment=assessment, by=approver)
        report.record("update", f"Revise+finalize {assessment.enrollment.student.student_number}")

    def _ensure_prior_term_balance(self, report, ctx, student):
        hist = ctx["terms"]["hist"]
        enr = Enrollment.objects.filter(student=student, term=hist).first()
        if enr is None:
            report.record("skip", f"Prior-term assessment {student.student_number} (no hist enrollment)")
            return
        if Assessment.objects.filter(enrollment=enr).exists():
            report.record("skip", f"Prior-term assessment {student.student_number}")
            return
        # Historical details are COMPLETED (not ENROLLED), so the fee service would
        # yield no lines; a legacy direct-ORM assessment with a DEMO total represents
        # an unpaid prior-term balance (policy = WARN, not BLOCK).
        Assessment.objects.create(
            enrollment=enr, total_amount=Decimal("8000.00"),
            status=Assessment.Status.FINALIZED,
            remarks=DEMO_ASSESSMENT_REMARK + " (prior-term, unpaid)")
        report.record("create", f"Prior-term assessment {student.student_number} (legacy, unpaid 8000)")

    # -- Stage 8: verification ----------------------------------------------
    def _stage8_verify(self, report, ctx):
        self.stdout.write("Stage 8: verification")
        assess = ctx["assess"]
        negatives = [a.enrollment.student.student_number for a in Assessment.objects.all()
                     if assessment_balance(assessment=a) < Decimal("0.00")]
        assert not negatives, f"Negative balances found: {negatives}"
        assert FeeRule.objects.filter(is_demo=True).count() >= 8, "demo fee rules missing"
        a13 = assess[13]
        assert a13.versions.count() >= 2, "S13 revision did not create a second version"
        a8 = assess[8]
        assert Payment.objects.filter(assessment=a8, status=Payment.Status.REVERSED).exists(), "S08 reversed payment missing"
        assert assessment_balance(assessment=a8) == a8.current_version.total_amount, "reversed payment must not reduce balance"
        report.record("skip", "Verify: no negative balances; >=8 fee rules; revision & reversal scenarios OK")
        report.record("skip", "Balances S01=%s S06=%s S07=%s" % (
            assessment_balance(assessment=assess[1]),
            assessment_balance(assessment=assess[6]),
            assessment_balance(assessment=assess[7])))
        counts = {
            "College": College.objects.count(), "Program": Program.objects.count(),
            "Course": Course.objects.count(), "AcademicTerm": AcademicTerm.objects.count(),
            "User": User.objects.count(), "Student": Student.objects.count(),
            "Instructor": Instructor.objects.count(), "Room": Room.objects.count(),
            "Section": Section.objects.count(), "Enrollment": Enrollment.objects.count(),
            "EnrollmentDetail": EnrollmentDetail.objects.count(),
            "FeeRule": FeeRule.objects.count(), "Assessment": Assessment.objects.count(),
            "AssessmentVersion": AssessmentVersion.objects.count(),
            "Payment": Payment.objects.count(),
            "PaymentAllocation": PaymentAllocation.objects.count(),
            "Adjustment": Adjustment.objects.count(),
            "ScholarshipAward": ScholarshipAward.objects.count(),
        }
        ctx["counts"] = counts
        report.record("skip", "In-transaction counts: " + ", ".join(f"{k}={v}" for k, v in counts.items()))

    # -- generic idempotent upsert -----------------------------------------
    def _ensure(self, report, model, lookup, create, updatable=None, immutable=None, label=None):
        updatable = updatable or {}
        immutable = immutable or {}
        label = label or model.__name__
        obj = model.objects.filter(**lookup).first()
        if obj is None:
            obj = model(**lookup, **create)
            obj.save()
            report.record("create", label)
            return obj
        conflicts = {f: (getattr(obj, f), v) for f, v in immutable.items() if getattr(obj, f) != v}
        if conflicts:
            raise SeedConflict(
                f"{label}: existing record conflicts with blueprint on {conflicts}. "
                f"Refusing to overwrite a natural-key match; resolve manually.")
        changed = [f for f, v in updatable.items() if getattr(obj, f) != v]
        if changed:
            for f in changed:
                setattr(obj, f, updatable[f])
            obj.save(update_fields=changed)
            report.record("update", label, f"fields: {', '.join(changed)}")
        else:
            report.record("skip", label)
        return obj

    def _ensure_user(self, report, username, *, role, first, last, is_active=True):
        """Create-only identity. Never resets an existing password or role."""
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create_user(
                username=username, email=f"{username.replace('.', '_')}@example.com",
                password=DEMO_PASSWORD, first_name=first, last_name=last,
                role=role, is_active=is_active)
            report.record("create", f"User {username} ({role})")
        else:
            report.record("skip", f"User {username} (exists; password/role untouched)")
        return user

    def _ensure_room(self, report, room_code):
        """Reuse or create a normalized Room from a free-text code. Blank -> None."""
        code = (room_code or "").strip()
        if not code:
            return None
        room = Room.objects.filter(room_code=code).first()
        if room is None:
            room = Room.objects.create(room_code=code, name=code, is_active=True)
            report.record("create", f"Room {code}")
        return room

    def _ensure_section(self, report, code, course, term, instructor, day, start, end, room, cap, status):
        existing = Section.objects.filter(course=course, term=term, section_code=code).first()
        if existing is not None:
            has_details = EnrollmentDetail.objects.filter(section=existing).exists()
            wants = (existing.capacity != cap or existing.room_code != (room or "")
                     or existing.day_of_week != (int(day) if day is not None else None)
                     or existing.start_time != start or existing.end_time != end
                     or existing.status != status)
            if wants and has_details:
                raise SeedConflict(
                    f"Section {code}: cannot change a section that already has enrollment "
                    f"details. Resolve manually.")
            # Defensive: link a Room if a legacy section still lacks one.
            if existing.room_id is None and (room or "").strip():
                existing.room = self._ensure_room(report, room)
                existing.save(update_fields=["room"])
                report.record("update", f"Section {code} (room linked)")
            else:
                report.record("skip" if not wants else "update", f"Section {code}")
            return existing
        room_obj = self._ensure_room(report, room)
        section = create_section(
            course=course, term=term, section_code=code, capacity=cap,
            instructor=instructor, room=room_obj, room_code=(room or ""),
            day_of_week=(int(day) if day is not None else None),
            start_time=start, end_time=end, status=status)
        report.record("create", f"Section {code}")
        return section

    def _svc_enroll(self, report, student, term, sections, *, confirm):
        enr = Enrollment.objects.filter(student=student, term=term).first()
        if enr is None:
            enr = create_enrollment(student=student, term=term)
            report.record("create", f"Enrollment {student.student_number}")
        else:
            report.record("skip", f"Enrollment {student.student_number}")
        for section in sections:
            if not EnrollmentDetail.objects.filter(enrollment=enr, section=section).exists():
                enroll_in_section(enrollment=enr, section=section)
                report.record("create", f"EnrollmentDetail {student.student_number}/{section.section_code}")
            else:
                report.record("skip", f"EnrollmentDetail {student.student_number}/{section.section_code}")
        if confirm and enr.status == Enrollment.Status.DRAFT:
            confirm_enrollment(enrollment=enr)
            report.record("update", f"Confirm Enrollment {student.student_number}")
        return enr

    def _expect_rejection(self, report, label, fn):
        try:
            fn()
        except ValidationError as exc:
            report.rejection_ok(label, "; ".join(exc.messages))
        else:
            report.rejection_missing(label)

    # -- teardown (preview unless --confirm) --------------------------------
    def _teardown(self, *, confirm):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"seed_demo teardown: {'EXECUTE' if confirm else 'PREVIEW (use --confirm to delete)'}"))
        demo_users = User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
        demo_students = Student.objects.filter(student_number__startswith=DEMO_STUDENT_PREFIX)
        demo_enrollments = Enrollment.objects.filter(student__in=demo_students)
        demo_room_codes = (
            {s[7] for s in MAIN_SECTIONS if s[7]} | {h[6] for h in HIST_SECTIONS if h[6]}
        )
        # Reverse-dependency order (children before parents; all FKs are PROTECT
        # except Assessment.current_version/FinanceAuditLog.actor which SET_NULL).
        plan = [
            ("PaymentAllocation", PaymentAllocation.objects.filter(
                version__assessment__enrollment__in=demo_enrollments)),
            ("Adjustment", Adjustment.objects.filter(assessment__enrollment__in=demo_enrollments)),
            ("ScholarshipAward", ScholarshipAward.objects.filter(student__in=demo_students)),
            ("Payment", Payment.objects.filter(receipt_number__startswith=DEMO_RECEIPT_PREFIX)),
            ("AssessmentLine", AssessmentLine.objects.filter(
                version__assessment__enrollment__in=demo_enrollments)),
            ("FeeRule", FeeRule.objects.filter(is_demo=True)),
            ("AssessmentVersion", AssessmentVersion.objects.filter(
                assessment__enrollment__in=demo_enrollments)),
            ("Assessment", Assessment.objects.filter(enrollment__in=demo_enrollments)),
            ("EnrollmentDetail", EnrollmentDetail.objects.filter(enrollment__in=demo_enrollments)),
            ("Enrollment", demo_enrollments),
            ("Section", Section.objects.filter(course__course_code__startswith="SIM-")),
            ("Room", Room.objects.filter(room_code__in=demo_room_codes)),
            ("Student", demo_students),
            ("Instructor", Instructor.objects.filter(employee_number__startswith="EMP-I-")),
            ("User(demo)", demo_users),
            ("CurriculumCourse", CurriculumCourse.objects.filter(curriculum__curriculum_code=DEMO_CURRICULUM_CODE)),
            ("CoursePrerequisite", CoursePrerequisite.objects.filter(course__course_code__startswith="SIM-")),
            ("Curriculum", Curriculum.objects.filter(curriculum_code=DEMO_CURRICULUM_CODE)),
            ("Course", Course.objects.filter(course_code__startswith="SIM-")),
            ("Program", Program.objects.filter(program_code__in=[p[1] for p in PROGRAMS])),
            ("College", College.objects.filter(college_code__in=[c[0] for c in COLLEGES])),
            ("AcademicTerm", AcademicTerm.objects.filter(
                academic_year__in=[HIST_YEAR, MAIN_YEAR, SEM2_YEAR])),
        ]
        # Safety: never touch the Administrator / superusers / non-demo accounts.
        for label, qs in plan:
            self.stdout.write(f"  {label}: {qs.count()} demo row(s)")
        if not confirm:
            self.stdout.write(self.style.WARNING("Preview only. No rows deleted. Re-run with --confirm to delete."))
            return
        with transaction.atomic():
            for label, qs in plan:
                deleted, _ = qs.delete()
                self.stdout.write(f"  deleted {label}: {deleted}")
        self.stdout.write(self.style.SUCCESS("Teardown complete (Administrator and non-demo data preserved)."))

    def _print_report(self, report):
        self.stdout.write(self.style.MIGRATE_HEADING("Action report"))
        for line in report.lines:
            self.stdout.write(line)
        for line in report.rejections_ok:
            self.stdout.write(self.style.SUCCESS(line))
        for line in report.rejections_missing:
            self.stdout.write(self.style.ERROR(line))
        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        self.stdout.write(
            f"  creates={report.actions['create']} updates={report.actions['update']} "
            f"skips={report.actions['skip']} "
            f"expected-rejections-ok={len(report.rejections_ok)} "
            f"rejections-missing={len(report.rejections_missing)}")
