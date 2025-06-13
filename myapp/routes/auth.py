from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from myapp.models.users import User
from myapp.extensions import db
from myapp.utils import is_valid_email
from myapp.auth.decorators import no_cache
from myapp.auth.helpers import get_msal_auth_url, get_token_from_code

bp = Blueprint('auth', __name__)

# Microsoft Authentication Configuration
MS_SCOPE = ["User.Read", "Calendars.ReadWrite", "Mail.Send"]

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(f"{current_user.role}.dashboard") if current_user.role in ['admin', 'hr', 'interviewer', 'referrer'] else url_for('main.home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username').lower()
        email = request.form.get('email').lower()

        if not is_valid_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        user = User(name=name, username=username, email=email, auth_type='microsoft')
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f"New user registration: Username = {user.username}, Email = {user.email}")
        return redirect(url_for('auth.login', registration_success=True))

    return render_template('auth/register.html')

@bp.route('/register/referrer', methods=['GET', 'POST'])
def register_referrer():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(f"{current_user.role}.dashboard") if current_user.role in ['admin', 'hr', 'interviewer', 'referrer'] else url_for('main.home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username').lower()
        email = request.form.get('email').lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if not is_valid_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html', form_data=request.form)

        user = User(name=name, username=username, email=email, auth_type='local')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f"New user registration: Username = {user.username}, Email = {user.email}")
        return redirect(url_for('auth.login_referrer', registration_success=True))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
@no_cache
def login():
    auth_url = get_msal_auth_url(scopes=MS_SCOPE)
    return redirect(auth_url)

@bp.route('/auth/redirect')
@no_cache
def authorized_redirect():
    code = request.args.get('code')
    if not code:
        flash("Authorization failed.", "error")
        return redirect(url_for("auth.login"))

    token = get_token_from_code(code, scopes=MS_SCOPE)
    if not token:
        flash("Token acquisition failed.", "error")
        return redirect(url_for("auth.login"))

    msal_user = token.get("id_token_claims", {})
    email = msal_user.get("preferred_username") or msal_user.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("You're not registered. Please contact the admin.", "error")
        return redirect(url_for("auth.login"))

    if user.auth_type != 'microsoft':
        flash("Invalid authentication method for this user.", "error")
        return redirect(url_for("auth.login"))

    if not user.role:
        flash("Your account is pending admin approval.", "warning")
        return redirect(url_for("main.home"))

    login_user(user)
    session.permanent = True
    session["ms_authenticated"] = True
    flash("Login successful!", "success")
    return redirect(url_for(f"{user.role}.dashboard"))

@bp.route('/login_referrer', methods=['GET', 'POST'])
@no_cache
def login_referrer():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(f"{current_user.role}.dashboard") if current_user.role in ['admin', 'hr', 'interviewer', 'referrer'] else url_for('main.home'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')

        if '@' in username_or_email and not is_valid_email(username_or_email):
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('auth.login_referrer'))

        user = None
        if '@' in username_or_email:
            user = User.query.filter_by(email=username_or_email).first()
        else:
            user = User.query.filter_by(username=username_or_email).first()

        #if user and user.password_changed:
            #return redirect(url_for('main.home', password_changed=True))
        
        if user and user.auth_type == 'local' and user.check_password(password):
            if not user.role:
                current_app.logger.info(f"Login attempt for unapproved user: {username_or_email}")
                return redirect(url_for('main.home', pending_approval=True))
            
            login_user(user)
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
@no_cache
@login_required
def logout():
    username = current_user.username if current_user.is_authenticated else 'Unknown'
    current_app.logger.info(f"User logged out: {username}")

    logout_user()
    
    session.pop("token_cache", None)
    session.pop("user", None) 

    flash("You have been logged out.", "info")

    if session.get("ms_authenticated"):
        session.pop("ms_authenticated")
        ms_logout_url = (
            f"https://login.microsoftonline.com/common/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={url_for('main.home', _external=True)}"
        )
        return redirect(ms_logout_url)

    return redirect(url_for('main.home'))
