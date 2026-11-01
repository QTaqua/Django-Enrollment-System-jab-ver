# E3 — Final ERD and Differences from the Original

The **original ERD source is preserved** in `erd_artifacts/`
(`ADS_Enrollment_System_Simplified_ERD.png`, `..._Schema.sql`, `....mwb`). That
artifact reflects the **pre-Milestone-A/B** schema (the original 15 business
tables, crow's-foot notation). It was **not modified**. This document provides an
**updated final-schema ERD** reflecting Milestones A (Room) and B (finance
versioning/ledger), and lists the differences.

> The live database schema was **not** changed to produce this document.

## Differences vs. the original `erd_artifacts/` ERD

**Added in Milestone A (scheduling):**
- New entity **`room`**; `section` gained a nullable FK **`room`** (legacy
  `room_code` retained).

**Added in Milestone B (finance):** new entities
- **`fee_rule`**, **`assessment_version`**, **`assessment_line`**,
  **`payment_allocation`**, **`adjustment`**, **`scholarship_award`**,
  **`finance_policy`**, **`reconciliation`**, **`finance_audit_log`**.
- `assessment` gained `current_version` (FK→assessment_version, SET_NULL) and
  `needs_review`.
- `payment` gained statuses (PENDING/REVERSED), method E_WALLET, `reference_note`,
  `reversed_at`.

Business tables: **15 → 25**.

## Final ERD (Mermaid; crow's-foot cardinalities)

`||` = exactly one · `o{` = zero-or-many · `|{` = one-or-many · `o|` =
zero-or-one. Attributes are abbreviated to keys for readability.

```mermaid
erDiagram
  USER ||--o| STUDENT : "has profile"
  USER ||--o| INSTRUCTOR : "has profile"
  COLLEGE ||--o{ PROGRAM : offers
  PROGRAM ||--o{ CURRICULUM : "has versions"
  CURRICULUM ||--o{ CURRICULUM_COURSE : contains
  COURSE ||--o{ CURRICULUM_COURSE : "placed in"
  COURSE ||--o{ COURSE_PREREQUISITE : "is course"
  COURSE ||--o{ COURSE_PREREQUISITE : "is prerequisite"
  CURRICULUM ||--o{ STUDENT : "followed by"

  COURSE ||--o{ SECTION : "offered as"
  ACADEMIC_TERM ||--o{ SECTION : "in term"
  INSTRUCTOR ||--o{ SECTION : teaches
  ROOM ||--o{ SECTION : hosts

  STUDENT ||--o{ ENROLLMENT : has
  ACADEMIC_TERM ||--o{ ENROLLMENT : "in term"
  ENROLLMENT ||--o{ ENROLLMENT_DETAIL : includes
  SECTION ||--o{ ENROLLMENT_DETAIL : "registered in"

  ENROLLMENT ||--o| ASSESSMENT : "assessed by"
  ASSESSMENT ||--o{ ASSESSMENT_VERSION : "has versions"
  ASSESSMENT_VERSION ||--o{ ASSESSMENT_LINE : itemizes
  FEE_RULE ||--o{ ASSESSMENT_LINE : "sourced from"
  ASSESSMENT ||--o{ PAYMENT : receives
  PAYMENT ||--o{ PAYMENT_ALLOCATION : allocated
  ASSESSMENT_VERSION ||--o{ PAYMENT_ALLOCATION : "applied to"
  ASSESSMENT ||--o{ ADJUSTMENT : "adjusted by"
  STUDENT ||--o{ SCHOLARSHIP_AWARD : "awarded"
  ASSESSMENT ||--o{ SCHOLARSHIP_AWARD : "applied to"
  USER ||--o{ PAYMENT : "received by"

  USER {
    int id PK
    string username UK
    string role
  }
  STUDENT {
    int id PK
    int user_id FK
    int curriculum_id FK
    string student_number UK
  }
  INSTRUCTOR {
    int id PK
    int user_id FK
    string employee_number UK
  }
  COLLEGE { int id PK
    string college_code UK }
  PROGRAM { int id PK
    int college_id FK
    string program_code UK }
  CURRICULUM { int id PK
    int program_id FK
    string curriculum_code }
  COURSE { int id PK
    string course_code UK
    decimal units }
  CURRICULUM_COURSE { int id PK
    int curriculum_id FK
    int course_id FK
    int year_level }
  COURSE_PREREQUISITE { int id PK
    int course_id FK
    int prerequisite_course_id FK }
  ACADEMIC_TERM { int id PK
    string academic_year
    int semester_number }
  ROOM { int id PK
    string room_code UK }
  SECTION { int id PK
    int course_id FK
    int term_id FK
    int instructor_id FK
    int room_id FK
    string section_code }
  ENROLLMENT { int id PK
    int student_id FK
    int term_id FK
    string status }
  ENROLLMENT_DETAIL { int id PK
    int enrollment_id FK
    int section_id FK
    string status
    decimal final_grade }
  FEE_RULE { int id PK
    string category
    string scope
    int course_id FK
    int program_id FK
    decimal amount }
  ASSESSMENT { int id PK
    int enrollment_id FK
    int current_version_id FK
    decimal total_amount }
  ASSESSMENT_VERSION { int id PK
    int assessment_id FK
    int version_number
    string status }
  ASSESSMENT_LINE { int id PK
    int version_id FK
    int fee_rule_id FK
    decimal line_total }
  PAYMENT { int id PK
    int assessment_id FK
    int received_by_id FK
    string receipt_number UK
    string status }
  PAYMENT_ALLOCATION { int id PK
    int payment_id FK
    int version_id FK
    decimal amount }
  ADJUSTMENT { int id PK
    int assessment_id FK
    string adjustment_type
    string status }
  SCHOLARSHIP_AWARD { int id PK
    int student_id FK
    int assessment_id FK
    string status }
```

> `FINANCE_POLICY` (single-row config), `RECONCILIATION`, and `FINANCE_AUDIT_LOG`
> are standalone finance tables not shown above (few/no cross-entity relations:
> policy is a singleton; reconciliation and audit-log reference a user/term
> loosely). They are documented in `../database_documentation.md`.

## Explanation

Cardinalities follow the model FKs: a `USER` has at most one `STUDENT` **or**
`INSTRUCTOR` profile (OneToOne); a `COLLEGE` offers many `PROGRAM`s; a `SECTION`
belongs to one course/term and optionally one instructor and one room; an
`ENROLLMENT` (one per student per term) has many `ENROLLMENT_DETAIL`s; an
`ENROLLMENT` has at most one `ASSESSMENT`, which owns many immutable
`ASSESSMENT_VERSION`s (one marked current), each itemized by `ASSESSMENT_LINE`s;
`PAYMENT`s are linked to versions through `PAYMENT_ALLOCATION`s. All FKs are
`PROTECT` except `ASSESSMENT.current_version` and `FINANCE_AUDIT_LOG.actor`
(`SET_NULL`).
