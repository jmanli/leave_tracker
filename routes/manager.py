from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from models import Leave, LeaveStatus, Holiday
from extensions import db
from utils import manager_required, get_team_leave_summary, generate_dashboard_greeting
from flask_login import login_required, current_user
import datetime
import csv
from io import StringIO
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

@manager_bp.route('/export_team_leaves')
@login_required
@manager_required
def export_team_leaves():
    """
    Display team leave data in a table format with optional filtering by date range
    Query parameters:
    - filter_type: 'all', 'week', 'month', 'year', 'custom'
    - start_date: YYYY-MM-DD (for custom filter)
    - end_date: YYYY-MM-DD (for custom filter)
    - status: 'all', 'PENDING', 'APPROVED', 'REJECTED'
    - format: 'html' (default) or 'csv' (for download)
    """
    try:
        # Get filter parameters
        filter_type = request.args.get('filter_type', 'all')
        status_filter = request.args.get('status', 'all')
        custom_start = request.args.get('start_date')
        custom_end = request.args.get('end_date')
        export_format = request.args.get('format', 'html')
        
        # Get managed employees
        managed_employee_ids = [emp.id for emp in current_user.managed_employees.all()]
        
        # Base query
        query = Leave.query.filter(Leave.user_id.in_(managed_employee_ids))
        
        # Apply status filter
        if status_filter and status_filter != 'all':
            try:
                status_enum = LeaveStatus[status_filter]
                query = query.filter(Leave.status == status_enum)
            except KeyError:
                pass
        
        # Apply date filter
        today = datetime.date.today()
        start_date = None
        end_date = None
        filter_description = "All Time"
        
        if filter_type == 'week':
            # Current week (Monday to Sunday)
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = start_date + datetime.timedelta(days=6)
            filter_description = f"This Week ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')})"
        elif filter_type == 'month':
            # Current month
            start_date = today.replace(day=1)
            # Last day of current month
            if today.month == 12:
                end_date = today.replace(day=31)
            else:
                end_date = (today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1))
            filter_description = f"This Month ({today.strftime('%B %Y')})"
        elif filter_type == 'year':
            # Current year
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
            filter_description = f"This Year ({today.year})"
        elif filter_type == 'custom' and custom_start and custom_end:
            # Custom date range
            try:
                start_date = datetime.datetime.strptime(custom_start, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(custom_end, '%Y-%m-%d').date()
                filter_description = f"Custom ({start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')})"
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return redirect(url_for('manager.dashboard'))
        
        # Apply date range filter if specified
        if start_date and end_date:
            query = query.filter(Leave.start_date <= end_date, Leave.end_date >= start_date)
        
        # Order by date
        leaves = query.order_by(Leave.start_date.desc()).all()
        
        # If CSV format is requested, generate CSV download
        if export_format == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Employee Name',
                'Employee Email',
                'Leave Type',
                'Start Date',
                'End Date',
                'Days',
                'Status',
                'Reason',
                'Applied At',
                'Approved/Rejected By',
                'Approved/Rejected At',
                'Rejection Reason',
                'Document Attached'
            ])
            
            # Write data rows
            for leave in leaves:
                days = (leave.end_date - leave.start_date).days + 1
                approver_name = leave.approver.name if leave.approver else 'N/A'
                applied_at = leave.applied_at.strftime('%Y-%m-%d %H:%M') if leave.applied_at else 'N/A'
                approved_at = leave.approved_at.strftime('%Y-%m-%d %H:%M') if leave.approved_at else 'N/A'
                
                writer.writerow([
                    leave.employee.name,
                    leave.employee.email,
                    leave.leave_type.value,
                    leave.start_date.strftime('%Y-%m-%d'),
                    leave.end_date.strftime('%Y-%m-%d'),
                    days,
                    leave.status.value,
                    leave.reason or 'N/A',
                    applied_at,
                    approver_name,
                    approved_at,
                    leave.rejection_reason or 'N/A',
                    'Yes' if leave.document_path else 'No'
                ])
            
            output.seek(0)
            filename = f"team_leaves_{current_user.name.replace(' ', '_')}_{filter_type}"
            if start_date and end_date:
                filename += f"_{start_date}_{end_date}"
            filename += f"_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename={filename}'}
            )
        
        # Otherwise, render HTML page
        return render_template('manager/team_leaves_report.html',
                             leaves=leaves,
                             filter_type=filter_type,
                             filter_description=filter_description,
                             status_filter=status_filter,
                             start_date=start_date,
                             end_date=end_date,
                             LeaveStatus=LeaveStatus,
                             title='Team Leaves Report')
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('manager.dashboard'))