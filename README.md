# EduManage

A Django-based school management system for handling teachers, students, class arms, subjects, results, and academic terms, with role-based dashboards for Admins, Teachers, and Students.

## Features

- **Role-based access** — separate dashboards and permissions for Admins, Teachers, and Students
- **People management** — register teachers and students, assign registration numbers
- **Class structure** — create class arms, assign teachers and students to them
- **Subjects** — register subjects and assign them to class arms
- **Results** — enter test/assignment/exam scores, auto-calculated totals, grades, and class positions
- **Academic terms** — results are scoped to a specific term/session, so starting a new term never overwrites past results; past terms remain viewable
- **PDF report cards** — students can download their result sheet as a PDF, including an automated performance comment
- **Profiles** — each role can view and edit their own profile
- **Midterm assignments** — teachers can create and manage midterm assignments per class

## Tech Stack

- **Backend:** Django 6.0
- **Database:** PostgreSQL (production), SQLite (local development fallback)
- **PDF generation:** ReportLab
- **Static files:** WhiteNoise
- **WSGI server:** Gunicorn
- **Deployment:** Render

## Local Setup

1. **Clone the repo and create a virtual environment**
   ```bash
   git clone <repo-url>
   cd Mini_School_Sysytem
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your `.env` file**

   Create a `.env` file in the project root (never commit this):
   ```env
   SECRET_KEY=your-local-secret-key
   DEBUG=True
   ALLOWED_HOSTS=
   # Leave DATABASE_URL unset to use local SQLite, or set it to test against Postgres
   # DATABASE_URL=
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the dev server**
   ```bash
   python manage.py runserver
   ```

7. **Set the active academic term**

   Log in as the superuser, go to the Admin Dashboard → **Start New Term**, and set the current session/term. Score entry is blocked until a term is active.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django's cryptographic signing key. Use a different value in production than in dev. |
| `DEBUG` | Yes | `True` for local dev, `False` in production. |
| `ALLOWED_HOSTS` | Production only | Comma-separated list of allowed hostnames (e.g. your Render domain). |
| `DATABASE_URL` | Production only | Full Postgres connection string. Falls back to local SQLite when unset. |

## Deployment (Render)

1. Provision a PostgreSQL instance on Render and copy its **Internal Database URL**.
2. Create a Web Service pointing at this repo.
3. Set environment variables (`SECRET_KEY`, `DEBUG=False`, `DATABASE_URL`) in the service's Environment tab.
4. **Build Command:**
   ```bash
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
   ```
5. **Start Command:**
   ```bash
   gunicorn Mini_School_Sysytem.wsgi
   ```
6. Deploy, then log in with `createsuperuser` (run via Render's shell) and set the active term.

## Project Structure

```
Mini_School_Sysytem/
├── Mini_School_Sysytem/     # Project settings, URLs, WSGI
├── school_app/
│   ├── models.py            # StudentProfile, TeacherProfile, ClassArm, Subject, Result, Term, AcademicSession
│   ├── views/                # Role-based views (result_views.py, auth_views.py, etc.)
│   ├── decorators.py         # admin_required, teacher_required, student_required
│   ├── utils.py               # Score/grade/comment calculation helpers
│   ├── context_processors.py # Injects the active term into every template
│   └── templates/school/      # HTML templates (shared navy/green design system)
├── requirements.txt
└── manage.py
```

## Roles & Access

| Role | Access |
|---|---|
| **Admin** | Full access — manage people, classes, subjects, terms, and view all results |
| **Teacher** | Manage scores and view results for their own assigned class arm only |
| **Student** | View and download their own results and profile only |
