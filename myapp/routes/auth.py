from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from myapp.models.users import User
from myapp.extensions import db
from myapp.utils import is_valid_email
from myapp.auth.decorators import no_cache

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'hr':
            return redirect(url_for('hr.dashboard'))
        elif current_user.role == 'interviewer':
            return redirect(url_for('interviewer.dashboard'))
        elif current_user.role == 'referrer':
            return redirect(url_for('referrer.dashboard'))
        else:
            return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')

        if not is_valid_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)
        
        if password != password2:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html', form_data=request.form)

        user = User(name=name, username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f"New user registration: Username = {user.username}, Email = {user.email}")
        return redirect(url_for('auth.login', registration_success=True))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
@no_cache
def login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'hr':
            return redirect(url_for('hr.dashboard'))
        elif current_user.role == 'interviewer':
            return redirect(url_for('interviewer.dashboard'))
        elif current_user.role == 'referrer':
            return redirect(url_for('referrer.dashboard'))
        else:
            return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        if '@' in username_or_email and not is_valid_email(username_or_email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('auth.login'))

        user = None
        if '@' in username_or_email:
            user = User.query.filter_by(email=username_or_email).first()
            print("DEBUG: email ok", user)
        else:
            user = User.query.filter_by(username=username_or_email).first()
            print("DEBUG: username ok", user)

        #if user and user.password_changed:
           # return redirect(url_for('main.home', password_changed=True))
        
        if user and user.check_password(password):
            if not user.role:
                current_app.logger.info(f"Login attempt for unapproved user: {username_or_email}")
                return redirect(url_for('main.home', pending_approval=True))
            
            login_user(user)
            print("DEBUG: login ok", user)
            session.permanent = True
            current_app.logger.info(f"User logged in: {user.username}, {user.role.capitalize() if user.role != 'hr' else 'HR'}")
            if user.role == 'hr':
                return redirect(url_for('hr.dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'referrer':
                return redirect(url_for('referrer.dashboard'))
            elif user.role == 'interviewer':
                return redirect(url_for('interviewer.dashboard'))
            else:
                flash('Invalid user role. Please contact support.', 'error')
                current_app.logger.info(f"Invalid user: {username_or_email}")
                return redirect(url_for('auth.login'))
        
        flash('Invalid username/email or password', 'error')
        current_app.logger.info(f"Invalid login attempt: {username_or_email}")
        return render_template('auth/login.html', form_data=request.form)
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    username = current_user.username if current_user.is_authenticated else 'Unknown'
    current_app.logger.info(f"User logged out: {username}")

    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))