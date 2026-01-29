from flask import Blueprint, render_template, redirect, url_for, flash, request
from forms import UserForm, HolidayForm
from models import User, UserRole, Holiday
from extensions import db
from utils import admin_required
from flask_login import login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html', title='Admin Dashboard')

# --- User Management ---
@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users, title='Manage Users')

@admin_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserForm()
    # Make password required for new user
    form.password.validators = [v for v in form.password.validators if v is not form.password.validators[0]] + [d for d in [v for v in form.password.validators if v is not form.password.validators[0]] if isinstance(d, type(request.method == 'POST'))] # hacky way to force DataRequired
    form.password.validators.append(lambda form_field, x: form_field.data is not None and form_field.data != '' or ValidationError('Password is required'))
    
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('An account with this email already exists.', 'danger')
            return redirect(url_for('admin.add_user'))

        user = User(
            name=form.name.data,
            email=form.email.data,
            role=UserRole[form.role.data]
        )
        user.set_password(form.password.data)
        user.force_password_change = True

        if UserRole[form.role.data] == UserRole.EMPLOYEE and form.manager_id.data != 0:
            user.manager_id = form.manager_id.data
        elif UserRole[form.role.data] != UserRole.EMPLOYEE:
            user.manager_id = None # Managers/Admins don't have managers in this system

        db.session.add(user)
        db.session.commit()
        flash(f'User {user.name} added successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/add_edit_user.html', form=form, title='Add User', is_edit=False)


@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    #form.user_id = user.id # Pass user_id for validation context
    form.original_user = user
    
    # Remove DataRequired validator for password on edit, but allow if provided
    form.password.validators = [v for v in form.password.validators if not isinstance(v, type(request.method == 'POST'))] # Remove DataRequired
    form.confirm_password.validators = [v for v in form.confirm_password.validators if not isinstance(v, type(request.method == 'POST'))]


    # Re-populate manager_id choices, and remove current user from managers list if manager
    managers_list = [(0, 'None')] + [(u.id, u.name) for u in User.query.filter_by(role=UserRole.MANAGER).filter(User.id != user_id).all()]
    form.manager_id.choices = managers_list

    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.role = UserRole[form.role.data]

        if form.password.data: # Only update password if provided
            user.set_password(form.password.data)
            user.force_password_change = True
        
        if UserRole[form.role.data] == UserRole.EMPLOYEE and form.manager_id.data != 0:
            user.manager_id = form.manager_id.data
        elif UserRole[form.role.data] != UserRole.EMPLOYEE:
            user.manager_id = None
        else: # employee without a manager or manager_id set to 0
             user.manager_id = None

        db.session.commit()
        flash(f'User {user.name} updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    elif request.method == 'GET':
        form.role.data = user.role.name # Set enum value for form
        if user.manager_id:
            form.manager_id.data = user.manager_id

    return render_template('admin/add_edit_user.html', form=form, title='Edit User', is_edit=True, user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin() and User.query.filter_by(role=UserRole.ADMIN).count() == 1:
        flash("Cannot delete the last admin user.", "danger")
        return redirect(url_for('admin.manage_users'))
    
    # Import Leave model
    from models import Leave
    
    # Disassociate managed employees
    for emp in user.managed_employees:
        emp.manager_id = None
    
    # Delete all leave applications by this user
    Leave.query.filter_by(user_id=user_id).delete()
    
    # Update leaves approved by this user (set approved_by_id to None)
    Leave.query.filter_by(approved_by_id=user_id).update({Leave.approved_by_id: None})
    
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

# --- Holiday Management ---
@admin_bp.route('/holidays')
@login_required
@admin_required
def manage_holidays():
    holidays = Holiday.query.order_by(Holiday.date).all()
    return render_template('admin/manage_holidays.html', holidays=holidays, title='Manage Holidays & Critical Days')

@admin_bp.route('/holidays/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_holiday():
    form = HolidayForm()
    if form.validate_on_submit():
        holiday = Holiday(date=form.date.data, name=form.name.data, is_critical=form.is_critical.data)
        try:
            db.session.add(holiday)
            db.session.commit()
            flash(f'Holiday "{holiday.name}" added successfully!', 'success')
            return redirect(url_for('admin.manage_holidays'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding holiday: A holiday already exists on this date. {e}', 'danger')
    return render_template('admin/add_edit_holiday.html', form=form, title='Add Holiday', is_edit=False)

@admin_bp.route('/holidays/edit/<int:holiday_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    form = HolidayForm(obj=holiday)
    if form.validate_on_submit():
        try:
            holiday.date = form.date.data
            holiday.name = form.name.data
            holiday.is_critical = form.is_critical.data
            db.session.commit()
            flash(f'Holiday "{holiday.name}" updated successfully!', 'success')
            return redirect(url_for('admin.manage_holidays'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating holiday: A holiday already exists on this date. {e}', 'danger')
    elif request.method == 'GET':
        form.is_critical.data = 'True' if holiday.is_critical else 'False'
    return render_template('admin/add_edit_holiday.html', form=form, title='Edit Holiday', is_edit=True)

@admin_bp.route('/holidays/delete/<int:holiday_id>', methods=['POST'])
@login_required
@admin_required
def delete_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    flash(f'Holiday "{holiday.name}" deleted successfully!', 'success')
    return redirect(url_for('admin.manage_holidays'))