-- Create the empty PostgreSQL database used by the Django e-wallet project.
--
-- pgAdmin 4 usage:
--   1. Select the existing "postgres" database.
--   2. Open Tools > Query Tool.
--   3. Open this file and press F5 (Execute Script).
--   4. Refresh the Databases node.
--   5. Configure .env and run: python manage.py migrate
--
-- Run this script only once. If ewallet already exists, do not run it
-- again; continue with the Django migration step instead.

CREATE DATABASE ewallet
    WITH
    OWNER = postgres
    ENCODING = 'UTF8'
    TEMPLATE = template0;
