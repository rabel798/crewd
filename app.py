from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from models import db, User, Project, Application, TECH_CHOICES
from forms import LoginForm, RegisterForm, ProjectForm, ApplicationForm, ProfileForm
from utils import allowed_file
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    login_form = LoginForm()
    register_form = RegisterForm()
    
    if login_form.validate_on_submit() and request.form.get('form_type') == 'login':
        user = User.query.filter_by(email=login_form.email.data).first()
        if user and check_password_hash(user.password, login_form.password.data):
            login_user(user)
            if not user.role:
                return redirect(url_for('role_selection'))
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    
    if register_form.validate_on_submit() and request.form.get('form_type') == 'register':
        existing_user = User.query.filter((User.email == register_form.email.data) | 
                                          (User.username == register_form.username.data)).first()
        if existing_user:
            flash('Email or username already exists', 'error')
        else:
            # Handle profile picture upload
            profile_pic = None
            if register_form.profile_picture.data:
                file = register_form.profile_picture.data
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    profile_pic = filename
            
            # Process tech stack selection
            tech_stack = request.form.getlist('tech_stack')
            
            new_user = User(
                username=register_form.username.data,
                email=register_form.email.data,
                password=generate_password_hash(register_form.password.data),
                profile_picture=profile_pic,
                tech_stack=','.join(tech_stack) if tech_stack else '',
                created_at=datetime.now()
            )
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user)
            return redirect(url_for('role_selection'))
    
    return render_template('auth.html', login_form=login_form, register_form=register_form, tech_choices=TECH_CHOICES)

@app.route('/role-selection', methods=['GET', 'POST'])
@login_required
def role_selection():
    if request.method == 'POST':
        role = request.form.get('role')
        if role in ['applicant', 'leader', 'company']:
            current_user.role = role
            db.session.commit()
            return redirect(url_for('dashboard'))
        flash('Invalid role selected', 'error')
    
    return render_template('role_selection.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.role:
        return redirect(url_for('role_selection'))
    
    if current_user.role == 'applicant':
        # Get projects user has applied to
        applied_projects = Project.query.join(Application).filter(
            Application.applicant_id == current_user.id
        ).all()
        
        # Get all projects for browsing
        available_projects = Project.query.filter(
            Project.status == 'active'
        ).all()
        
        return render_template(
            'dashboard_applicant.html', 
            applied_projects=applied_projects, 
            available_projects=available_projects
        )
    
    elif current_user.role == 'leader':
        # Get projects created by this team leader
        my_projects = Project.query.filter_by(creator_id=current_user.id).all()
        
        # Get applications for all projects
        project_applications = {}
        for project in my_projects:
            applications = Application.query.filter_by(project_id=project.id).all()
            project_applications[project.id] = applications
        
        return render_template(
            'dashboard_leader.html', 
            projects=my_projects, 
            project_applications=project_applications
        )
    
    elif current_user.role == 'company':
        # Get all company projects
        company_projects = Project.query.filter_by(creator_id=current_user.id).all()
        
        # Get all applications across all projects
        all_applications = []
        for project in company_projects:
            applications = Application.query.filter_by(project_id=project.id).all()
            all_applications.extend(applications)
        
        return render_template(
            'dashboard_company.html', 
            projects=company_projects, 
            applications=all_applications
        )
    
    return redirect(url_for('index'))

@app.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if current_user.role not in ['leader', 'company']:
        flash('Only team leaders and companies can create projects', 'error')
        return redirect(url_for('dashboard'))
    
    form = ProjectForm()
    
    if form.validate_on_submit():
        required_skills = request.form.getlist('required_skills')
        
        new_project = Project(
            title=form.title.data,
            description=form.description.data,
            required_skills=','.join(required_skills) if required_skills else '',
            team_size=form.team_size.data,
            duration=form.duration.data,
            status='active',
            creator_id=current_user.id,
            created_at=datetime.now()
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('project_create.html', form=form, tech_choices=TECH_CHOICES)

@app.route('/projects/<int:project_id>')
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    creator = User.query.get(project.creator_id)
    
    # Check if current user has already applied
    applied = False
    if current_user.is_authenticated:
        application = Application.query.filter_by(
            project_id=project.id, 
            applicant_id=current_user.id
        ).first()
        applied = application is not None
    
    return render_template('project_view.html', project=project, creator=creator, applied=applied)

@app.route('/projects')
def project_list():
    projects = Project.query.filter_by(status='active').all()
    return render_template('project_list.html', projects=projects)

@app.route('/projects/<int:project_id>/apply', methods=['GET', 'POST'])
@login_required
def apply_project(project_id):
    if current_user.role != 'applicant':
        flash('Only applicants can apply to projects', 'error')
        return redirect(url_for('dashboard'))
    
    project = Project.query.get_or_404(project_id)
    
    # Check if already applied
    existing_application = Application.query.filter_by(
        project_id=project.id, 
        applicant_id=current_user.id
    ).first()
    
    if existing_application:
        flash('You have already applied to this project', 'error')
        return redirect(url_for('view_project', project_id=project.id))
    
    form = ApplicationForm()
    
    if form.validate_on_submit():
        new_application = Application(
            project_id=project.id,
            applicant_id=current_user.id,
            status='pending',
            message=form.message.data,
            created_at=datetime.now()
        )
        
        db.session.add(new_application)
        db.session.commit()
        
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('application_form.html', form=form, project=project)

@app.route('/applications')
@login_required
def application_list():
    if current_user.role == 'applicant':
        applications = Application.query.filter_by(applicant_id=current_user.id).all()
    elif current_user.role in ['leader', 'company']:
        # Get applications for projects created by this user
        applications = Application.query.join(Project).filter(
            Project.creator_id == current_user.id
        ).all()
    else:
        flash('Invalid user role', 'error')
        return redirect(url_for('dashboard'))
    
    # Get project details for each application
    projects = {}
    for app in applications:
        if app.project_id not in projects:
            projects[app.project_id] = Project.query.get(app.project_id)
    
    return render_template('application_list.html', applications=applications, projects=projects)

@app.route('/applications/<int:application_id>/update', methods=['POST'])
@login_required
def update_application(application_id):
    if current_user.role not in ['leader', 'company']:
        flash('Only team leaders and companies can update application status', 'error')
        return redirect(url_for('dashboard'))
    
    application = Application.query.get_or_404(application_id)
    
    # Verify the project belongs to the current user
    project = Project.query.get(application.project_id)
    if project.creator_id != current_user.id:
        flash('You do not have permission to update this application', 'error')
        return redirect(url_for('dashboard'))
    
    new_status = request.form.get('status')
    if new_status in ['pending', 'accepted', 'rejected']:
        application.status = new_status
        db.session.commit()
        flash('Application status updated', 'success')
    else:
        flash('Invalid status', 'error')
    
    return redirect(url_for('application_list'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        
        # Process tech stack selection
        tech_stack = request.form.getlist('tech_stack')
        current_user.tech_stack = ','.join(tech_stack) if tech_stack else ''
        
        # Handle profile picture upload
        if form.profile_picture.data:
            file = form.profile_picture.data
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                # Delete old profile picture if it exists
                if current_user.profile_picture:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_picture)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                current_user.profile_picture = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', form=form, tech_choices=TECH_CHOICES)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
