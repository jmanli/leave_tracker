from flask import Blueprint, render_template, redirect, url_for, flash, request
from forms import LoginForm, ChangePasswordForm
from models import User
from extensions import db, login_manager
from flask_login import login_user, logout_user, current_user, login_required

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome, {user.name}!', 'success')
            if user.is_admin():
                return redirect(next_page or url_for('admin.dashboard'))
            elif user.is_manager():
                return redirect(next_page or url_for('manager.dashboard'))
            else: # Employee
                return redirect(next_page or url_for('employee.dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            current_user.force_password_change = False # Unset the flag
            db.session.commit()
            flash('Your password has been updated successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Incorrect current password.', 'danger')
    return render_template('auth/change_password.html', form=form, title='Change Password')