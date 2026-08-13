# e_wallet

A Django wallet application built with Django REST Framework and Tailwind CSS.

## Prerequisites

- Python 3.10+ installed
- Git (optional)
- Optional: PostgreSQL if you want to use a remote database via `DATABASE_URL`

## Setup

1. Open a terminal in the project root:
   - Windows PowerShell:
     ```powershell
     cd C:\Users\Admin\Documents\BIU_Y3\S1\System_Analysis_Class\assignment\e_wallet
     ```
   - macOS / Linux:
     ```bash
     cd ~/Documents/BIU_Y3/S1/System_Analysis_Class/assignment/e_wallet
     ```

2. Create and activate a virtual environment (if not already activated):
   - Windows PowerShell:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - macOS / Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install dependencies:
   - Windows / macOS / Linux:
     ```bash
     pip install django djangorestframework djangorestframework-simplejwt dj-database-url python-dotenv psycopg2-binary
     ```

   If you prefer, create a `requirements.txt` file with these packages and install with:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (optional):

   - The project will use SQLite by default via `db.sqlite3`.
   - To use PostgreSQL or another database, create a `.env` file in the project root with:
     ```dotenv
     DATABASE_URL=<your-supabase-postgresql-connection-url>
     ```

## Database setup

Run migrations:

```powershell
python manage.py migrate
```

Create a superuser if you need admin access:

```powershell
python manage.py createsuperuser
```

## Run server

Start the local development server:

```powershell
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Notes

- Tailwind CSS is loaded via CDN in the templates, so no local frontend build step is required.
- Default login redirect is `/` and logout redirect is `/login/`.
- If an `.env` file exists, the project loads it using `python-dotenv`.
- The default database is SQLite, but `dj-database-url` allows switching to a different database with `DATABASE_URL`.

## Helpful commands

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
