from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from forms import LeaveApplicationForm
from models import User, Leave, LeaveStatus, LeaveType, Holiday
from extensions import db
from utils import employee_required, is_holiday_or_critical_day, allowed_file, get_leave_summary, generate_dashboard_greeting
from flask_login import login_required, current_user
import os
import uuid
import datetime
import openai

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@login_required
@employee_required
def dashboard():
    my_leaves = current_user.leaves_applied.order_by(Leave.start_date.desc()).limit(10).all()
    
    # Get team leaves (for employees under the same manager)
    team_leaves = []
    if current_user.manager: # if current user has a manager
        # Get all employees under the same manager, excluding current user
        team_members = current_user.manager.managed_employees.filter(
            User.id != current_user.id
        ).all()
        
        # Get leaves for those team members
        if team_members:
            team_member_ids = [member.id for member in team_members]
            team_leaves = Leave.query.filter(
                Leave.user_id.in_(team_member_ids)
            ).order_by(Leave.start_date.desc()).limit(10).all()
            
    summary = get_leave_summary(current_user)
    
    greeting_data = generate_dashboard_greeting(current_user)

    return render_template('employee/dashboard.html', 
                           my_leaves=my_leaves, 
                           team_leaves=team_leaves, 
                           summary=summary,
                           greeting_data=greeting_data,
                           LeaveStatus=LeaveStatus,
                           title='Employee Dashboard')

@employee_bp.route('/leaves/apply', methods=['GET', 'POST'])
@login_required
@employee_required
def apply_leave():
    form = LeaveApplicationForm()
    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data

        if start_date > end_date:
            flash('End Date cannot be before Start Date.', 'danger')
            return render_template('employee/apply_leave.html', form=form, title='Apply for Leave')

        # Check for holidays/critical days
        current_date = start_date
        while current_date <= end_date:
            if is_holiday_or_critical_day(current_date):
                holiday = Holiday.query.filter_by(date=current_date).first()
                flash(f'Cannot apply for leave on {current_date.strftime("%Y-%m-%d")} which is a {holiday.name} ({ "Critical Day" if holiday.is_critical else "Holiday"}).', 'danger')
                return render_template('employee/apply_leave.html', form=form, title='Apply for Leave')
            current_date += datetime.timedelta(days=1)
        
        document_path = None
        if form.leave_type.data == LeaveType.SICK.name and form.document.data:
            file = form.document.data
            if file and allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                document_path = filename # Store only the path relative to UPLOAD_FOLDER
            else:
                flash('Invalid file type for attachment.', 'danger')
                return render_template('employee/apply_leave.html', form=form, title='Apply for Leave')
        elif form.leave_type.data == LeaveType.SICK.name and not form.document.data:
            flash('Sick Leave requires an attachment.', 'danger')
            # You might want to make the document field required via WTForms validator dynamically
            return render_template('employee/apply_leave.html', form=form, title='Apply for Leave')


        leave = Leave(
            user_id=current_user.id,
            leave_type=LeaveType[form.leave_type.data],
            start_date=start_date,
            end_date=end_date,
            reason=form.reason.data,
            document_path=document_path
        )
        db.session.add(leave)
        db.session.commit()
        flash('Leave application submitted successfully!', 'success')
        return redirect(url_for('employee.dashboard'))

    return render_template('employee/apply_leave.html', form=form, title='Apply for Leave')


@employee_bp.route('/get_leaves_for_calendar')
@login_required
@employee_required
def get_leaves_for_calendar():
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    start_date = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00')).date() if start_str else None
    end_date = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00')).date() if end_str else None

    # Get my leaves
    my_leaves_query = current_user.leaves_applied
    if start_date and end_date:
        my_leaves_query = my_leaves_query.filter(Leave.start_date <= end_date, Leave.end_date >= start_date)
    my_leaves = my_leaves_query.all()

    # Get team leaves (similar logic as dashboard)
    team_leaves = []
    if current_user.manager:
        team_member_ids = [member.id for member in current_user.manager.managed_employees.all() if member.id != current_user.id]
        if team_member_ids:
            team_leaves_query = Leave.query.filter(Leave.user_id.in_(team_member_ids))
            if start_date and end_date:
                team_leaves_query = team_leaves_query.filter(Leave.start_date <= end_date, Leave.end_date >= start_date)
            team_leaves = team_leaves_query.all()
    
    holidays = Holiday.query.all() # Fetch all holidays

    events = []
    for leave in my_leaves:
        color = ''
        if leave.status == LeaveStatus.APPROVED:
            color = 'green'
        elif leave.status == LeaveStatus.PENDING:
            color = 'orange' # Or yellow
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
                'is_mine': True
            }
        })
    
    for leave in team_leaves:
        color = ''
        if leave.status == LeaveStatus.APPROVED:
            color = '#87CEEB' # light blue for team approved
        elif leave.status == LeaveStatus.PENDING:
            color = '#ADD8E6' # lighter blue for team pending
        elif leave.status == LeaveStatus.REJECTED:
            color = '#FFB6C1' # light red for team rejected
        
        events.append({
            'title': f'{leave.employee.name} - {leave.leave_type.value}',
            'start': leave.start_date.isoformat(),
            'end': (leave.end_date + datetime.timedelta(days=1)).isoformat(), # FullCalendar end date is exclusive
            'color': color,
            'extendedProps': {
                'status': leave.status.value,
                'type': leave.leave_type.value,
                'reason': leave.reason,
                'document_path': leave.document_path,
                'is_mine': False
            }
        })

     # Query for holidays and critical days separately
    holidays = Holiday.query.filter_by(is_critical=False).all()
    critical_days = Holiday.query.filter_by(is_critical=True).all()

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

@employee_bp.route('/chat', methods=['POST'])
@login_required
@employee_required
def chat():
    """Handles chat requests, calls the GenAI, and returns a response."""
    data = request.json
    user_message = data.get('message')
    chat_history = data.get('history', [])

    if not user_message:
        return jsonify({"error": "No message provided."}), 400

    try:
        # --- The core logic is to build a good prompt ---
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        if not openai.api_key:
            return jsonify({"error": "AI assistant is not configured."}), 500

        # Get context from our application's database
        today = datetime.date.today()
        future_date = today + datetime.timedelta(days=180)
        company_holidays = Holiday.query.filter(Holiday.is_critical == False, Holiday.date.between(today, future_date)).all()
        company_critical_days = Holiday.query.filter(Holiday.is_critical == True, Holiday.date.between(today, future_date)).all()

        # This is our powerful system prompt that defines the AI's persona
        system_prompt = f"""
        You are 'Leavy', a friendly and brilliant AI assistant integrated into a company's Leave Tracker app.
        You have two expert personas you must embody:

        1.  **Expert HR Leave Planner:** When asked about leave schedules, filing dates, or long weekends, you MUST use the provided company data. Your goal is to help employees maximize their vacation time by identifying strategic days to take leave.
        2.  **Inspirational Travel Advisor:** When asked for vacation ideas, destinations, or travel tips, you should provide creative and helpful suggestions specifically for travel within the Philippines.

        **CONTEXT FOR YOUR HR PERSONA:**
        - Today's Date: {today.strftime('%Y-%m-%d')}
        - Company Holidays (days off): {', '.join([f'{h.name} on {h.date.strftime("%Y-%m-%d")}' for h in company_holidays]) or 'None provided.'}
        - Company Critical Days (LEAVE IS NOT ALLOWED): {', '.join([f'{c.name} on {c.date.strftime("%Y-%m-%d")}' for c in company_critical_days]) or 'None provided.'}
        - You ALSO know about all official Philippine public holidays.

        **INSTRUCTIONS:**
        - Always respond in a friendly, conversational, and encouraging tone.
        - Use Markdown for formatting (headings, lists, bold text) to make your answers easy to read.
        - Keep responses concise and to the point.
        - Infer the user's intent to decide which persona to use. If they ask "Where and when should I take a vacation?", use BOTH personas.
        """

        # Construct the message history for the API call
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        messages.append({"role": "user", "content": user_message})

        # Call the API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )

        ai_reply = response.choices[0].message.content
        return jsonify({"reply": ai_reply})

    except Exception as e:
        print(f"Error in /chat route: {e}")
        return jsonify({"error": "Sorry, I'm having trouble connecting to my brain right now. Please try again in a moment."}), 500