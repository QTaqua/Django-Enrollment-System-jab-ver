# E2 — Data Flow Diagram: Context (Level 0)

A single central process (the system) with the five external entities and the
major data flows between them. Mermaid source below.

## Legend / notation

- **Central process** = the whole ADS Enrollment System (one process at context
  level).
- **External entities** = the five user roles (sources/sinks of data).
- **Arrows** = data flows (label = the data moving).

```mermaid
flowchart TB
  Reg[Registrar]
  Cash[Cashier]
  Adm[Administrator]
  Ins[Instructor]
  Stu[Student]

  SYS((ADS Enrollment System))

  Reg -- "academic/catalog data,\nsection & enrollment data,\nassessment finalize" --> SYS
  SYS -- "enrollment confirmations,\nvalidation errors,\nenrolled/semester reports" --> Reg

  Cash -- "payment details,\nadjustment/scholarship requests" --> SYS
  SYS -- "assessment & balance,\nreceipts, collection report" --> Cash

  Adm -- "fee rules, policy,\napprovals, user management" --> SYS
  SYS -- "approval queues, reports,\naudit records" --> Adm

  Stu -- "login credentials" --> SYS
  SYS -- "own enrollment records (read-only)" --> Stu

  Ins -- "login credentials" --> SYS
  SYS -- "instructor dashboard" --> Ins
```

## Explanation

The context diagram treats the entire application as one process. Registrars
supply academic, scheduling, and enrollment data and receive confirmations and
enrollment reports. Cashiers supply payments and receive assessments, balances,
receipts, and the collection report. Administrators configure fee rules/policy,
approve finance actions, and manage users, receiving approval queues, reports,
and audit information. Students and instructors authenticate and receive
read-only views appropriate to their role. The Level-1 diagram
([dfd_level_1.md](dfd_level_1.md)) decomposes this single process into the
functional processes and data stores.
