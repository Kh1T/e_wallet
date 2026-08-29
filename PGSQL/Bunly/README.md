# E-Wallet PostgreSQL Setup

This project uses **PostgreSQL 18 + Django migrations**.

## 1. Create the Database

Open pgAdmin 4 and connect to the existing `postgres` database.

Open **Tools → Query Tool** and run:

```sql
CREATE DATABASE ewallet
    WITH
    OWNER = postgres
    ENCODING = 'UTF8';
```

> `DB.sql` only creates the `ewallet` database. It does **not** create tables.

## 2. Configure `.env`

Set your PostgreSQL connection:

```dotenv
DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/ewallet
```

Replace `YOUR_POSTGRES_PASSWORD` with your PostgreSQL password.

## 3. Run Django Migrations

Open Terminal:

```bash
cd /Users/macbook/Documents/UC1-IT/Y3-S1/django/ass/e_wallet
source venv/bin/activate
python manage.py migrate
```

Django migrations will create all required tables.

## 4. Check Migration Status

```bash
python manage.py check
python manage.py showmigrations
```

Applied migrations should show:

```text
[X]
```

## 5. Create Admin User

To create the prepared administrator and normal customer in pgAdmin:

1. Select the **ewallet** database.
2. Open **Tools → Query Tool**.
3. Open `PGSQL/Bunly/user.sql`.
4. Press **F5**.

The accounts are:

| Type | Login | Password |
| --- | --- | --- |
| Administrator | `admin@gmail.com` | `00000000` |
| Normal customer | `normal@ewallet.local` | `0000` |

Run `user.sql` only after `python manage.py migrate`. It also creates the normal customer's KHR wallet and the security and transaction-limit records for both users. Re-running the script resets the administrator password to `00000000` and the normal customer password to `0000`.

For local development only, these passwords are intentionally simple. Change them before deploying the project.

Alternatively, create an administrator interactively:

```bash
python manage.py createsuperuser
```

## 6. Run the Project

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Database Workflow

```text
DB.sql
   ↓
Create ewallet database
   ↓
Configure .env
   ↓
python manage.py migrate
   ↓
Django creates all tables
   ↓
python manage.py runserver
```

### Important

Do **not** import the old Supabase database.

Django migration files in:

```text
wallet/migrations/
```

are the source of truth for the database tables.
