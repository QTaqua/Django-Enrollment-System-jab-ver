# E5 — Live Demonstration Script (complete cycle)

Uses the seeded **fictional DEMO data**. Log in with the `demo.*` accounts; the
password is the `DEMO_PASSWORD` constant in the seed command — **do not display
it on screen**. Start the server (`python manage.py runserver`) with the seeded
disposable DB. Routes: `/login/`, `/dashboard/`, `/sections/`, `/enrollments/`,
`/finance/`, `/reports/`, `/admin/`.

Tip: before presenting, you may re-run `python manage.py seed_demo --commit`
(idempotent) to ensure the scenarios exist.

---

## Part A — Enrollment cycle (Registrar)

| Step | Account | Page | Action | Expected result | Explain |
|---|---|---|---|---|---|
| A1 | demo.registrar1 | `/login/` → dashboard | Log in | Registrar dashboard with nav (Academics, Sections, Enrollments, People, Finance, Reports) | Role-aware routing |
| A2 | demo.registrar1 | `/academics/courses/` | Browse courses/curriculum | SIM-BSIT courses listed | Catalog is the basis for enrollment |
| A3 | demo.registrar1 | `/sections/add/` | Create a section, pick a Room + time that **overlaps** an existing one | Validation error: room/instructor already booked | Milestone A room + instructor conflict checks |
| A4 | demo.registrar1 | `/sections/add/` | Fix the time/room, save | Section created with a Room | Normalized Room entity |
| A5 | demo.registrar1 | `/enrollments/add/` | Create a draft enrollment for a student in the open term | Draft enrollment created | One enrollment per student/term |
| A6 | demo.registrar1 | `/enrollments/<id>/add/` | Add a section whose **prerequisite is unmet** (e.g., S11 → CS201) | Rejected: prerequisite not completed | FR-C2 prerequisite validation |
| A7 | demo.registrar1 | `/enrollments/<id>/add/` | Add valid sections, then **Confirm** | Enrollment CONFIRMED; a DRAFT assessment is auto-created | FR-C + auto assessment (Milestone B) |

## Part B — Finance cycle (Cashier + Administrator)

| Step | Account | Page | Action | Expected result | Explain |
|---|---|---|---|---|---|
| B1 | demo.registrar1 | `/finance/assessment/<id>/` | Open the new assessment, click **Finalize** | Status FINALIZED; itemized lines + total | Fee engine (category stacking, precedence) |
| B2 | demo.cashier1 | `/finance/assessment/<id>/` | View itemized charges + balance | Lines, total, amount paid, balance shown | FR-D1/D2/D4 |
| B3 | demo.cashier1 | `/finance/assessment/<id>/pay/` | Record a partial CASH payment | Balance decreases; auto-allocated | FR-D3 + explicit allocation |
| B4 | demo.cashier1 | `/finance/payment/<id>/receipt/` | Open receipt, click Print | Printable acknowledgment (Save as PDF) | Receipt |
| B5 | demo.cashier1 | `/finance/assessment/<id>/adjustment/new/` | Raise a CREDIT adjustment | Submitted for approval (not yet applied) | Separation of duties |
| B6 | demo.admin1 | `/finance/approvals/` | Approve the adjustment | Credit applied; balance reflects it | Creator ≠ approver enforced |
| B7 | demo.admin1 | `/finance/assessment/<id>/` | (Optional) Reverse a payment | Payment REVERSED; no longer counts; audit entry | Reversal with trail |

Pre-seeded scenarios you can also show without creating anything: S01 unpaid
(9,650), S07 fully paid (0), S08 reversed, S09 approved scholarship, S12
outstanding prior-term balance, S13 revised assessment (two versions).

## Part C — Reports & exports

| Step | Account | Page | Action | Expected result |
|---|---|---|---|---|
| C1 | demo.registrar1 | `/reports/enrolled/` | Filter by term/program | Enrolled students by course/year |
| C2 | demo.registrar1 | `/reports/semester/` | View | Distinct students vs enrollment records |
| C3 | demo.cashier1 | `/reports/collection/` | Filter by method/date | Received collections; scholarship separate |
| C4 | demo.cashier1 | `/reports/collection/?format=csv` | Export | CSV downloads; opens in a spreadsheet |
| C5 | demo.registrar1 | `/reports/enrolled/` | Click **Print / Save as PDF** | Print-friendly report |

## Part D — Roles & security (quick)

| Step | Account | Page | Expected |
|---|---|---|---|
| D1 | demo.stud01 | `/dashboard/`, `/my-enrollments/` | Student dashboard + own enrollments only |
| D2 | demo.stud01 | `/finance/` | **403** (denied) |
| D3 | demo.stud01 | `/my-enrollments/<other-student-id>/` | **404** (cannot view others) |
| D4 | nicholohq (superuser) | `/admin/` | Django admin (fee rules, policy, users) |

**Total demo time:** ~10–12 minutes (fits within slides 12–14).
