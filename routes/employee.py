from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, session
from forms import LeaveApplicationForm
from models import User, Leave, LeaveStatus, LeaveType, Holiday
from extensions import db
from utils import employee_required, is_holiday_or_critical_day, allowed_file, get_leave_summary, generate_dashboard_greeting
from flask_login import login_required, current_user
import os
import uuid
import datetime
import json
from openai import AzureOpenAI

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

def suggest_leave_dates(num_days: int = 1):
    print(f"🤖 Tool called: suggest_leave_dates(num_days={num_days})")
    suggestions = []
    today = datetime.date.today()
    future_date = today + datetime.timedelta(days=365)
    company_holidays = Holiday.query.filter(Holiday.is_critical == False, Holiday.date >= today,
        Holiday.date <= today + datetime.timedelta(days=90), Holiday.date.between(today, future_date)).all()
    for i in range(365):
        current_date = today + datetime.timedelta(days=i)
        if current_date.weekday() == 0 and current_date in company_holidays:
            leave_date = current_date - datetime.timedelta(days=3)
            if leave_date > today:
                suggestions.append({
                    "leave_date": leave_date.isoformat(), "holiday_date": current_date.isoformat(),
                    "reason": f"Take Friday off for a 4-day weekend holiday on Monday."
                })
        if current_date.weekday() == 4 and current_date in company_holidays:
            leave_date = current_date + datetime.timedelta(days=3)
            if leave_date > today:
                suggestions.append({
                    "leave_date": leave_date.isoformat(), "holiday_date": current_date.isoformat(),
                    "reason": f"Take Monday off for a 4-day weekend holiday on Friday."
                })
    if not suggestions:
        return json.dumps({"message": "I couldn't find any upcoming long weekend opportunities."})
    return json.dumps(suggestions[0])

def file_leave(start_date: str, end_date: str):
    print(f"🤖 Tool called: file_leave(start_date='{start_date}', end_date='{end_date}')")
    try:
        leave = Leave(
            user_id=current_user.id, 
            leave_type=LeaveType.VACATION.name,
            start_date=datetime.date.fromisoformat(start_date),
            end_date=datetime.date.fromisoformat(end_date),
            reason='Vacation leave filed by Leavy Chatbot',
        )
        db.session.add(leave)
        db.session.commit()
        return json.dumps({"status": "success", "message": f"Leave from {start_date} to {end_date} has been filed."})
    except Exception as e:
        print(f"❌ Error filing leave: {e}")
        return json.dumps({"status": "error", "message": "There was an error filing your leave."})

def file_sick_leave(reason: str):
    TODAY = datetime.date.today()
    today_str = TODAY.isoformat()
    print(f"🤖 Tool called: file_sick_leave(reason='{reason}') for date {today_str}")
    try:
        leave = Leave(
            user_id=current_user.id,
            leave_type=LeaveType.SICK.name,
            start_date=TODAY,
            end_date=TODAY,
            reason=reason,
        )
        db.session.add(leave)
        db.session.commit()
        return json.dumps({
            "status": "success",
            "message": f"Sick leave for {today_str} has been filed. Reason: {reason}"
        })
    except Exception as e:
        print(f"❌ Error filing sick leave: {e}")
        return json.dumps({"status": "error", "message": "There was an error filing your sick leave."})

available_functions = {
    "suggest_leave_dates": suggest_leave_dates,
    "file_leave": file_leave,
    "file_sick_leave": file_sick_leave,
}

# Helper to initialize history
def get_history(system_prompt):
    if "messages" not in session:
        session["messages"] = [
            {"role": "system", "content": system_prompt}
        ]
    return session["messages"]

def save_history(messages):
    session["messages"] = messages

# Convert assistant message with tool calls into a pure dict for safe storage
def to_assistant_dict(msg):
    out = {"role": "assistant", "content": msg.content}
    if getattr(msg, "tool_calls", None):
        out["tool_calls"] = []
        for tc in msg.tool_calls:
            out["tool_calls"].append({
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            })
    return out

# THIS SECTION REMAINS UNCHANGED
tools = [
    {
        "type": "function",
        "function": {
            "name": "suggest_leave_dates",
            "description": "Suggests an optimal date to file for a VACATION leave to create a long weekend.",
            "parameters": {"type": "object", "properties": {"num_days": {"type": "integer", "description": "The number of leave days the user wants to take.", "default": 1}}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_leave",
            "description": "Files the user's VACATION leave request in the system for one or more specified dates.",
            "parameters": {"type": "object", "properties": {"start_date": {"type": "string", "description": "The start date of the leave in YYYY-MM-DD format."}, "end_date": {"type": "string", "description": "The end date of the leave in YYYY-MM-DD format. Same as start_date if it's a single day."}}, "required": ["start_date", "end_date"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_sick_leave",
            "description": "Files a SICK leave for the current day after the user has confirmed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "The user's stated reason for being sick, e.g., 'not feeling well', 'have a fever'.",
                    },
                },
                "required": ["reason"],
            },
        },
    }
]

@employee_bp.route('/chat', methods=['POST'])
@login_required
@employee_required
def chat():
    try:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        subscription_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
 
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=subscription_key,
            api_version=api_version,
        )

        # Get context from our application's database
        today = datetime.date.today()
        future_date = today + datetime.timedelta(days=365)
        company_holidays = Holiday.query.filter(Holiday.is_critical == False, Holiday.date.between(today, future_date)).all()
        company_critical_days = Holiday.query.filter(Holiday.is_critical == True, Holiday.date.between(today, future_date)).all()

        system_prompt = f"""
        You are 'Leavy', a friendly and brilliant AI assistant integrated into a company's Leave Tracker app.
        You have two expert personas you must embody:

        1.  **Expert HR Leave Planner:** When asked about leave schedules, filing dates, or long weekends, you MUST use the provided company data. Your goal is to help employees maximize their vacation time by identifying strategic days to take leave.
        2.  **Inspirational Travel Advisor:** When asked for vacation ideas, destinations, or travel tips, you should provide creative and helpful suggestions specifically for travel within the Philippines.

        **CONTEXT FOR YOUR HR PERSONA:**
        "- Today's Date: {today.strftime('%Y-%m-%d')}"
        "- Company Holidays (LEAVE IS NOT ALLOWED) (days off): {', '.join([f'{h.name} on {h.date.strftime("%Y-%m-%d")}' for h in company_holidays]) or 'None provided.'}"
        "- Company Critical Days (LEAVE IS NOT ALLOWED): {', '.join([f'{c.name} on {c.date.strftime("%Y-%m-%d")}' for c in company_critical_days]) or 'None provided.'}"

        "Your workflows are:\n"
            "1. **Vacation Leave**: If the user wants vacation, FIRST use `suggest_leave_dates`. PRESENT the suggestion and ask for confirmation. After confirmation, use `file_leave`.\n"
            "2. **Sick Leave**: If the user says they are sick, FIRST **ask for confirmation** before filing. After they confirm, use the `file_sick_leave` tool for today's date."

        **INSTRUCTIONS:**
        - Always respond in a friendly, conversational, and encouraging tone.
        - Use Markdown for formatting (headings, lists, bold text) to make your answers easy to read.
        - Keep responses concise and to the point.
        - Infer the user's intent to decide which persona to use. If they ask "Where and when should I take a vacation?", use BOTH personas.
        """
        user_input = request.json.get("message", "").strip()
        if not user_input:
            return jsonify({"error": "Empty message"}), 400
        
        # 1) Load history and append current user turn
        messages = get_history(system_prompt)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_input}
            ]
        })
        
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            tools=tools,
            tool_choice="auto",
            top_p=0.95
        )

        response_message = completion.choices[0].message
        
        # 3) If the model decided to call tools
        if getattr(response_message, "tool_calls", None):
            # Store the assistant turn with its tool_calls
            messages.append(to_assistant_dict(response_message))

            # Execute tools and add tool results to history
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions.get(function_name)
                if not function_to_call:
                    # If unknown tool, tell the model
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps({"error": "Unknown function"})
                    })
                    continue

                try:
                    function_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    function_args = {}

                function_response = function_to_call(**function_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": function_response
                })

            # 4) Ask the model to produce the final assistant message after tool outputs
            second_response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )
            final_assistant = second_response.choices[0].message
            final_message = final_assistant.content
            messages.append({"role": "assistant", "content": final_message})

        else:
            # No tool calls — just a normal assistant reply
            final_message = response_message.content
            messages.append({"role": "assistant", "content": final_message})

        # 5) Persist history so the next "Yes" is in context
        save_history(messages)

        return jsonify({"reply": final_message})

    except Exception as e:
        print(f"Error in /chat route: {e}")
        return jsonify({"error": "Sorry, I'm having trouble connecting to my brain right now. Please try again in a moment."}), 500