leave_tracker/
├── .env
├── app.py
├── config.py
├── extensions.py
├── models.py
├── forms.py
├── utils.py (for roles decorators, etc.)
├── routes/
│   ├── __init__.py
│   ├── admin.py
│   ├── auth.py
│   ├── employee.py
│   └── manager.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── manage_users.html
│   │   ├── add_edit_user.html
│   │   ├── manage_holidays.html
│   │   └── add_edit_holiday.html
│   ├── employee/
│   │   ├── dashboard.html
│   │   └── apply_leave.html
│   ├── manager/
│   │   ├── dashboard.html
│   │   └── review_leaves.html
│   ├── _flash_messages.html
│   └── _calendar_panel.html
│   └── _summary_panel.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   ├── uploads/ (for sick leave attachments)
├── migrations/ (created by Flask-Migrate)
└── README.md


Let's start building!

1. Setup Environment

Create a virtual environment and install dependencies:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install Flask Flask-SQLAlchemy Flask-Migrate Flask-Login Flask-WTF python-dotenv Werkzeug Pillow email-validator

flask db init
flask db migrate -m "initial migration"
flask db upgrade

flask db-seed # To create the admin user

# Generate the migration script in case force_password_change
flask db migrate -m "Add force_password_change flag to User model"

# Apply the migration to the database
flask db upgrade

manager@example.com
managerpassword

jomz@example.com
jomzpassword


netero@example.com
neteropassword
