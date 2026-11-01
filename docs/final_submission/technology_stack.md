# E3 — Technology Stack and Justification

Versions below are **verified from the project environment** (`python --version`,
`django.get_version()`, `requirements.txt`, the Bootstrap CDN link in
`templates/base.html`, and the README). No version is guessed.

| Technology | Version (verified) | Role |
|---|---|---|
| Python | 3.13.7 | Application language / runtime |
| Django | 5.2.18 | Web framework (ORM, auth, admin, templating, migrations) |
| MySQL Server | 9.5.0 (8.0+ supported) | Relational database |
| mysqlclient | 2.3.0 | Python ↔ MySQL driver (DB-API) |
| Bootstrap | 5.3.3 (jsDelivr CDN) | Front-end CSS/JS framework |
| asgiref / sqlparse / tzdata | 3.13.0 / 0.6.0 / 2026.5 | Django transitive dependencies |
| Google Fonts — Poppins | — | Brand typeface (CDN, with system fallbacks) |

## Justification

### Python 3.13
A mature, readable, batteries-included language with first-class Django support.
Version 3.13 is the verified development runtime; Django 5.2 requires Python 3.10+.
*(Ref: Python docs.)*

### Django 5.2
Chosen as the full-stack framework because it provides, out of the box, exactly
the capabilities the instructor requirements need: a declarative **ORM** with
migrations (schema-as-code), **authentication** and a customizable **User** model
for role-based access, an **admin site**, server-side **form/validation** tooling,
the **template** engine for the HTML UI, and `transaction.atomic` /
`select_for_update` for the concurrency-safe business rules (prerequisites,
capacity, scheduling conflicts, fee finalization, payment allocation). Django 5.2
is an LTS-series release. *(Ref: Django docs — models, migrations, auth,
transactions, admin.)*

### MySQL 9.5 (via mysqlclient)
A widely used relational database appropriate for an Advanced **Database** Systems
project, supporting the normalized schema, foreign-key `PROTECT` semantics,
`UNIQUE`/`CHECK` constraints, and transactions used throughout. `mysqlclient` is
the standard C-based DB-API driver recommended by Django for MySQL. *(Ref: MySQL
Reference Manual; Django "Databases — MySQL notes".)*

### Bootstrap 5.3.3
Provides a responsive, accessible component/grid system so the UI is clean and
mobile-friendly without a heavy custom CSS effort, letting the project focus on
database and workflow logic. Loaded from a CDN; the HTU theme layer
(`static/css/htu-theme.css`) adds branding on top. *(Ref: Bootstrap docs.)*

### Why this stack fits the requirements
- **Data integrity (ADS focus):** ORM + DB constraints + service-layer
  transactions implement the enrollment and finance rules safely.
- **Role-based access:** Django auth + a custom `User.role` + permission
  mixins/decorators enforce the five roles server-side.
- **Reports/exports:** Django views + the standard-library `csv` module +
  print-friendly HTML satisfy the reporting requirement with **no extra
  dependency**.
- **Reproducibility:** migrations + a management-command seeder make the demo
  environment reproducible.

## References

Official documentation (home pages / relevant sections). URLs were used as the
basis for the justifications above; no claim is attributed that these sources do
not make.

1. Python Software Foundation — *Python 3.13 Documentation*. https://docs.python.org/3/
2. Django Software Foundation — *Django 5.2 Documentation* (Models, Migrations,
   Authentication, Database transactions, The admin site, Databases/MySQL notes).
   https://docs.djangoproject.com/en/5.2/
3. Oracle — *MySQL Reference Manual*. https://dev.mysql.com/doc/
4. *mysqlclient* (PyMySQL/mysqlclient) — project documentation.
   https://mysqlclient.readthedocs.io/
5. Bootstrap team — *Bootstrap 5.3 Documentation*. https://getbootstrap.com/docs/5.3/
6. Google Fonts — *Poppins*. https://fonts.google.com/specimen/Poppins

> Citation style: numbered references; cite by number in the slides/notes
> (e.g., "[2] Django docs"). Access dates can be added by the reviewer at
> submission time.
