# ADS Enrollment System

A college enrollment management system built with Django and MySQL. The
simplified design uses 15 business tables and a single weekly meeting per course
section. It provides authentication and role-based dashboards, academic master
data, student and instructor profiles, section management, enrollment creation
and confirmation, a read-only student enrollment portal, and a small finance data
layer.

This repository contains the simplified ADS implementation. The original,
larger data model has been replaced, but the repository's Git history is
preserved.

## Technology stack

| Component | Version |
| --- | --- |
| Python | 3.13.7 |
| Django | 5.2.18 |
| MySQL Server | 9.5.0 |
| mysqlclient | 2.3.0 |
| asgiref | 3.13.0 |
| sqlparse | 0.6.0 |
| tzdata | 2026.5 |

Django 5.2 requires Python 3.10 or newer. The versions above are the verified
development environment.

## Roles

The custom user model is `accounts.User` (table `app_user`). Authentication uses
Django's normal username/password flow, and a coarse `role` field drives
authorization.

| Role | Current access |
| --- | --- |
| Administrator | Read-only access to academic master data, people, sections, and enrollments in the web application. Staff administrators can also use the custom Django admin site; some admin models are read-only. |
| Registrar | Creates and updates academic master data, student and instructor accounts, sections, and enrollments. Creates DRAFT enrollments, adds/removes sections, and confirms enrollments. |
| Cashier | Role dashboard only. Finance services exist, but no cashier/payment screens are implemented yet. |
| Student | Dashboard and read-only access to their own enrollment records. Students cannot view another student's enrollment by changing a URL. |
| Instructor | Role dashboard only. No instructor section or grading screens are implemented yet. |

Administrators are read-only on the Registrar screens, including section and
enrollment write endpoints. Cashier and Instructor accounts cannot use Registrar
screens.

## Implemented features

### Authentication and dashboards

- Role-aware login redirects each user to the correct dashboard.
- Inactive accounts are denied access; anonymous users are redirected to login.
- Shared Bootstrap-based layout and navigation.
- The custom admin site at `/admin/` is restricted to staff users with the
  Administrator role.

### Academic master data

Registrar-managed list, detail, create, and update screens for:

- Colleges
- Programs
- Curricula
- Courses
- Curriculum course placements
- Course prerequisites
- Academic terms

Academic terms carry their dates and an `enrollment_open` flag. Administrators
can view these records but cannot modify them from the web screens.

### Student and instructor profiles

Registrar-managed account creation and profile updates for students and
instructors. Student profiles include a student number, curriculum, and year
level. Instructor profiles include an employee number. Personal names and
contact details live on the shared user record.

### Section management

Sections are offered per course and academic term, with:

- Section code, capacity, room code, day of week, start time, and end time.
- Optional instructor assignment.
- OPEN, CLOSED, and CANCELLED statuses.
- TBA schedules (day, start, and end all blank) and complete schedules.
- Validation that partial schedules are rejected and end time is later than
  start time.
- Instructor overlap prevention for the same term and day/time.
- Protection against reducing capacity below the number of actively enrolled
  students.
- Protection against cancelling a section that has active enrolled students.
- Protection against course or term changes once enrollment records exist.
- Protection against schedule changes that would conflict with already enrolled
  students' other sections.

TBA sections and sections without an OPEN status cannot receive new enrollment.
CLOSED sections do not accept new enrollment, but existing enrollment records
remain valid. There is no separate room entity and no room-conflict validation.

### Enrollment workflow

Registrar-managed enrollment records:

- One enrollment per student per academic term.
- New enrollments start as DRAFT and require an open enrollment period.
- A DRAFT enrollment may still be confirmed after the enrollment period closes.
- Sections can be added only to a DRAFT enrollment in its own academic term.
- A section must be OPEN, have a complete schedule, have available capacity, and
  not already be part of the enrollment.
- The course must be in the student's curriculum.
- Duplicate sections of the same course are rejected within one enrollment.
- Prerequisites must be satisfied by a prior-term detail that is both
  `COMPLETED` and `PASSED`; numeric grades never imply a pass.
- Overlapping sections for the same student, term, and day are rejected.
- Removing a section marks its detail as `DROPPED` with a recorded result status
  and timestamp; the detail is preserved, not deleted.
- Confirmation requires at least one active ENROLLED detail and revalidates the
  section term, schedule completeness, capacity, and cancellation status.
- Enrollment cancellation is intentionally not exposed because the unique
  student/term constraint includes cancelled records.

Students can view their own enrollment list and details at `/my-enrollments/`.
The student portal is read-only.

### Finance data layer

The finance app currently provides the data model and service helpers only:

- One `Assessment` per enrollment, with a derived balance.
- `Payment` records with receipt numbers, methods, and statuses.
- `record_payment()` records a positive payment against an assessment.
- `assessment_balance()` derives the balance from the assessment total minus
  received payments.

There are no finance screens in this phase. Do not assume a cashier or payment
UI exists.

## Project structure

```text
.
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── config/                  # Django project package and URL routing
├── accounts/                # custom user, roles, authentication, dashboards, people
├── academics/               # colleges, programs, curricula, courses, terms
├── scheduling/              # sections and section rules
├── enrollment/              # enrollments, details, prerequisites, student portal
├── finance/                 # assessments, payments, and finance service helpers
├── templates/               # shared Bootstrap UI and role dashboards
└── erd_artifacts/           # simplified schema and ERD reference artifacts
```

## Data model

The 15 business tables are:

```text
app_user
college
program
curriculum
course
curriculum_course
course_prerequisite
academic_term
student
instructor
section
enrollment
enrollment_detail
assessment
payment
```

Django also creates its normal framework tables for authentication, permissions,
sessions, content types, admin logs, and migrations.

Key simplifications:

- No `Room` table: `section.room_code` is a free-text label.
- No `SectionMeeting` table: each section has one weekly day/start/end schedule.
- No separate `StudentCourseResult` table: final grade and result status live on
  `enrollment_detail`.
- All application primary keys use integer `AutoField`.
- Foreign keys use `on_delete=PROTECT` for historical records.
- Row-level rules use database constraints; cross-row rules live in service
  modules.

## Prerequisites

- Python 3.13 (3.10+ should work; 3.13.7 is verified)
- MySQL Server 8.0+ (9.5.0 verified)
- A MySQL database and user you can use
- A C compiler and Python headers if `mysqlclient` must be built from source
  (on Windows, Visual C++ Build Tools are typically required)
- Git

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If PowerShell blocks the activation script for this session:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Create the MySQL database

```sql
CREATE DATABASE ads_enrollment_simplified
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Create or choose a MySQL user that can use this database. Do not commit database
credentials.

### 3. Configure the environment

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your own values. `.env` is git-ignored and must never be
committed.

| Variable | Purpose | Example |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key | `replace-with-a-long-random-value` |
| `DJANGO_DEBUG` | Debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DB_NAME` | Database name | `ads_enrollment_simplified` |
| `DB_USER` | Database user | `root` |
| `DB_PASSWORD` | Database password | (your password) |
| `DB_HOST` | Database host | `localhost` |
| `DB_PORT` | Database port | `3306` |

Real environment variables take precedence over values in `.env`.

### 4. Apply migrations

```powershell
python manage.py migrate
```

### 5. Create an administrator

```powershell
python manage.py createsuperuser
```

New users default to the Student role, and the custom admin site requires the
Administrator role. Promote the account before using `/admin/`:

```powershell
python manage.py shell -c "from accounts.models import User; u = User.objects.get(username='YOUR_USERNAME'); u.role = User.Role.ADMINISTRATOR; u.save(update_fields=['role'])"
```

Alternatively, create the account directly:

```powershell
python manage.py shell -c "from accounts.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'change-me', role=User.Role.ADMINISTRATOR)"
```

Do not keep a development password in source control.

### 6. Run the development server

```powershell
python manage.py runserver
```

The application is available at <http://127.0.0.1:8000/>. The custom admin site
is at <http://127.0.0.1:8000/admin/>.

Main routes:

| Route | Purpose |
| --- | --- |
| `/login/` | Login |
| `/dashboard/` | Role-aware dashboard redirect |
| `/academics/` | Academic master data |
| `/people/` | Student and instructor profiles |
| `/sections/` | Section management |
| `/enrollments/` | Registrar enrollment management |
| `/my-enrollments/` | Student's own enrollments |
| `/admin/` | Administrator-only Django admin |

## Testing

Run the full suite:

```powershell
python manage.py test --noinput
```

The test runner creates and destroys the dedicated test database
`test_ads_enrollment_simplified`. The application database is not used for tests.

Useful checks:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py showmigrations
```

The current suite contains 196 tests covering authentication, roles, academic
master data, people, sections, enrollment rules, prerequisites, confirmation,
removal, ownership, and Phase 6B/6C regressions.

## Migrations and schema

Django migrations are the source of truth for the schema. The repository already
contains the initial migrations for all five applications.

- Do not create schema changes by editing the database manually.
- Run `makemigrations` only after an intentional model change.
- Run `migrate` to apply pending migrations.

## ERD artifacts

The files under `erd_artifacts/` are design and documentation artifacts only:

- `ADS_Enrollment_System_Simplified_Schema.sql` — schema-only SQL script for
  MySQL Workbench/ERD tooling.
- `ADS_Enrollment_System_Simplified.mwb` — MySQL Workbench EER model.
- `ADS_Enrollment_System_Simplified_ERD.png` — exported ERD image.

Do not execute the SQL script as a substitute for Django migrations. It does not
record migration state. Use `python manage.py migrate` for a fresh database.

## Current limitations

- MySQL is required by settings; there is no SQLite fallback.
- Finance has models and service helpers but no cashier or payment screens.
- There is no grade-entry/finalization UI. Result fields exist on
  `enrollment_detail`, but current screens do not record final grades.
- Instructors have no section-management or grading screens yet.
- There is no waitlist, enrollment cancellation UI, or self-service student
  add/drop.
- There is no separate room entity, so room-conflict detection is not possible.
- Each section supports one weekly meeting only.
- Cross-row rules are enforced by service functions, not database triggers.
  Direct ORM writes can bypass prerequisite, capacity, and schedule checks.
- Development defaults exist: `DEBUG` defaults to `True`, and an insecure secret
  key fallback is used when `DJANGO_SECRET_KEY` is unset. Override both outside
  development.
- No license has been declared. Add one before distributing the project or
  accepting external contributions.
