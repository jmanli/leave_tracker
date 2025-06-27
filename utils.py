from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from models import UserRole, Holiday
import datetime

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            if not current_user.role == role:
                flash(f"You do not have the required '{role.value}' role to access this page.", "danger")
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required(UserRole.ADMIN)
manager_required = role_required(UserRole.MANAGER)
employee_required = role_required(UserRole.EMPLOYEE) # Or you can add specific ones if needed

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def is_holiday_or_critical_day(date_obj):
    """Checks if a given date is a holiday or critical day."""
    return Holiday.query.filter_by(date=date_obj).first() is not None

def get_leave_summary(user, month=None, year=None):
    from models import Leave, LeaveStatus, LeaveType
    from sqlalchemy import func

    # Base query for leaves by user
    query = Leave.query.filter_by(user_id=user.id)

    # Filter by year if specified
    if year:
        query = query.filter(func.strftime('%Y', Leave.start_date) == str(year))

    # Filter by month if specified
    if month:
        query = query.filter(func.strftime('%m', Leave.start_date) == f'{month:02d}')

    leaves = query.all()

    # Initialize summary
    summary = {
        'total_leaves_month': 0,
        'total_leaves_year': 0,
        'leaves_ytd_approved': 0,
        'leaves_ytd_less_sl': 0,
        'vl_ytd': 0,
        'sl_ytd': 0,
        'pending_leaves_count': 0,
    }

    current_date = datetime.date.today()
    current_year = current_date.year
    current_month = current_date.month

    for leave in user.leaves_applied: # Iterate over all applied leaves of the user
        # Check if the leave falls within the current month (for 'Leaves This Month')
        if leave.start_date.month == current_month and leave.start_date.year == current_year:
            summary['total_leaves_month'] += (leave.end_date - leave.start_date).days + 1

        # Check if the leave falls within the current year (for 'Leaves this Year', VLs YTD, SLs YTD)
        if leave.start_date.year == current_year:
            summary['total_leaves_year'] += (leave.end_date - leave.start_date).days + 1
            if leave.status == LeaveStatus.PENDING:
                summary['pending_leaves_count'] += (leave.end_date - leave.start_date).days + 1

            # Leaves Year to Date (approved consumed already)
            # This is tricky without a specific column for 'consumed'. For simplicity, we'll count approved leaves starting before or on today.
            if leave.status == LeaveStatus.APPROVED and leave.start_date <= current_date:
                summary['leaves_ytd_approved'] += (leave.end_date - leave.start_date).days + 1

            # Leaves this current year less SL (includes unapproved and approved leaves without the SL total)
            if leave.leave_type != LeaveType.SICK:
                summary['leaves_ytd_less_sl'] += (leave.end_date - leave.start_date).days + 1

            # VLs YTD
            if leave.leave_type == LeaveType.VACATION:
                summary['vl_ytd'] += (leave.end_date - leave.start_date).days + 1

            # SLs YTD
            if leave.leave_type == LeaveType.SICK:
                summary['sl_ytd'] += (leave.end_date - leave.start_date).days + 1
    
    return summary

def get_team_leave_summary(manager):
    from models import Leave, LeaveStatus, LeaveType
    from sqlalchemy import func

    team_members = manager.managed_employees.all()
    team_leaves = Leave.query.filter(Leave.user_id.in_([emp.id for emp in team_members])).all()

    summary = {
        'total_team_leaves_month': 0,
        'total_team_leaves_year': 0,
        'team_pending_leaves_count': 0,
        'team_approved_leaves_count': 0,
        'team_vl_ytd': 0,
        'team_sl_ytd': 0,
    }

    current_date = datetime.date.today()
    current_year = current_date.year
    current_month = current_date.month

    for leave in team_leaves:
        days = (leave.end_date - leave.start_date).days + 1

        if leave.start_date.month == current_month and leave.start_date.year == current_year:
            summary['total_team_leaves_month'] += days

        if leave.start_date.year == current_year:
            summary['total_team_leaves_year'] += days
            if leave.status == LeaveStatus.PENDING:
                summary['team_pending_leaves_count'] += days
            elif leave.status == LeaveStatus.APPROVED:
                summary['team_approved_leaves_count'] += days
            
            if leave.leave_type == LeaveType.VACATION:
                summary['team_vl_ytd'] += days
            elif leave.leave_type == LeaveType.SICK:
                summary['team_sl_ytd'] += days
                
    return summary

def generate_dashboard_greeting(user):
    # 
    # Generates a personalized greeting message for the dashboard,
    # including information about upcoming holidays.
    # 
    today = datetime.date.today()
    greeting = f"Welcome back, {user.name.split()[0]}!" # Greet by first name

    # Find the next 2 upcoming holidays within the next 90 days
    upcoming_holidays = Holiday.query.filter(
        Holiday.is_critical == False, 
        Holiday.date >= today,
        Holiday.date <= today + datetime.timedelta(days=90)
    ).order_by(Holiday.date.asc()).limit(2).all()

    holiday_message = ""
    if not upcoming_holidays:
        holiday_message = "No holidays in the next 90 days. Keep up the great work!"
    elif len(upcoming_holidays) == 1:
        # This part is already correct and handles the 'today' case for a single holiday
        holiday = upcoming_holidays[0]
        days_until = (holiday.date - today).days
        if days_until == 0:
            holiday_message = f"Just a heads up, today is {holiday.name}!"
        elif days_until == 1:
            holiday_message = f"Don't forget, {holiday.name} is tomorrow!"
        else:
            holiday_message = f"Looking ahead, {holiday.name} is coming up in {days_until} days on {holiday.date.strftime('%B %d')}. "
            if holiday.is_critical:
                holiday_message += "This is marked as a critical day, so plan accordingly."
                
    else: # We have 2 or more holidays. THIS IS THE BLOCK TO MODIFY.
        holiday1 = upcoming_holidays[0]
        holiday2 = upcoming_holidays[1]
        days_until1 = (holiday1.date - today).days

        # --- START: NEW LOGIC ---
        # Part 1 of the message, handling the 'today' case
        if days_until1 == 0:
            first_holiday_part = f"The next holiday is {holiday1.name}, which is today!"
        elif days_until1 == 1:
            first_holiday_part = f"The next holiday is {holiday1.name}, which is tomorrow."
        else:
            first_holiday_part = f"The next holiday is {holiday1.name} in {days_until1} days."
        
        # Part 2 of the message is always the same
        second_holiday_part = f"After that, we have {holiday2.name} on {holiday2.date.strftime('%B %d')}."

        # Combine the parts
        holiday_message = f"{first_holiday_part} {second_holiday_part}"
        # --- END: NEW LOGIC ---

    return {
        'greeting': greeting,
        'holiday_message': holiday_message
    }