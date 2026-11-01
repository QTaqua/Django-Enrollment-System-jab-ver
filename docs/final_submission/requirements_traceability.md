# E1 — Requirements Traceability Matrix

Maps each instructor requirement to the implementing code and its verification.
Status: **Impl** = Implemented · **Part** = Partial · **No** = Not Implemented.
Paths are relative to the project root. See `functional_requirements.md` for
full descriptions.

| ID | Requirement | Primary code (view / service / model) | URL name | Evidence (tests / method) | Status |
|---|---|---|---|---|---|
| FR-A1 | Student registration (personal/academic/contact) | `accounts/people_views.py` StudentCreateView; `accounts/services.py` create_student_account; `accounts.User`, `academics.Student` | `people:student_create` | `accounts/tests.py`; HTTP 200 | Impl |
| FR-A2 | Unique student ID | `academics.Student` (uq_student_student_number) | — | model constraint; dup-rejection test | Part |
| FR-A3 | Retrieve/update student records | people_views List/Detail/UpdateView; update_student_profile | `people:student_list/detail/update` | account tests | Impl |
| FR-B1 | Course creation/management | `academics/views.py` Course*View; `academics.Course` | `academics:course_create/update` | academics tests | Part (no delete UI) |
| FR-B2 | Program & year-level relationships | `academics.Program`, `academics.CurriculumCourse` | `academics:program_*` | academics tests | Impl |
| FR-B3 | Curriculum management | `academics/views.py` Curriculum*View | `academics:curriculum_*` | academics tests | Impl |
| FR-B4 | Prerequisites | `academics.CoursePrerequisite`; enforced in `enroll_in_section` | `academics:course_prerequisite_*` | prerequisite tests | Impl |
| FR-C1 | Course selection by curriculum | `enrollment/services.py` enroll_in_section | `enrollment:enrollment_add_section` | enrollment tests | Impl |
| FR-C2 | Prerequisite validation | `enrollment/services.py` missing_prerequisites | — | prerequisite tests; seed S11 | Impl |
| FR-C3 | Schedule-conflict validation | enroll_in_section; `scheduling/services.py` instructor+room checks | section/enroll views | scheduling + room + enrollment tests | Impl |
| FR-C4 | Enrollment records (course/section/semester) | `enrollment.Enrollment`, `EnrollmentDetail`; confirm_enrollment | `enrollment:enrollment_*` | confirmation tests | Impl |
| FR-D1 | Automatic fee calculation | `finance/services.py` compute_fee_breakdown; `FeeRule` | (auto on confirm) | finance fee tests | Impl |
| FR-D2 | Detailed assessment breakdown | `finance/views.py` AssessmentDetailView; `AssessmentLine` | `finance:assessment_detail` | finance tests; HTTP 200 | Impl |
| FR-D3 | Payment recording | `finance/views.py` RecordPaymentView; record_payment | `finance:record_payment` | finance payment tests; HTTP 200 | Impl |
| FR-D4 | Balance calculation/updates | `finance/services.py` assessment_balance | (all finance pages) | finance balance tests; seed balances | Impl |
| FR-E1 | Day/time/room/instructor | `scheduling.Section`, `scheduling.Room` | `scheduling:section_*` | scheduling tests | Impl |
| FR-E2 | Classroom conflict prevention | `scheduling/services.py` _room_has_conflict | section create/update | `scheduling/tests_room.py` | Impl |
| FR-E3 | Instructor conflict prevention | `scheduling/services.py` _instructor_has_conflict | section create/update | scheduling tests | Impl |
| FR-E4 | Available class sections | `enrollment/forms.py` AddSectionForm | `enrollment:enrollment_add_section` | enrollment tests | Impl |
| FR-F1 | Enrolled by course/year | `accounts/report_views.py` enrolled_report | `reports:enrolled` | `accounts/tests_reports.py` | Impl |
| FR-F2 | Total enrollment per semester | report_views semester_report | `reports:semester` | reports tests | Impl |
| FR-F3 | Collection report | report_views collection_report | `reports:collection` | reports tests | Impl |
| FR-F4 | PDF or Excel export | report_views CSV + print-friendly HTML | `reports:*?format=csv` | reports CSV tests | Impl (CSV + browser PDF) |
| FR-G1..5 | Five roles | `accounts.User.Role`; dashboards | `*_dashboard` | role tests | Impl |
| FR-G6 | Unique credentials + role permissions | `accounts/permissions.py` mixins/decorators | all protected views | permission matrix tests; HTTP | Impl |

## Summary

- **Implemented:** FR-A1, FR-A3, FR-B2, FR-B3, FR-B4, FR-C1–C4, FR-D1–D4,
  FR-E1–E4, FR-F1–F4, FR-G1–G6.
- **Partial:** FR-A2 (manual student ID), FR-B1 (no delete UI).
- **Not Implemented:** none of the base A–G requirements (two are Partial).

All statuses are verified against the codebase and the 248-test suite; see
`functional_requirements.md` for per-requirement evidence and limitations.
