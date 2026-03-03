-- =============================================================================
-- least_privilege.sql
-- Module 5 — GradCafe Admissions Analysis
--
-- Creates a non-superuser PostgreSQL role and login user for the application.
-- Run this script as a PostgreSQL SUPERUSER against the target database.
--
-- Replace ALL placeholder values before running:
--   REPLACE_ME         → a strong, randomly generated password
--   your_database_name → the actual target database name
--
-- Generate a strong password with:
--   python -c "import secrets; print(secrets.token_urlsafe(32))"
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Application role (no superuser, no DB/role creation, no inheritance)
--    NOLOGIN: the role itself cannot log in; only the user account can.
-- -----------------------------------------------------------------------------
CREATE ROLE module5_app_role
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOLOGIN;


-- -----------------------------------------------------------------------------
-- 2. Login user that carries the role
--    LOGIN: allowed to open a session.
--    All other dangerous privileges explicitly denied.
-- -----------------------------------------------------------------------------
CREATE USER module5_app_user
    WITH LOGIN
    PASSWORD 'REPLACE_ME'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE;


-- -----------------------------------------------------------------------------
-- 3. Assign role to user so the user inherits the role's privileges
-- -----------------------------------------------------------------------------
GRANT module5_app_role TO module5_app_user;


-- -----------------------------------------------------------------------------
-- 4. Database-level: allow connection
--    Without CONNECT, the user cannot open a session to the database at all.
-- -----------------------------------------------------------------------------
GRANT CONNECT ON DATABASE your_database_name TO module5_app_role;


-- -----------------------------------------------------------------------------
-- 5. Schema-level: allow name resolution within the public schema
--    Without USAGE, references like "public.applicants" cannot be resolved.
-- -----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO module5_app_role;


-- -----------------------------------------------------------------------------
-- 6. Table-level: only SELECT and INSERT
--    - SELECT: required by all 11 analytical queries in query_data.py
--    - INSERT: required by load_rows() in load_data.py (append-only ETL)
--    The application never issues UPDATE, DELETE, TRUNCATE, DROP, or ALTER.
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT ON TABLE public.applicants TO module5_app_role;


-- -----------------------------------------------------------------------------
-- 7. Sequence-level: USAGE so the SERIAL primary key auto-increments on INSERT
--    - USAGE: required for nextval() — called internally by PostgreSQL on INSERT
--    - SELECT: required for currval() — used internally by psycopg after INSERT
--    Without USAGE on the sequence, every INSERT will fail with a permissions error.
-- -----------------------------------------------------------------------------
GRANT USAGE, SELECT ON SEQUENCE public.applicants_id_seq TO module5_app_role;


-- -----------------------------------------------------------------------------
-- 8. Default privileges: ensure the role retains access if new tables/sequences
--    are created in the public schema in the future.
--    Run this as the schema owner (usually the superuser or the database owner).
-- -----------------------------------------------------------------------------
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT ON TABLES TO module5_app_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO module5_app_role;
