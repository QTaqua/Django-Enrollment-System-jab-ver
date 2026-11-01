# E5 — Presentation Slide Outline (≤ 45 minutes)

Content package for building the PowerPoint later (the file itself is **not**
created yet). 18 slides; durations sum to ~45 min (live-demo slides are
flexible). Visuals reference the diagrams/screenshots in this submission.
All figures are **verified**; demo data is **fictional**.

| # | Title | Main points | Suggested visual | Duration |
|---|---|---|---|---|
| 1 | Title | Holy Trinity University · Enrollment System; ADS final project; team; date | HTU seal (`static/img/htu-seal.png`) | 0:30 |
| 2 | Introduction & background | Academic ADS project; college enrollment domain; HTU branding (not official) | #01 login screenshot | 2:00 |
| 3 | Problem statement & objectives | Manual enrollment pain points; objectives = integrity-safe enrollment + finance + reports + roles | bullet list | 2:30 |
| 4 | Scope & limitations | In scope: A–G requirements; out of scope: instructor grading, native PDF/xlsx, reconciliation UI; DEMO data only | scope table | 2:30 |
| 5 | Functional requirements (A–G) | Summarize 7 groups + status (mostly Implemented; FR-A2/FR-B1 Partial) | traceability matrix excerpt | 4:00 |
| 6 | Technology stack | Python 3.13.7, Django 5.2.18, MySQL 9.5, mysqlclient 2.3.0, Bootstrap 5.3.3; why each | stack table | 3:00 |
| 7 | System architecture / DFD | 5 Django apps; context + level-1 DFD; services enforce rules | `dfd_context` / `dfd_level_1` | 3:30 |
| 8 | Use case diagram | Five roles and their implemented use cases | `use_case.md` diagram | 2:00 |
| 9 | Database design & ERD | 25 tables; PK/FK PROTECT; unique/check constraints; 3NF | `erd/ERD_NOTES.md` diagram | 4:00 |
| 10 | Finance data design | Assessment versioning, immutable lines, payment allocation, authoritative balance, separation of duties | finance ERD subset | 3:00 |
| 11 | Application & roles overview | Role-aware dashboards; server-side permissions; branded UI | #02–#04 dashboards | 2:00 |
| 12 | DEMO — Enrollment cycle | Registrar: catalog → scheduled section (room conflict) → create & confirm enrollment; show a rejection | live app / #10–#14 | 5:00 |
| 13 | DEMO — Finance | Auto draft assessment → finalize → record payment → receipt → balance; scholarship/credit approval (admin) | live app / #15–#18 | 6:00 |
| 14 | Reports & exports | Enrolled/semester/collection reports; CSV export; browser print-to-PDF | #19–#23 | 3:00 |
| 15 | Testing & verification | 248 automated tests passing; `check` clean; HTTP-session role checks; seed scenarios | test summary | 3:00 |
| 16 | Project statistics | Verified counts (apps, tables, demo data, users by role) | stats table (slide 17 data) | 1:30 |
| 17 | Limitations & future work | Legacy assessments; prev-term WARN hook; reconciliation UI; auto student-ID; native PDF/xlsx; GUI test env | bullet list | 2:00 |
| 18 | Conclusion & references | Requirements met; integrity focus; references | reference list | 1:30 |

**Total ≈ 44:30** (slides 12–13 live-demo durations are adjustable).

## Verified project statistics (for slides 15–16)

- **Apps:** 5 (`accounts`, `academics`, `scheduling`, `enrollment`, `finance`).
- **Business tables:** 25. **Automated tests:** **248 passing**; `check` clean;
  `makemigrations --check` → no changes.
- **DEMO data:** 5 colleges, 21 programs, 1 BSIT simulation curriculum, 11
  courses, 3 terms, 6 rooms, 15 sections, 20 enrollments, 8 fee rules, 15
  assessments, 8 payments.
- **Demo users (25):** 1 Administrator, 2 Registrar, 2 Cashier, 5 Instructor,
  15 Student (+ the project's real superuser).

> Do not claim production deployment or performance benchmarks — none were
> measured.
