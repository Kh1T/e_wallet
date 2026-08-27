# E-Wallet PostgreSQL Setup

This directory contains a complete PostgreSQL export of the Django e-wallet database:

- `e_wallet_postgresql.sql`

The export includes the wallet tables, Django authentication and admin tables, JWT blacklist tables, migrations, constraints, indexes, and Cambodia geography seed data.

## 1. Start PostgreSQL on macOS

If PostgreSQL was installed with Homebrew, start it with:

```bash
brew services start postgresql
```

Confirm that PostgreSQL is running:

```bash
pg_isready -h localhost -p 5432
```

Expected output:

```text
localhost:5432 - accepting connections
```

## 2. Create the database

The project is configured to use the local macOS user `macbook` and database `bunly_wallet`.

```bash
createdb -h localhost -p 5432 -U macbook bunly_wallet
```

If the database already exists, PostgreSQL will report an error. Do not delete an existing database unless you are sure its data is no longer needed.

## 3. Import the SQL file

From the project root, run:

```bash
cd /Users/macbook/Documents/UC1-IT/Y3-S1/django/ass/e_wallet

psql -X -v ON_ERROR_STOP=1 \
  -h localhost \
  -p 5432 \
  -U macbook \
  -d bunly_wallet \
  -f PGSQL/Bunly/e_wallet_postgresql.sql
```

`ON_ERROR_STOP=1` makes the import stop immediately if PostgreSQL encounters an error.

## 4. Configure Django

The project `.env` file should contain:

```dotenv
DATABASE_URL=postgresql://macbook@localhost:5432/bunly_wallet
```

If your PostgreSQL user requires a password, use:

```dotenv
DATABASE_URL=postgresql://macbook:YOUR_PASSWORD@localhost:5432/bunly_wallet
```

Replace `YOUR_PASSWORD` with the real password. Do not commit `.env` to Git.

## 5. Verify the import

Check that the wallet tables were created:

```bash
psql -h localhost -p 5432 -U macbook -d bunly_wallet \
  -c "SELECT COUNT(*) AS wallet_tables FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'wallet_%';"
```

The expected result is `26` wallet tables.

Check the Django migration records:

```bash
psql -h localhost -p 5432 -U macbook -d bunly_wallet \
  -c "SELECT app, name FROM django_migrations WHERE app = 'wallet' ORDER BY id;"
```

The result should list wallet migrations `0001` through `0014`.

Run Django's checks:

```bash
source venv/bin/activate
python manage.py check
python manage.py showmigrations
```

All migrations should be marked with `[X]`. You do not need to run them again because the SQL export already contains the complete schema and migration history.

## 6. Create an administrator

Create a Django administrator account if needed:

```bash
source venv/bin/activate
python manage.py createsuperuser
```

## 7. Run the application

```bash
source venv/bin/activate
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser.

## Common errors

### `connection refused`

PostgreSQL is not running. Start it with:

```bash
brew services start postgresql
```

### `role "macbook" does not exist`

Use your existing PostgreSQL username instead of `macbook` in the commands and `DATABASE_URL`. You can list PostgreSQL roles with:

```bash
psql postgres -c "\du"
```

### `database "bunly_wallet" already exists`

The database has already been created. If it is empty, continue with the import step. If it contains tables or data, back it up before making changes.

### `relation already exists`

The SQL export must be imported into an empty database. Create a new database with a different name, or back up and remove the existing database before retrying.
