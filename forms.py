from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField, TextAreaField, FileField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, InputRequired
from models import User, UserRole, LeaveType
from wtforms.widgets import DateInput
from flask_wtf.file import FileAllowed

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Temporary Password', validators=[Optional()]) # Optional for edit, DataRequired for add
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password', message='Passwords must match')])
    role = SelectField('Role', choices=[(role.name, role.value) for role in UserRole], validators=[DataRequired()])
    manager_id = SelectField('Manager', coerce=int, validators=[Optional()])
    submit = SubmitField('Save User')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        # Populate managers dynamically
        self.manager_id.choices = [(0, 'None')] + [(u.id, u.name) for u in User.query.filter_by(role=UserRole.MANAGER).order_by(User.name).all()]

    def validate_email(self, email):
        # user = User.query.filter_by(email=email.data).first()
        # if user and user.id != (self.user_id.data if hasattr(self, 'user_id') else None): # For edit scenario
        #     raise ValidationError('That email is already registered. Please choose a different one.')
        if hasattr(self, 'original_user'):
            # If so, find a user with the new email that ISN'T the user we are currently editing.
            user = User.query.filter(User.email == email.data, User.id != self.original_user.id).first()
        else:
            # This is "add" mode. Just check if the email exists at all.
            user = User.query.filter_by(email=email.data).first()

        if user:
            raise ValidationError('That email is already registered. Please choose a different one.')

class HolidayForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()], widget=DateInput())
    name = StringField('Holiday Name', validators=[DataRequired(), Length(min=2, max=100)])
    is_critical = SelectField('Is Critical Day?', choices=[('False', 'No'), ('True', 'Yes')], validators=[InputRequired()], coerce=lambda x: x == 'True')
    submit = SubmitField('Save Holiday')

class LeaveApplicationForm(FlaskForm):
    leave_type = SelectField('Leave Type', choices=[(lt.name, lt.value) for lt in LeaveType], validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()], widget=DateInput())
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()], widget=DateInput())
    reason = TextAreaField('Reason', validators=[DataRequired(), Length(min=10, max=500)])
    document = FileField('Attachment (for Sick Leave)', validators=[Optional(), FileAllowed(['jpg', 'png', 'pdf'], 'Images and PDFs only!')])
    submit = SubmitField('Apply Leave')

class RejectLeaveForm(FlaskForm):
    rejection_reason = TextAreaField('Reason for Rejection', validators=[DataRequired(), Length(min=10, max=500)])
    submit = SubmitField('Reject Leave')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField('Confirm New Password', 
                                         validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')