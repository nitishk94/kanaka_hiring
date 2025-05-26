from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.models.users import User
from app.extensions import db
from app.utils import is_valid_email

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
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not is_valid_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f"New user registration: Username = {user.username}, Email = {user.email}")
        return redirect(url_for('auth.login', registration_success=True))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
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
        username_or_email = request.form['username_or_email']
        password = request.form['password']

        if '@' in username_or_email and not is_valid_email(username_or_email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('auth.login'))

        user = None
        if '@' in username_or_email:
            user = User.query.filter_by(email=username_or_email).first()
        else:
            user = User.query.filter_by(username=username_or_email).first()

        if user and user.check_password(password):
            if not user.role:
                current_app.logger.info(f"Login attempt for unapproved user: {username_or_email}")
                return redirect(url_for('main.home', pending_approval=True))
            
            login_user(user)
            current_app.logger.info(f"User logged in: {user.email}, {user.role.capitalize()}")
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
        return redirect(url_for('auth.login'))

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    user_email = current_user.email if current_user.is_authenticated else 'Unknown'
    current_app.logger.info(f"User logged out: {user_email}")

    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))