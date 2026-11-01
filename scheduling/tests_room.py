"""Milestone A tests: Room model, room-code backfill migration, and classroom
double-booking prevention. Existing instructor/student conflict checks are
exercised for regression."""

import importlib
from datetime import time

from django.apps import apps as global_apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from academics.models import AcademicTerm, Course, Instructor
from scheduling.models import Room, Section
from scheduling.services import create_section, update_section
from scheduling.tests import SchedulingTestBase

MON, TUE = 0, 1


class RoomModelTests(TestCase):
    def test_room_code_is_unique(self):
        Room.objects.create(room_code="R-A", name="Room A")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(room_code="R-A", name="Duplicate")

    def test_capacity_must_be_positive_or_null(self):
        Room.objects.create(room_code="R-NULLCAP", name="No cap")  # null ok
        Room.objects.create(room_code="R-POS", name="Pos", capacity=30)  # ok
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(room_code="R-ZERO", name="Zero", capacity=0)


class RoomBackfillMigrationTests(TestCase):
    """Exercise the actual 0003 data-migration functions."""

    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(
            course_code="MIG101", title="Migration Course", units=3
        )
        cls.term = AcademicTerm.objects.create(
            academic_year="2030-2031",
            semester_number=1,
            start_date="2030-08-01",
            end_date="2030-12-15",
        )

    def _section(self, code, room_code):
        return Section.objects.create(
            course=self.course, term=self.term, section_code=code,
            capacity=30, room_code=room_code,
        )

    def test_forward_dedups_and_leaves_blank_null_then_reverse(self):
        migration = importlib.import_module(
            "scheduling.migrations.0003_backfill_room_from_room_code"
        )
        s1 = self._section("A", "LAB-A")
        s2 = self._section("B", "LAB-A")   # duplicate code -> same Room
        s3 = self._section("C", "")         # blank/TBA -> stays NULL
        s4 = self._section("D", "MAIN-101")

        migration.backfill_rooms(global_apps, None)
        for s in (s1, s2, s3, s4):
            s.refresh_from_db()

        self.assertEqual(Room.objects.filter(room_code="LAB-A").count(), 1)
        self.assertIsNotNone(s1.room_id)
        self.assertEqual(s1.room.room_code, "LAB-A")
        self.assertEqual(s2.room_id, s1.room_id)      # dedup
        self.assertIsNone(s3.room_id)                 # blank stays NULL
        self.assertEqual(s4.room.room_code, "MAIN-101")
        # room_code values preserved, not discarded
        self.assertEqual(s1.room_code, "LAB-A")
        self.assertEqual(s3.room_code, "")
        # migrated room name is the code (no invented details)
        self.assertEqual(s1.room.name, "LAB-A")

        migration.unbackfill_rooms(global_apps, None)
        for s in (s1, s2, s3, s4):
            s.refresh_from_db()
        self.assertIsNone(s1.room_id)
        self.assertIsNone(s4.room_id)
        self.assertEqual(Room.objects.count(), 0)


class RoomConflictServiceTests(SchedulingTestBase):
    def setUp(self):
        self.room_a = Room.objects.create(room_code="RM-A", name="Room A")
        self.room_b = Room.objects.create(room_code="RM-B", name="Room B")

    def _make(self, code, *, room, term=None, day=MON, start=time(8, 0),
              end=time(9, 30), instructor=None, status=Section.Status.OPEN):
        return create_section(
            course=self.course1, term=term or self.term1, section_code=code,
            capacity=30, instructor=instructor, room=room, room_code="",
            day_of_week=day, start_time=start, end_time=end, status=status,
        )

    def test_same_room_overlapping_time_rejected(self):
        self._make("A", room=self.room_a)
        with self.assertRaises(ValidationError) as ctx:
            self._make("B", room=self.room_a, start=time(9, 0), end=time(10, 30))
        self.assertIn("room is already booked", " ".join(ctx.exception.messages))

    def test_same_room_adjacent_slot_allowed(self):
        self._make("A", room=self.room_a, start=time(8, 0), end=time(9, 30))
        # ends exactly when the next begins -> allowed
        self._make("B", room=self.room_a, start=time(9, 30), end=time(11, 0))

    def test_same_room_different_day_allowed(self):
        self._make("A", room=self.room_a, day=MON)
        self._make("B", room=self.room_a, day=TUE)

    def test_different_rooms_same_slot_allowed(self):
        self._make("A", room=self.room_a)
        self._make("B", room=self.room_b)

    def test_different_term_same_room_slot_allowed(self):
        self._make("A", room=self.room_a, term=self.term1)
        self._make("B", room=self.room_a, term=self.term2)

    def test_cancelled_section_does_not_block_room(self):
        self._make("A", room=self.room_a, status=Section.Status.CANCELLED)
        # a cancelled section must not occupy the room
        self._make("B", room=self.room_a)

    def test_tba_room_never_conflicts(self):
        self._make("A", room=None)
        self._make("B", room=None)  # no room -> no room conflict

    def test_update_does_not_conflict_with_itself(self):
        section = self._make("A", room=self.room_a)
        # re-saving the same schedule/room must not trip the conflict check
        update_section(section, capacity=40, room=self.room_a)
        section.refresh_from_db()
        self.assertEqual(section.capacity, 40)
        self.assertEqual(section.room_id, self.room_a.id)

    def test_update_into_occupied_room_rejected(self):
        self._make("A", room=self.room_a, start=time(8, 0), end=time(9, 30))
        other = self._make("B", room=self.room_b, start=time(8, 0), end=time(9, 30))
        with self.assertRaises(ValidationError):
            update_section(other, room=self.room_a)

    def test_instructor_conflict_still_enforced(self):
        # fresh instructor + isolated slot so base fixtures don't interfere
        user = User.objects.create_user(
            username="rm_instr", password="pass12345", role=User.Role.INSTRUCTOR
        )
        instr = Instructor.objects.create(user=user, employee_number="RM-EMP-9")
        self._make("INS1", room=self.room_a, instructor=instr,
                   start=time(16, 0), end=time(17, 30))
        # different room, same instructor + slot -> still rejected
        with self.assertRaises(ValidationError) as ctx:
            self._make("INS2", room=self.room_b, instructor=instr,
                       start=time(16, 0), end=time(17, 30))
        self.assertIn("instructor", " ".join(ctx.exception.messages).lower())
