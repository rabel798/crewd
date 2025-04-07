from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    profile_picture = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Register')

class ProjectForm(FlaskForm):
    title = StringField('Project Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    team_size = IntegerField('Team Size', validators=[DataRequired()])
    duration = StringField('Project Duration', validators=[DataRequired()])
    submit = SubmitField('Create Project')

class ApplicationForm(FlaskForm):
    message = TextAreaField('Message to Project Creator', validators=[DataRequired()])
    submit = SubmitField('Submit Application')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    profile_picture = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg']), Optional()])
    submit = SubmitField('Update Profile')
