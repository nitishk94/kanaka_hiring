# HR Recruitment Management System

A modern, full-stack HR recruitment management system built with Flask, SQLAlchemy, and HTML with Tailwind CSS. This application streamlines the process of applicant tracking, referrals, interview scheduling, and admin management for HR teams.

## Features

- **Role-based Dashboards**: Separate dashboards for Admin, HR, Interviewer, and Referrer roles.
- **Applicant Management**: Upload, view, and manage applicants with detailed information and CV uploads.
- **Referrals**: Referrers can submit candidates, and HR can track and link referrals to applicants.
- **Test and Interview Scheduling**: HR can schedule and reschedule both tests and interviews, assign interviewers, and track progress.
- **Feedback Submission**: Interviewers can submit feedback regarding applicants during each interview.
- **User Management**: Admins can manage users, view logs, and configure system settings.
- **Modern UI**: Responsive, user-friendly interface with modern components and dropdowns.
- **Validation & Error Handling**: Robust form validation, duplicate detection, and user-friendly error messages.
- **Activity Logs**: System logs for admin review.

## Tech Stack

- **Backend**: Python v3.11, Flask, SQLAlchemy
- **Frontend**: Jinja2 templates, Tailwind CSS v3, Vue.js v2 (for advanced UI components)
- **Database**: PostgreSQL v17 (or any SQLAlchemy-supported DB)
- **Migrations**: Flask-Migrate (Alembic)
- **Testing**: Pytest

## Setup Instructions

### 1. Clone the Repository
```sh
git clone https://github.com/Shrivatsa-Naik/kanaka_hiring
cd Project
```

### 2. Create and Activate a Virtual Environment
### For development:
- On MacOS/Linux
  ```sh
  python3.11 -m venv venv
  source venv/bin/activate
  ```
- On Windows:
  ```powershell
  py -3.11 -m venv venv
  venv\Scripts\activate  
  ```

### 3. Install Dependencies
```sh
pip install -r requirements.txt
```

### 4. Set Environment Variables
### For development:
- On MacOS/Linux:
  ```sh
  export FLASK_APP=myapp:create_app
  export DATABASE_URL=postgresql://user:password@localhost/dbname
  export PYTHONPATH=.           # For running unit tests
  ```
- On Windows (cmd):
  ```cmd
  set FLASK_APP=myapp:create_app
  set DATABASE_URL=postgresql://user:password@localhost/dbname
  set PYTHONPATH=.              # For running unit tests
  ```
- On Windows (PowerShell):
  ```powershell
  $env:FLASK_APP="myapp:create_app"
  $env:DATABASE_URL="postgresql://user:password@localhost/dbname"
  $env:PYTHONPATH= "."          # For running unit tests
  ```

### 5. Initialize the Database
```sh
flask db init
flask db upgrade
```

### 6. Run the Application
### For development:
- On MacOS/Linux:
  ```sh
  python3 run.py
  ```
- On Windows:
  ```cmd
  python run.py
  ```

Visit [http://localhost:5002](http://localhost:5002) in your browser.

## Running Tests
```sh
pytest tests/*
```

## Folder Structure
- `myapp/` - Main application package
  - `auth/` - Contains decorators.py which defines custom decorators used thoughout the Flask backend
  - `models/` - SQLAlchemy models
  - `routes/` - Flask blueprints for each role/module
  - `templates/` - Jinja2 HTML templates (divided into folders based on roles)
  - `services/` - Set of third party services used in the app
  - `static/` - Static files (CSS, JS, images)
  - `__init__.py` - Initializes the app, DB and logger
  - `config.py` - Contains configs for the app (one for normal use, another for running unit tests)
  - `utils.py` - Set of 'global' functions that are used in the backend routes
  - `uploads/` - Uploaded CVs and files
- `migrations/` - Alembic migration scripts
- `tests/` - Pytest test suite
- `requirements.txt` - List of Python modules that are needed to run the app
- `run.py` - Entry point for the app

