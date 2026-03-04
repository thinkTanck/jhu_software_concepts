# Security Notes — Database Least-Privilege Configuration

## Overview

This application connects to PostgreSQL using the connection string stored in
the `DATABASE_URL` environment variable.  The database account should follow
the **principle of least privilege**: grant only the permissions the application
actually needs, and nothing more.

---

## What permissions this app needs

The application is **read-only** from the perspective of the analytical
queries (`query_data.py`) and **write-once** for the data-loading pipeline
(`load_data.py`).  Specifically:

| Operation | SQL privilege required |
|---|---|
| Analytical queries (SELECT) | `SELECT` on `applicants` |
| Load pipeline (INSERT) | `INSERT` on `applicants` |
| Idempotent upsert (`ON CONFLICT DO NOTHING`) | `INSERT` on `applicants` |
| Connect to the database | `CONNECT` on the database |
| Access the schema | `USAGE` on the schema |

The application does **not** need:

- `UPDATE` or `DELETE` (data is append-only)
- `DROP`, `ALTER`, `TRUNCATE` (no DDL at runtime)
- Superuser or ownership privileges
- Access to any table other than `applicants`

---

## Example SQL to create a least-privilege role

Run the following as a PostgreSQL superuser (replace placeholders):

```sql
-- 1. Create a dedicated role for the application.
--    Use a strong, randomly generated password in production.
CREATE ROLE app_gradcafe WITH LOGIN PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';

-- 2. Allow the role to connect to the database.
GRANT CONNECT ON DATABASE your_database_name TO app_gradcafe;

-- 3. Allow the role to use the public (or named) schema.
GRANT USAGE ON SCHEMA public TO app_gradcafe;

-- 4. Grant only SELECT and INSERT on the applicants table.
--    The app never needs UPDATE, DELETE, DROP, or ALTER.
GRANT SELECT, INSERT ON TABLE public.applicants TO app_gradcafe;

-- 5. (Optional) Allow the role to use the applicants_id_seq sequence
--    so that SERIAL primary-key auto-increment works.
GRANT USAGE, SELECT ON SEQUENCE public.applicants_id_seq TO app_gradcafe;
```

---

## Why these privileges?

- **CONNECT** — required for the application to open a database connection at all.
- **USAGE on schema** — required to resolve table/sequence names within the schema.
- **SELECT on applicants** — all nine analytical queries (`q1`–`q9`, `extra_1`, `extra_2`)
  read from this table.
- **INSERT on applicants** — `load_rows()` inserts new applicant records.
  The `ON CONFLICT DO NOTHING` clause also requires INSERT privilege.
- **USAGE + SELECT on sequence** — PostgreSQL SERIAL columns require the role to
  advance the sequence counter on each INSERT.

No other tables, schemas, or databases are accessed by this application.

---

## Credentials management

- Store `DATABASE_URL` (and `SECRET_KEY`) in your shell environment or a
  secrets manager; never hard-code them in source files.
- Use `.env.example` as a template; copy it to `.env` locally and fill in
  real values.  `.env` is listed in `.gitignore` so it is never committed.
- In CI/CD (GitHub Actions), use encrypted repository secrets to inject
  `DATABASE_URL` as an environment variable.

---

## Least Privilege Database Account

A dedicated non-superuser database account isolates the application from
accidental or malicious privilege escalation.  The account (`module5_app_user`)
inherits its privileges from the `module5_app_role` role, which is restricted to
exactly what the application needs at runtime:

- **CONNECT** on the database — required to open a connection at all.
- **USAGE** on the `public` schema — required to resolve table and sequence names.
- **SELECT** on `public.applicants` — required by all 11 analytical queries in
  `query_data.py` (`q1`–`q9`, `extra_question_1`, `extra_question_2`).
- **INSERT** on `public.applicants` — required by `load_rows()` in `load_data.py`;
  the `ON CONFLICT DO NOTHING` clause also requires INSERT privilege.
- **USAGE + SELECT** on `public.applicants_id_seq` — required so the SERIAL
  primary key auto-increments on every INSERT (`nextval()` / `currval()`).

No UPDATE, DELETE, DROP, ALTER, or TRUNCATE privileges are granted because the
application never issues those statements at runtime.  The role is also created
with `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT` to prevent any lateral
privilege escalation.

The full SQL script that creates the role, user, and all grants is in
[`sql/least_privilege.sql`](sql/least_privilege.sql).

Verification commands (psql queries to confirm non-superuser status and show
table/sequence grants) are in
[`evidence/least-privilege-psql.txt`](evidence/least-privilege-psql.txt).
