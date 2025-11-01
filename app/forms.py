from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ComplaintForm(FlaskForm):
    title = StringField('Complaint Title', validators=[DataRequired()])
    location = StringField('Location (e.g., City, State)', validators=[DataRequired()])
    description = TextAreaField('Detailed Description', validators=[DataRequired()])
    submit = SubmitField('Submit Complaint')

class PublicInfoForm(FlaskForm):
    name = StringField('Name / Title', validators=[DataRequired()])
    details = TextAreaField('Details / Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Missing', 'Missing Person'), ('Wanted', 'Most Wanted'), ('Unidentified', 'Unidentified Body')], validators=[DataRequired()])
    picture = FileField('Upload Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Add Record')