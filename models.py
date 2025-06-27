from datetime import datetime
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import enum

class UserRole(enum.Enum):
    ADMIN = 'Admin'
    MANAGER = 'Manager'
    EMPLOYEE = 'Employee'

class LeaveStatus(enum.Enum):
    PENDING = 'Pending'
    APPROVED = 'Approved'
    REJECTED = 'Rejected'

class LeaveType(enum.Enum):
    VACATION = 'Vacation'
    SICK = 'Sick Leave'
    BEREAVEMENT = 'Bereavement'
    UNPAID = 'Unpaid Leave'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Self-referencing
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    managed_employees = db.relationship('User', backref=db.backref('manager', remote_side=[id]), lazy='dynamic', foreign_keys=[manager_id])
    leaves_applied = db.relationship('Leave', backref='employee', lazy='dynamic', foreign_keys='Leave.user_id')
    leaves_approved = db.relationship('Leave', backref='approver', lazy='dynamic', foreign_keys='Leave.approved_by_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_manager(self):
        return self.role == UserRole.MANAGER

    def is_employee(self):
        return self.role == UserRole.EMPLOYEE

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(db.Enum(LeaveType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(LeaveStatus), nullable=False, default=LeaveStatus.PENDING)
    reason = db.Column(db.Text, nullable=True)
    document_path = db.Column(db.String(255), nullable=True) # Path to attached file
    applied_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Leave {self.id} for {self.employee.name} ({self.start_date} to {self.end_date}) - {self.status.value}>"

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_critical = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Holiday {self.name} on {self.date}>"