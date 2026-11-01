# E2 — Use Case Diagram

Only **genuinely implemented** interactions are shown (no invented use cases).
Rendered with Mermaid (GitHub/VS Code render this natively). Source is this file.

## Legend / notation

- **Ovals (use cases)** = actions the system supports.
- **Actors (left/right)** = the five user roles.
- An edge **actor → use case** means that role can perform it (server-side
  enforced).
- Read-only use cases are suffixed "(view)". Administrator management of fee
  rules / policy / users is via the Django admin site (`is_staff` + Administrator
  role).

```mermaid
flowchart LR
  Reg([Registrar])
  Cash([Cashier])
  Adm([Administrator])
  Ins([Instructor])
  Stu([Student])

  subgraph SYS[ADS Enrollment System]
    UC_login(Login / role dashboard)
    UC_acad(Manage academic catalog\ncolleges, programs, curricula,\ncourses, prerequisites, terms)
    UC_people(Manage student &\ninstructor accounts)
    UC_sched(Manage sections & rooms\nconflict-checked)
    UC_enroll(Manage enrollment\ncreate, add section, confirm, drop)
    UC_final(Finalize / revise assessment)
    UC_pay(Record payment & print receipt)
    UC_adj(Raise adjustment / scholarship)
    UC_appr(Approve adjustments,\nscholarships, reverse payments)
    UC_fee(Manage fee rules & policy\nDjango admin)
    UC_rep_enr(View enrolled & semester reports\n+ CSV)
    UC_rep_col(View collection report + CSV)
    UC_view_acad(View academic/section/\nenrollment data - view)
    UC_my(View own enrollments - view)
  end

  Reg --> UC_login & UC_acad & UC_people & UC_sched & UC_enroll & UC_final & UC_rep_enr & UC_view_acad
  Cash --> UC_login & UC_pay & UC_adj & UC_rep_col & UC_view_acad
  Adm --> UC_login & UC_view_acad & UC_final & UC_appr & UC_fee & UC_rep_enr & UC_rep_col
  Ins --> UC_login
  Stu --> UC_login & UC_my
```

## Explanation

- **Registrar** owns academic/people/section/enrollment management and finalizes
  or revises assessments; can view the enrolled/semester reports.
- **Cashier** records payments and prints receipts, raises adjustments/
  scholarships for approval, and views the collection report.
- **Administrator** is read-only on the in-app academic/enrollment screens, but
  approves finance adjustments/scholarships, reverses payments, finalizes/revises
  assessments, manages fee rules and policy (Django admin), and views all
  reports.
- **Instructor** currently has login + a role dashboard only (no roster/grading
  screens — intentionally not shown, as they are not implemented).
- **Student** has login + a read-only view of their own enrollments; students
  cannot self-enroll or view other students' records.
