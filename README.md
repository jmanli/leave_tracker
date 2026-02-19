# Leave Tracker Application

A comprehensive Flask-based leave management system for managing employee leave requests, approvals, and holiday tracking.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Dependencies](#dependencies)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Default Admin Credentials](#default-admin-credentials)
- [User Roles](#user-roles)
- [Project Structure](#project-structure)
- [Usage Guide](#usage-guide)
- [Environment Variables](#environment-variables)
- [File Uploads](#file-uploads)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## Overview

The Leave Tracker Application is a web-based system built with Flask that enables organizations to manage employee leave requests efficiently. It supports multiple user roles (Admin, Manager, Employee) and provides features for leave application, approval workflows, holiday management, and reporting.

## Features

### Admin Features
- User management (create, edit, delete users)
- Assign managers to employees
- Holiday management (add, edit, delete holidays)
- Mark critical holidays
- View all leave requests across the organization
- Role-based access control

### Manager Features
- Review and approve/reject leave requests from team members
- View team leave calendar
- Access leave summaries and statistics
- View team member leave history

### Employee Features
- Apply for different types of leave (Vacation, Sick Leave, Bereavement, Unpaid Leave)
- **AI-Powered Chatbot Assistant ("Leavy")** - Interactive chatbot for leave planning and filing:
  - Smart leave date suggestions based on company holidays and critical days
  - Maximize vacation time by identifying strategic leave opportunities
  - Travel recommendations and destination ideas within the Philippines
  - Conversational leave filing through natural language
  - Quick sick leave filing with simple confirmation
  - Context-aware assistance using real company holiday data
- Upload supporting documents
- View leave application history
- Check leave status (Pending, Approved, Rejected)
- View personal leave calendar
- View holiday calendar

### General Features
- Secure authentication system
- Forced password change on first login
- Calendar view of leaves and holidays
- Leave status tracking
- Document attachment support
- Responsive web interface
- Flash message notifications
- AI-powered chatbot integration (Azure OpenAI) for intelligent leave planning

## System Requirements

- Python 3.7 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- SQLite (included) or PostgreSQL/MySQL (optional)

## Dependencies

The application requires the following Python packages:

### Core Framework
- **Flask** (^2.3.0) - Web framework
- **Flask-SQLAlchemy** (^3.0.0) - ORM for database operations
- **Flask-Migrate** (^4.0.0) - Database migration management
- **Flask-Login** (^0.6.2) - User session management

### Security
- **Werkzeug** (^2.3.0) - Password hashing and security utilities

### Environment Management
- **python-dotenv** (^1.0.0) - Load environment variables from .env file

### AI Integration
- **openai** (^1.12.0) - Azure OpenAI integration for chatbot functionality
- **email-validator** (^2.1.0) - Email validation for forms

### Optional (for production)
- **gunicorn** - WSGI HTTP server for production deployment
- **psycopg2-binary** - PostgreSQL adapter (if using PostgreSQL)
- **pymysql** - MySQL adapter (if using MySQL)

## Installation

### Step 1: Clone or Download the Repository

```bash
# If using git
git clone <repository-url>
cd leave_tracker

# Or extract the project files to a directory
cd leave_tracker
```

### Step 2: Create a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

Create a `requirements.txt` file with the following content:

```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Migrate==4.0.5
Flask-Login==0.6.2
Flask-WTF==1.2.1
WTForms==3.1.2
python-dotenv==1.0.0
Werkzeug==2.3.7
email-validator==2.1.0
openai==1.12.0
```

Then install the dependencies:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login python-dotenv Werkzeug
```

### Step 4: Create Environment Configuration

Create a `.env` file in the project root directory:

```env
# Application Configuration
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_APP=app.py
FLASK_ENV=development

# Database Configuration
DATABASE_URL=sqlite:///site.db

# Upload Configuration
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16000000

# Azure OpenAI Configuration (for chatbot)
AZURE_OPENAI_ENDPOINT=your-azure-endpoint-here
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

**Important:** Replace `your-secret-key-here-change-in-production` with a strong, random secret key. You can generate one using:

```python
python -c "import secrets; print(secrets.token_hex(32))"
```

## Configuration

The application configuration is managed through the `config.py` file and environment variables:

| Configuration | Description | Default Value |
|--------------|-------------|---------------|
| `SECRET_KEY` | Secret key for session management | Required (set in .env) |
| `DATABASE_URL` | Database connection URI | `sqlite:///site.db` |
| `UPLOAD_FOLDER` | Directory for uploaded files | `static/uploads` |
| `MAX_CONTENT_LENGTH` | Maximum file upload size (bytes) | `16000000` (16 MB) |
| `ALLOWED_EXTENSIONS` | Allowed file extensions | `txt, pdf, png, jpg, jpeg, gif` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | Required for chatbot |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name | Required for chatbot |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Required for chatbot |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | `2025-01-01-preview` |

## Database Setup

### Step 1: Initialize the Database

```bash
flask db init
```

This creates the `migrations` folder for database version control.

### Step 2: Create Migration

```bash
flask db migrate -m "Initial migration"
```

This generates the initial database schema based on your models.

### Step 3: Apply Migration

```bash
flask db upgrade
```

This creates the database tables.

### Step 4: Seed the Database with Admin User

```bash
flask db-seed
```

This creates a default admin user with the following credentials:
- **Email:** admin@example.com
- **Password:** adminpassword

**IMPORTANT:** Change the default admin password immediately after first login!

## Running the Application

### Development Mode

```bash
python app.py
```

Or using Flask's built-in command:

```bash
flask run
```

The application will be available at: `http://127.0.0.1:5000/`

### Production Mode

For production, use a production-grade WSGI server like Gunicorn:

```bash
# Install gunicorn
pip install gunicorn

# Run the application
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

## Default Admin Credentials

After running `flask db-seed`, use these credentials to log in:

- **Email:** admin@example.com
- **Password:** adminpassword

**Security Notice:** 
1. Change the admin password immediately after first login
2. Create additional admin accounts if needed
3. Never use default credentials in production

## User Roles

The application supports three user roles:

### 1. Admin
- Full system access
- User management (create, edit, delete)
- Holiday management
- View all leave requests
- No manager assignment required

### 2. Manager
- Review team members' leave requests
- Approve or reject leave applications
- View team calendar
- Must have a manager assigned (usually an Admin)
- Can apply for leave like employees

### 3. Employee
- Apply for leave
- View own leave history
- Upload supporting documents
- View personal calendar
- Must have a manager assigned for leave approval

## Project Structure

```
leave_tracker/
├── app.py                      # Application factory and entry point
├── config.py                   # Configuration settings
├── extensions.py               # Flask extensions initialization
├── models.py                   # Database models (User, Leave, Holiday)
├── forms.py                    # WTForms form definitions
├── utils.py                    # Utility functions and decorators
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── README.md                   # This file
│
├── instance/
│   └── site.db                # SQLite database (auto-generated)
│
├── migrations/                 # Database migration files
│   ├── versions/
│   └── alembic.ini
│
├── routes/                     # Application routes/blueprints
│   ├── __init__.py            # Main blueprint
│   ├── auth.py                # Authentication routes
│   ├── admin.py               # Admin routes
│   ├── employee.py            # Employee routes
│   └── manager.py             # Manager routes
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── index.html             # Home page
│   ├── login.html             # Login page
│   ├── _calendar_panel.html   # Calendar component
│   ├── _flash_messages.html   # Flash messages component
│   ├── _summary_panel.html    # Summary component
│   │
│   ├── admin/                 # Admin templates
│   │   ├── dashboard.html
│   │   ├── manage_users.html
│   │   ├── add_edit_user.html
│   │   ├── manage_holidays.html
│   │   └── add_edit_holiday.html
│   │
│   ├── auth/                  # Auth templates
│   │   └── change_password.html
│   │
│   ├── employee/              # Employee templates
│   │   ├── dashboard.html
│   │   └── apply_leave.html
│   │
│   └── manager/               # Manager templates
│       ├── dashboard.html
│       └── review_leaves.html
│
└── static/                     # Static files
    ├── css/
    │   └── style.css          # Custom styles
    ├── js/
    │   └── script.js          # Custom JavaScript
    └── uploads/               # User uploaded files
```

## Usage Guide

### For Admins

1. **Create Users:**
   - Navigate to Admin Dashboard → Manage Users
   - Click "Add New User"
   - Fill in user details (name, email, role)
   - Assign manager for employees/managers
   - System generates a temporary password
   - User must change password on first login

2. **Manage Holidays:**
   - Navigate to Admin Dashboard → Manage Holidays
   - Add public holidays
   - Mark critical holidays (affects leave calculations)
   - Edit or delete existing holidays

### For Managers

1. **Review Leave Requests:**
   - Navigate to Manager Dashboard → Review Leaves
   - View pending requests from team members
   - Approve or reject with optional comments
   - View team calendar

2. **Apply for Leave:**
   - Can apply for leave like employees
   - Their manager (or admin) approves their requests

### For Employees

1. **Apply for Leave:**
   - Navigate to Employee Dashboard → Apply Leave
   - Select leave type (Vacation, Sick, Bereavement, Unpaid)
   - Choose start and end dates
   - Provide reason
   - Optionally upload supporting document
   - Submit for manager approval

2. **View Leave Status:**
   - Check dashboard for leave status
   - View leave history
   - See upcoming holidays

3. **Use AI Chatbot ("Leavy"):**
   - Click on the chatbot icon in the employee dashboard
   - Ask questions like:
     - "When should I take leave to maximize my vacation?"
     - "Suggest the best dates for a long weekend in March"
     - "I'm sick today, file sick leave for me"
     - "Where should I travel in the Philippines?"
   - Chatbot provides personalized suggestions based on company holidays
   - Confirm leave filing directly through the chat interface

## Environment Variables

Create a `.env` file with the following variables:

```env
# Required
SECRET_KEY=your-secret-key-here

# Optional (with defaults)
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=sqlite:///site.db
UPLOAD_FOLDER=static/uploads
MAX_CONTENT_LENGTH=16000000

# Required for AI Chatbot
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

### Using PostgreSQL (Production)

```env
DATABASE_URL=postgresql://username:password@localhost:5432/leave_tracker
```

### Using MySQL

```env
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/leave_tracker
```

## File Uploads

The application supports file uploads for leave request documentation:

- **Supported Formats:** txt, pdf, png, jpg, jpeg, gif
- **Maximum Size:** 16 MB (configurable via `MAX_CONTENT_LENGTH`)
- **Storage Location:** `static/uploads/` directory
- **Naming Convention:** Files are saved with original names (ensure uniqueness in production)

**Security Recommendations:**
- Validate file types on server side
- Scan uploaded files for malware
- Store uploads outside web root in production
- Implement file size limits

## Development

### Running in Debug Mode

```bash
# Set environment variable
export FLASK_ENV=development  # Linux/Mac
set FLASK_ENV=development     # Windows CMD
$env:FLASK_ENV="development"  # Windows PowerShell

# Run the app
python app.py
```

Debug mode features:
- Auto-reload on code changes
- Detailed error pages
- Interactive debugger

### Database Migrations

When you modify models:

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Review the migration file in migrations/versions/

# Apply the migration
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Adding New Features

1. Create/modify models in `models.py`
2. Create migration: `flask db migrate -m "description"`
3. Apply migration: `flask db upgrade`
4. Add routes in appropriate blueprint
5. Create templates in `templates/`
6. Update `utils.py` for shared functionality

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'flask'`
- **Solution:** Activate virtual environment and install dependencies
  ```bash
  venv\Scripts\activate  # Windows
  pip install -r requirements.txt
  ```

**Issue:** `sqlalchemy.exc.OperationalError: no such table`
- **Solution:** Run database migrations
  ```bash
  flask db upgrade
  ```

**Issue:** `RuntimeError: The session is unavailable`
- **Solution:** Ensure SECRET_KEY is set in .env file

**Issue:** Admin user doesn't exist
- **Solution:** Run the seed command
  ```bash
  flask db-seed
  ```

**Issue:** File upload fails
- **Solution:** Check that `static/uploads/` directory exists and has write permissions
  ```bash
  mkdir static\uploads  # Windows
  mkdir -p static/uploads  # Linux/Mac
  ```

**Issue:** Port 5000 already in use
- **Solution:** Use a different port
  ```bash
  flask run --port 5001
  ```

**Issue:** Database is locked (SQLite)
- **Solution:** Close other connections or switch to PostgreSQL for production

### Logging

Enable detailed logging for debugging:

```python
# Add to app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Database Reset

To completely reset the database:

```bash
# WARNING: This deletes all data!
rm instance/site.db
flask db upgrade
flask db-seed
```

## Security Best Practices

1. **Never commit `.env` file** - Add to `.gitignore`
2. **Use strong SECRET_KEY** - Generate random keys
3. **Change default passwords** - Immediately after deployment
4. **Use HTTPS in production** - Encrypt data in transit
5. **Regular backups** - Back up database regularly
6. **Update dependencies** - Keep packages up to date
7. **Input validation** - Validate all user inputs
8. **SQL injection protection** - Use SQLAlchemy ORM (built-in protection)
9. **XSS protection** - Jinja2 auto-escapes (built-in protection)
10. **File upload validation** - Restrict file types and sizes

## Database Backup

### SQLite Backup

```bash
# Create backup
cp instance/site.db instance/site.db.backup

# Restore backup
cp instance/site.db.backup instance/site.db
```

### PostgreSQL Backup

```bash
# Backup
pg_dump leave_tracker > backup.sql

# Restore
psql leave_tracker < backup.sql
```

## Deployment

### Deploying to Production

1. **Set environment to production:**
   ```env
   FLASK_ENV=production
   SECRET_KEY=<strong-random-key>
   ```

2. **Use production database:**
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

3. **Use production server:**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
   ```

4. **Set up reverse proxy (Nginx):**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /static {
           alias /path/to/leave_tracker/static;
       }
   }
   ```

5. **Enable HTTPS with Let's Encrypt:**
   ```bash
   certbot --nginx -d yourdomain.com
   ```

## License

[Specify your license here]

## Support

For issues, questions, or contributions, please contact:
- Email: [your-email@example.com]
- Issue Tracker: [link-to-issue-tracker]

## Changelog

### Version 1.0.0 (Current)
- Initial release
- User management with roles (Admin, Manager, Employee)
- Leave application and approval workflow
- Holiday management
- Calendar view
- Document upload support
- Responsive UI
- AI-powered chatbot ("Leavy") for intelligent leave planning and filing
- Azure OpenAI integration for conversational leave assistance

---

**Last Updated:** January 29, 2026
