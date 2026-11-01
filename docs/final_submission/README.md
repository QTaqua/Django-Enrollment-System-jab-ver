# ADS Enrollment System — Final Submission Documentation

Academic final-project documentation for the **Advanced Database Systems (ADS)**
course. The application is a Django + MySQL college enrollment system, branded as
the **Holy Trinity University · Enrollment System**.

> **Academic / demonstration project.** This is an independently developed
> student project, **not** an official HTU-operated or HTU-endorsed system. All
> students, staff, fees, schedules, curricula, and transactions in the demo are
> **fictional DEMO data**. The HTU name, seal, and college/program *names* are
> used for identification only (see `docs/brand/NOTICE.md`).

## Contents

| Document | Purpose |
|---|---|
| [functional_requirements.md](functional_requirements.md) | E1 — full functional-requirements spec (A–G) with implementation status |
| [requirements_traceability.md](requirements_traceability.md) | E1 — traceability matrix (requirement → code → evidence) |
| [database_documentation.md](database_documentation.md) | E3 — entities, keys, constraints, normalization, finance/room design, limitations |
| [technology_stack.md](technology_stack.md) | E3 — technologies, versions, justification, references |
| [system_diagrams/use_case.md](system_diagrams/use_case.md) | E2 — Use Case diagram (Mermaid) |
| [system_diagrams/dfd_context.md](system_diagrams/dfd_context.md) | E2 — DFD context diagram (Mermaid) |
| [system_diagrams/dfd_level_1.md](system_diagrams/dfd_level_1.md) | E2 — DFD level-1 diagram (Mermaid) |
| [erd/ERD_NOTES.md](erd/ERD_NOTES.md) | E3 — final ERD (Mermaid) + differences vs the original `erd_artifacts/` |
| [screenshots/SCREENSHOT_CHECKLIST.md](screenshots/SCREENSHOT_CHECKLIST.md) | E4 — capture checklist + placeholders |
| [presentation/SLIDE_OUTLINE.md](presentation/SLIDE_OUTLINE.md) | E5 — slide-by-slide outline (≤45 min) |
| [presentation/SPEAKER_NOTES.md](presentation/SPEAKER_NOTES.md) | E5 — speaker notes per slide |
| [presentation/DEMO_SCRIPT.md](presentation/DEMO_SCRIPT.md) | E5 — end-to-end live demo script |
| [presentation/REFERENCES.md](presentation/REFERENCES.md) | E5 — reference list |

## Verified project facts (as of this milestone)

- **Stack:** Python 3.13.7, Django 5.2.18, MySQL (mysqlclient 2.3.0), Bootstrap
  5.3.3 (CDN). Verified from the project environment.
- **Apps (5):** `accounts`, `academics`, `scheduling`, `enrollment`, `finance`.
- **Business model tables (25):** 1 user + 9 academics + 2 scheduling + 2
  enrollment + 11 finance (see database_documentation.md).
- **Automated tests:** **248 tests, all passing** (`python manage.py test`),
  across Milestones A–D. `manage.py check` clean; `makemigrations --check` shows
  no uncommitted model changes.
- **Seeded DEMO dataset (disposable DB `ads_enrollment_fresh_test`):** 5 colleges,
  21 programs, 1 BSIT *simulation* curriculum, 11 courses, 3 academic terms, 6
  rooms, 15 sections, 20 enrollments, 8 fee rules, 15 assessments, 8 payments;
  25 demo users (1 Administrator, 2 Registrar, 2 Cashier, 5 Instructor, 15
  Student) alongside the project's real superuser.

## Known limitations (summary — details in each document)

- On the disposable DB, two assessments (S06/S07) remain **legacy** (flat total)
  from an earlier seed; a fresh seed makes all assessments fee-rule-computed.
- The previous-term-balance policy is **WARN** but has **no enrollment-time
  enforcement hook** (data/reporting only).
- Finance **reconciliation** has a data model + service but **no dedicated UI**.
- **GUI browser testing** was blocked in the dev environment (the Chrome
  extension could not reach `localhost`); workflows were verified via automated
  tests and live **HTTP-session** checks instead.
- Some instructor requirements are **Partial** (see functional_requirements.md):
  manual student-ID entry, no course delete UI, no enrollment-time year-level
  gate, browser-print "Save as PDF" (no server-side PDF engine).

## Scope note on this documentation

These documents describe the application **as actually implemented**. Where a
requirement is partial or unimplemented, it is labeled as such — a database model
alone is never treated as a completed workflow. Screenshots are left as
instructions/placeholders for the reviewer to capture, because genuine browser
screenshots could not be produced in the development environment.
