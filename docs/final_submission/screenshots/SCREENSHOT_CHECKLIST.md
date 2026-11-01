# E4 — Screenshot Capture Checklist

**No screenshots are fabricated.** GUI browser capture was unavailable in the
development environment (the Chrome automation extension could not reach
`localhost`). This is a **capture checklist** for the reviewer to produce genuine
screenshots after running the app. Save each image into this `screenshots/`
folder using the suggested filename; a matching `*.PLACEHOLDER` note is listed so
missing captures are obvious.

## Setup

1. Activate the venv and run the seeded disposable DB:
   `python manage.py runserver` → open `http://127.0.0.1:8000/`.
2. Ensure the DEMO data is seeded: `python manage.py seed_demo --commit`
   (idempotent). Use the **demo accounts** (usernames `demo.*`). The demo
   password is the `DEMO_PASSWORD` constant in
   `accounts/management/commands/seed_demo.py` — **do not paste it into
   screenshots or documents.** The real Administrator (`nicholohq`) is used only
   for Django `/admin/`.
3. Capture at a consistent window width (e.g., 1280px) with the HTU branding
   visible.

Login routes: `/login/`; dashboards at `/dashboard/`. Finance at `/finance/`;
reports at `/reports/`; Django admin at `/admin/`.

## Checklist

| # | Filename | Page / URL | Role (demo user) | Demonstrates | Required data/setup |
|---|---|---|---|---|---|
| 1 | `01_login.png` | `/login/` | (none) | Branded login page | — |
| 2 | `02_dashboard_registrar.png` | `/dashboard/registrar/` | demo.registrar1 | Registrar dashboard + nav | logged in |
| 3 | `03_dashboard_cashier.png` | `/dashboard/cashier/` | demo.cashier1 | Cashier dashboard with finance links | — |
| 4 | `04_dashboard_student.png` | `/dashboard/student/` | demo.stud01 | Student dashboard | — |
| 5 | `05_student_registration.png` | `/people/students/add/` | demo.registrar1 | Student registration form (FR-A1) | — |
| 6 | `06_student_list.png` | `/people/students/` | demo.registrar1 | Student records list (FR-A3) | — |
| 7 | `07_course_list.png` | `/academics/courses/` | demo.registrar1 | Course management (FR-B1) | — |
| 8 | `08_curriculum_courses.png` | `/academics/curriculum-courses/` | demo.registrar1 | Curriculum/course + year level (FR-B2/B3) | — |
| 9 | `09_prerequisites.png` | `/academics/course-prerequisites/` | demo.registrar1 | Prerequisites (FR-B4) | — |
| 10 | `10_section_list.png` | `/sections/` | demo.registrar1 | Sections with room/instructor (FR-E1) | — |
| 11 | `11_section_form.png` | `/sections/add/` | demo.registrar1 | Section form incl. Room select (FR-E1/E2) | — |
| 12 | `12_section_conflict.png` | `/sections/add/` | demo.registrar1 | Room/instructor conflict error (FR-E2/E3) | submit an overlapping room/time |
| 13 | `13_enrollment_detail.png` | `/enrollments/<id>/` | demo.registrar1 | Enrollment with sections (FR-C4) | open a confirmed enrollment |
| 14 | `14_enrollment_reject.png` | `/enrollments/<id>/add/` | demo.registrar1 | Validation error (prereq/capacity/conflict) (FR-C2/C3) | reproduce a seed negative scenario |
| 15 | `15_assessment_detail.png` | `/finance/assessment/<id>/` | demo.cashier1 | Itemized assessment + balance (FR-D1/D2/D4) | a finalized assessment (e.g., S01) |
| 16 | `16_record_payment.png` | `/finance/assessment/<id>/pay/` | demo.cashier1 | Payment form (FR-D3) | finalized assessment |
| 17 | `17_receipt.png` | `/finance/payment/<id>/receipt/` | demo.cashier1 | Printable receipt | after recording a payment |
| 18 | `18_approvals.png` | `/finance/approvals/` | demo.admin1 | Adjustment/scholarship approvals | pending items from seed |
| 19 | `19_report_enrolled.png` | `/reports/enrolled/` | demo.registrar1 | Enrolled-by-course/year report (FR-F1) | — |
| 20 | `20_report_semester.png` | `/reports/semester/` | demo.registrar1 | Per-semester totals (FR-F2) | — |
| 21 | `21_report_collection.png` | `/reports/collection/` | demo.cashier1 | Collection report (FR-F3) | — |
| 22 | `22_report_csv.png` | `/reports/collection/?format=csv` | demo.cashier1 | CSV opened in a spreadsheet (FR-F4) | open the downloaded file |
| 23 | `23_report_print.png` | `/reports/enrolled/` (Print dialog) | demo.registrar1 | Browser "Save as PDF" of a report (FR-F4) | use the Print button |
| 24 | `24_admin_fee_rules.png` | `/admin/` → Fee rules | nicholohq (superuser) | DEMO fee-rule management (FR-D1) | Django admin |
| 25 | `25_access_denied_403.png` | `/finance/` as a student | demo.stud01 | Server-side authorization (403) (FR-G6) | attempt a restricted URL |

## Placeholders

Until captured, create empty marker files or leave this note so gaps are clear.
Do **not** substitute unrelated images. Suggested placeholders:

- `01_login.PLACEHOLDER` … `25_access_denied_403.PLACEHOLDER`

The reviewer should replace each `.PLACEHOLDER` with the corresponding `.png`
after capturing it from the running application.
