# E2 — Data Flow Diagram: Level 1

Decomposes the system into functional processes and data stores that mirror the
actual Django apps, models, and services. Mermaid source below.

## Legend / notation

- **Pn (rounded)** = processes. **Dn (cylinders)** = data stores (database
  tables). **Actors (rectangles)** = the five roles. Arrows are labelled data
  flows.
- Process ↔ app mapping: P1 `accounts`; P2 `academics` (people); P3 `academics`
  (catalog); P4 `scheduling`; P5 `enrollment`; P6 `finance`; P7 reporting
  (`accounts/report_views.py`).

```mermaid
flowchart TB
  Reg[Registrar]
  Cash[Cashier]
  Adm[Administrator]
  Stu[Student]
  Ins[Instructor]

  P1([P1 User & Role Mgmt])
  P2([P2 Student/Instructor Records])
  P3([P3 Curriculum & Course Mgmt])
  P4([P4 Section & Room Scheduling])
  P5([P5 Enrollment Processing])
  P6([P6 Assessment & Finance])
  P7([P7 Reporting & Export])

  D1[(D1 Users)]
  D2[(D2 Academic Catalog)]
  D3[(D3 Sections & Rooms)]
  D4[(D4 Enrollments)]
  D5[(D5 Finance Ledger)]

  Adm --> P1 --> D1
  Reg --> P2 --> D1
  P2 --> D2
  Reg --> P3 --> D2
  Reg --> P4
  P4 --> D3
  P3 --> D2

  Reg --> P5
  P5 --> D4
  D2 -. curriculum/prereq .-> P5
  D3 -. sections/rooms .-> P5
  P5 -- confirmed enrollment --> P6

  Cash --> P6
  Adm --> P6
  P6 --> D5
  D2 -. fee rules .-> P6
  D4 -. enrollment .-> P6
  P6 -- receipts/balance --> Cash

  Reg --> P7
  Cash --> P7
  Adm --> P7
  D4 -. enrollment data .-> P7
  D5 -. payments/scholarships .-> P7
  P7 -- reports / CSV --> Reg
  P7 -- collection report / CSV --> Cash

  Stu --> P5
  P5 -- own records (read-only) --> Stu
  Ins --> P1
```

## Process descriptions

- **P1 User & Role Mgmt** — authentication, roles, dashboards (Django admin for
  Administrator user management). Store: **D1 Users** (`app_user`).
- **P2 Student/Instructor Records** — Registrar creates/updates accounts +
  profiles. Stores: D1, **D2** (curriculum link).
- **P3 Curriculum & Course Mgmt** — colleges, programs, curricula, courses,
  prerequisites, terms. Store: **D2 Academic Catalog**.
- **P4 Section & Room Scheduling** — sections with rooms/instructors; room,
  instructor, and student conflict checks. Store: **D3 Sections & Rooms**.
- **P5 Enrollment Processing** — curriculum/prerequisite/capacity/schedule
  validation; DRAFT→CONFIRMED. Reads D2/D3; store **D4 Enrollments**; emits a
  confirmed enrollment to P6.
- **P6 Assessment & Finance** — auto DRAFT assessment on confirmation, fee
  computation, finalize/revise, payments, allocations, adjustments, scholarships,
  balance. Reads fee rules (D2) + enrollment (D4); store **D5 Finance Ledger**.
- **P7 Reporting & Export** — enrolled-by-course/year, per-semester, and
  collection reports + CSV. Reads D4/D5 (read-only).

## Explanation

The data stores correspond to real tables: D1 = `app_user`; D2 = the academics
catalog tables + fee rules; D3 = `section`/`room`; D4 = `enrollment`/
`enrollment_detail`; D5 = the finance tables (assessment versions/lines,
payments, allocations, adjustments, scholarships, audit log). The flows match
the services: P5 reads curriculum/prerequisites/sections before writing an
enrollment, and a confirmed enrollment triggers P6 to create a draft assessment.
Reporting (P7) only reads — it never mutates D4/D5.
