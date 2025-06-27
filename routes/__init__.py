from flask import Blueprint, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_manager():
            return redirect(url_for('manager.dashboard'))
        else: # Employee
            return redirect(url_for('employee.dashboard'))
    return redirect(url_for('auth.login'))