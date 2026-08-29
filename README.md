# E-Wallet Project

A Django 6 e-wallet application using Django REST Framework, JWT authentication, PostgreSQL, and Tailwind CSS.

## Requirements

- Python 3.12 or newer
- PostgreSQL 18 or newer
- Git (optional)

## Install

From the project root, create a virtual environment and install the dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Copy the environment template and replace any service credentials needed by the features you use:

```bash
cp .env.example .env
```

Never commit real passwords, tokens, or API keys from `.env`.

## Create the PostgreSQL 18 database

On macOS with Homebrew:

```bash
brew services start postgresql@18
psql -X -v ON_ERROR_STOP=1 -d postgres -f PGSQL/Bunly/DB.sql
```

Set Django's database connection in `.env`:

```dotenv
DATABASE_URL=postgresql:///ewallet
```

The socket URL uses your current local PostgreSQL role and does not store a password. For a password-based or remote connection, use:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/ewallet
```

More database options and troubleshooting are in [`PGSQL/Bunly/README.md`](PGSQL/Bunly/README.md).

## Apply migrations

```bash
source venv/bin/activate
python manage.py migrate
python manage.py check
```

Migration `wallet.0013_load_cambodia_geography` loads the Cambodia geography data, so the first migration may take a little longer.

## Run the application

```bash
source venv/bin/activate
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Create an administrator when needed:

```bash
python manage.py createsuperuser
```

## Common commands

```bash
python manage.py showmigrations
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

Tailwind CSS is loaded from a CDN, so no local frontend build step is required. When `DATABASE_URL` is missing or empty, the project falls back to `db.sqlite3`.
