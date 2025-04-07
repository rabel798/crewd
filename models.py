from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Tech stack choices
TECH_CHOICES = [
    'Python', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js', 
    'Django', 'Flask', 'Ruby', 'Java', 'PHP', 'C#', 'Swift', 'Kotlin',
    'HTML/CSS', 'UI/UX Design', 'Database', 'DevOps', 'Mobile', 'AI/ML'
]

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    tech_stack = db.Column(db.String(255), nullable=True)  # Comma-separated list
    role = db.Column(db.String(20), nullable=True)  # applicant, leader, company
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    projects = db.relationship('Project', backref='creator', lazy=True)
    applications = db.relationship('Application', backref='applicant', lazy=True)
    
    def get_tech_stack_list(self):
        return self.tech_stack.split(',') if self.tech_stack else []

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.String(255), nullable=True)  # Comma-separated list
    team_size = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    applications = db.relationship('Application', backref='project', lazy=True)
    
    def get_required_skills_list(self):
        return self.required_skills.split(',') if self.required_skills else []

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
