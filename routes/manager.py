from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from models import Leave, LeaveStatus, Holiday
from extensions import db
from utils import manager_required, get_team_leave_summary, generate_dashboard_greeting
from flask_login import login_required, current_user
import datetime
from forms import RejectLeaveForm

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/dashboard')
@login_required
@manager_required
def dashboard():
    # Only show leaves of employees managed by this manager
    managed_employee_ids = [emp.id for emp in current_user.managed_employees.all()]
    
    pending_leaves = Leave.query.filter(
        Leave.user_id.in_(managed_employee_ids),
        Leave.status == LeaveStatus.PENDING
    ).order_by(Leave.applied_at.asc()).all()

    recent_approved_rejected_leaves = Leave.query.filter(
        Leave.user_id.in_(managed_employee_ids),
        Leave.status.in_([LeaveStatus.APPROVED, LeaveStatus.REJECTED])
    ).order_by(Leave.approved_at.desc()).limit(10).all()

    team_summary = get_team_leave_summary(current_user)
    greeting_data = generate_dashboard_greeting(current_user)

    return render_template('manager/dashboard.html', 
                           pending_leaves=pending_leaves, 
                           recent_leaves=recent_approved_rejected_leaves,
                           team_summary=team_summary,
                           greeting_data=greeting_data,
                           LeaveStatus=LeaveStatus,
                           title='Manager Dashboard')

@manager_bp.route('/leaves/approve/<int:leave_id>', methods=['POST'])
@login_required
@manager_required
def approve_leave(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    # Ensure manager has authority over this employee's leave
    if leave.employee.manager_id != current_user.id:
        flash('You are not authorized to approve this leave.', 'danger')
        return redirect(url_for('manager.dashboard'))

    leave.status = LeaveStatus.APPROVED
    leave.approved_by_id = current_user.id
    leave.approved_at = datetime.datetime.utcnow()
    db.session.commit()
    flash(f'Leave for {leave.employee.name} approved.', 'success')
    return redirect(url_for('manager.dashboard'))

@manager_bp.route('/leaves/reject/<int:leave_id>', methods=['GET', 'POST'])
@login_required
@manager_required
def reject_leave(leave_id):
    leave = Leave.query.get_or_404(leave_id)
    # Ensure manager has authority over this employee's leave
    if leave.employee.manager_id != current_user.id:
        flash('You are not authorized to reject this leave.', 'danger')
        return redirect(url_for('manager.dashboard'))

    form = RejectLeaveForm()
    if form.validate_on_submit():
        leave.status = LeaveStatus.REJECTED
        leave.approved_by_id = current_user.id # Still marks who took action
        leave.approved_at = datetime.datetime.utcnow() # Time of action
        leave.rejection_reason = form.rejection_reason.data
        db.session.commit()
        flash(f'Leave for {leave.employee.name} rejected.', 'success')
        return redirect(url_for('manager.dashboard'))
    
    return render_template('manager/review_leaves.html', leave=leave, form=form, title='Reject Leave')


@manager_bp.route('/get_team_leaves_for_calendar')
@login_required
@manager_required
def get_team_leaves_for_calendar():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    start_date = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00')).date() if start_str else None
    end_date = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00')).date() if end_str else None

    # Get leaves for employees managed by CURRENT_USER
    managed_employee_ids = [emp.id for emp in current_user.managed_employees.all()]
    
    team_leaves_query = Leave.query.filter(Leave.user_id.in_(managed_employee_ids))
    if start_date and end_date:
        team_leaves_query = team_leaves_query.filter(Leave.start_date <= end_date, Leave.end_date >= start_date)
    team_leaves = team_leaves_query.all()
    
    holidays = Holiday.query.all() # Fetch all holidays

    events = []
    for leave in team_leaves:
        color = ''
        if leave.status == LeaveStatus.APPROVED:
            color = 'green'
        elif leave.status == LeaveStatus.PENDING:
            color = 'orange'
        elif leave.status == LeaveStatus.REJECTED:
            color = 'red'
        
        events.append({
            'title': f'{leave.employee.name} - {leave.leave_type.value} ({leave.status.value})',
            'start': leave.start_date.isoformat(),
            'end': (leave.end_date + datetime.timedelta(days=1)).isoformat(), # FullCalendar end date is exclusive
            'color': color,
            'extendedProps': {
                'status': leave.status.value,
                'type': leave.leave_type.value,
                'reason': leave.reason,
                'document_path': leave.document_path,
                'is_manager_view': True,
                'leave_id': leave.id,
                'user_id': leave.user_id,
            }
        })

    # Query for holidays and critical days separately
    holidays = Holiday.query.filter_by(is_critical=False).all()
    critical_days = Holiday.query.filter_by(is_critical=True).all()

    # Loop for HOLIDAYS (days off)
    for holiday in holidays:
        events.append({
            'title': f'{holiday.name} (Holiday)',
            'start': holiday.date.isoformat(),
            'end': (holiday.date + datetime.timedelta(days=1)).isoformat(),
            'backgroundColor': '#ced4da', # A neutral grey for days off
            'borderColor': '#ced4da',
            'display': 'background',
        })

    # Loop for CRITICAL DAYS (no leave allowed)
    for day in critical_days:
        events.append({
            'title': f'{day.name} (Critical Day)',
            'start': day.date.isoformat(),
            'end': (day.date + datetime.timedelta(days=1)).isoformat(),
            'backgroundColor': '#f8d7da', # A light, cautionary red
            'borderColor': '#f8d7da',
            'display': 'background',
        })

    return jsonify(events)