# E5 — Speaker Notes (per slide)

Concise talking points matching `SLIDE_OUTLINE.md`. Keep to the noted durations.

1. **Title** — Greet; state this is the ADS final project: a Django + MySQL
   college enrollment system branded for HTU (an academic demonstration, not an
   official HTU system).
2. **Introduction** — Enrollment involves students, curricula, schedules, fees,
   and multiple staff roles; our goal is a database-centric system that keeps all
   of this consistent.
3. **Problem & objectives** — Manual enrollment risks double-booked rooms,
   missed prerequisites, and inconsistent balances. Objectives: enforce academic
   rules, compute fees reliably, support reporting, and separate role
   permissions.
4. **Scope & limitations** — We implemented instructor requirement groups A–G.
   Out of scope: instructor grading, native PDF/Excel engines, a reconciliation
   UI. All data shown is fictional DEMO data.
5. **Functional requirements** — Walk the 7 groups; note most are Implemented;
   student-ID is entered (unique but not auto-generated) and course deletion is
   not exposed — both honestly marked Partial.
6. **Technology stack** — Verified versions. Django gives us the ORM, auth,
   migrations, admin, and transaction tools that the integrity rules need; MySQL
   is the relational store; Bootstrap handles the responsive UI; CSV export needs
   no extra dependency.
7. **Architecture / DFD** — Five apps map to the DFD processes; business rules
   live in service modules using atomic transactions and row locking.
8. **Use case** — Each of the five roles and only the use cases actually
   implemented (e.g., instructor has login/dashboard only).
9. **Database & ERD** — 25 tables, integer PKs, PROTECT FKs, unique + check
   constraints, 3NF (units live only on Course; names only on User; balances are
   computed, not stored).
10. **Finance design** — Emphasize integrity: immutable finalized assessment
    versions, explicit payment allocations (no double counting), authoritative
    balance, and creator≠approver separation of duties.
11. **Application & roles** — Show role-aware dashboards and that permissions are
    enforced server-side (not just hidden links).
12. **Enrollment demo** — Follow `DEMO_SCRIPT.md` part A; highlight a rejection
    (prerequisite or room/schedule conflict) to show validation.
13. **Finance demo** — Follow part B; show auto draft assessment on confirmation,
    finalize, record payment, receipt, and an approval requiring a different
    approver.
14. **Reports & exports** — Run the three reports; export a CSV; use the Print
    button for Save-as-PDF; note scholarship is shown separately from cash.
15. **Testing** — 248 automated tests pass; `check` clean; role access verified
    live via HTTP sessions; the seed reproduces 12 finance scenarios.
16. **Statistics** — Read the verified counts; stress the demo data is fictional.
17. **Limitations & future work** — Legacy assessments on the disposable DB,
    previous-term WARN without an enforcement hook, reconciliation UI, auto
    student-ID, native PDF/xlsx, and the GUI-test environment constraint.
18. **Conclusion** — Requirements A–G met with a strong integrity focus; thank
    the audience; show references.
