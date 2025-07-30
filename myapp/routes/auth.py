from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy import text
from myapp.models.users import User
from myapp.extensions import db
from myapp.utils import is_valid_email
from myapp.auth.decorators import no_cache
from myapp.auth.helpers import get_msal_auth_url, get_token_from_code

bp = Blueprint('auth', __name__)

ROLE_REDIRECTS = {
    'admin': 'admin.dashboard',
    'hr': 'hr.dashboard',
    'interviewer': 'interviewer.dashboard',
    'internal_referrer': 'internal_referrer.dashboard',
    'external_referrer': 'external_referrer.dashboard',
}

@bp.route('/register', methods=['GET'])
def show_register_page():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))
    
    form_data = session.pop('form_data', None)
    
    return render_template('auth/register.html', form_data=form_data)

@bp.route('/register', methods=['POST'])
def handle_register():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))

    name = request.form.get('name')
    username = request.form.get('username').lower()
    email = request.form.get('email').lower()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not all([name, username, email, password]):
        flash("Please fill in all fields.", "error")
        return redirect(url_for('auth.show_register_page'))

    if email.endswith('@kanakasoftware.com'):
        flash('Kanaka employees should login using Microsoft. Registration is not allowed.', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('auth.show_register_page'))

    if password != confirm_password:
        flash('Passwords do not match', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('auth.show_register_page'))

    if not is_valid_email(email):
        flash('Please enter a valid email address', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('auth.show_register_page'))

    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('auth.show_register_page'))

    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('auth.show_register_page'))

    user = User(name=name, username=username, email=email, auth_type='local')
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.execute(text("SET app.current_user_id = :user_id"), {"user_id": user.id})
    db.session.commit()
    
    current_app.logger.info(f"New user registration: Username = {user.username}, Email = {user.email}")
    return redirect(url_for('auth.login', registration_success=True))

@bp.route('/login', methods=['GET'])
@no_cache
def login():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))

    form_data = session.pop('form_data', None)

    return render_template('auth/login.html', form_data=form_data)

@bp.route('/login/microsoft', methods=['GET', 'POST'])
@no_cache
def login_microsoft():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))

    auth_url = get_msal_auth_url(scopes=current_app.config["MS_SCOPE"])
    return redirect(auth_url)

@bp.route('/login/external', methods=['POST'])
@no_cache
def login_external():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))

    username_or_email = request.form.get('username_or_email')
    password = request.form.get('password')

    if not all([username_or_email, password]):
        flash("Please fill in all fields.", "error")
        return redirect(url_for('auth.login'))


    if '@' in username_or_email and not is_valid_email(username_or_email):
        flash('Please enter a valid email address', 'error')
        return redirect(url_for('auth.login')) 

    user = None
    if '@' in username_or_email:
        user = User.query.filter_by(email=username_or_email).first()
    else:
        user = User.query.filter_by(username=username_or_email).first()

    # if user and user.password_changed:
    #     return redirect(url_for('main.home', password_changed=True))
    
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
        elif user.role == 'internal_referrer':
            return redirect(url_for('internal_referrer.dashboard'))
        elif user.role == 'interviewer':
            return redirect(url_for('interviewer.dashboard'))
        elif user.role == 'external_referrer':
            return redirect(url_for('external_referrer.dashboard'))
        else:
            flash('Invalid user role. Please contact support.', 'error')
            current_app.logger.info(f"Invalid user: {username_or_email}")
            return redirect(url_for('auth.login'))
    
    flash('Invalid username/email or password', 'error')
    current_app.logger.info(f"Invalid login attempt: {username_or_email}")
    form_data = {'username_or_email': username_or_email}
    return render_template('auth/login.html', form_data=form_data), 401

@bp.route('/auth/redirect')
@no_cache
def authorized_redirect():
    # 1. Check Azure error param
    if "error" in request.args:
        err = request.args.get("error")
        desc = request.args.get("error_description", "")
        current_app.logger.error(f"MSAL callback error: {err}, {desc}")
        flash(f"Authentication error", "error")
        return redirect(url_for("auth.login"))

    # 2. Validate state
    incoming_state = request.args.get("state")
    stored_state = session.get("msal_state")
    if not stored_state or stored_state != incoming_state:
        current_app.logger.error("State mismatch or missing")
        flash("Authentication mismatch. Please try again.", "error")
        return redirect(url_for("auth.login"))
    session.pop("msal_state", None)

    # 3. Get code
    code = request.args.get('code')
    if not code:
        current_app.logger.error("Authorization code missing")
        flash("Authorization failed.", "error")
        return redirect(url_for("auth.login"))

    # 4. Exchange code for token
    token = get_token_from_code(code, scopes=current_app.config["MS_SCOPE"])
    if not token:
        current_app.logger.error("No token result returned")
        flash("Token acquisition failed.", "error")
        return redirect(url_for("auth.login"))
    if "error" in token:
        current_app.logger.error(f"Acquire token error: {token.get('error')} - {token.get('error_description')}")
        flash(f"Token authentication failed", "error")
        return redirect(url_for("auth.login"))
    if "id_token_claims" not in token:
        current_app.logger.error(f"No id_token_claims in token: {token}")
        flash("Token acquisition failed.", "error")
        return redirect(url_for("auth.login"))

    # 5. Proceed with user info
    session["token"] = token
    session["ms_authenticated"] = True
    msal_user = token["id_token_claims"]
    email = (msal_user.get("preferred_username") or
             msal_user.get("email") or
             msal_user.get("upn"))
    if not email:
        current_app.logger.error("No email in id_token_claims")
        flash("Unable to determine user email from Microsoft.", "error")
        return redirect(url_for("auth.login"))
    else:
        session["microsoft_user_email"] = email

    email = email.lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Welcome! Please register your account.", "info")
        return redirect(url_for("auth.show_add_new_user"))
    if user.auth_type != 'microsoft':
        flash("Invalid authentication method for this user.", "error")
        return redirect(url_for("auth.login"))
    if not user.role:
        flash("Your account is pending admin approval.", "warning")
        return redirect(url_for("main.home"))

    login_user(user)
    session.permanent = True
    flash("Login successful!", "success")
    return redirect(url_for(f"{user.role}.dashboard"))

@bp.route('/register/internal', methods=['GET'])
@no_cache
def show_add_new_user():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))
    
    form_data = session.pop('form_data', None)
    
    return render_template('auth/add_internal_user.html', form_data=form_data)

@bp.route('/register/internal', methods=['POST'])
@no_cache
def add_new_user():
    if current_user.is_authenticated:
        flash('You are already logged in.', 'info')
        return redirect(url_for(ROLE_REDIRECTS.get(current_user.role, 'main.home')))
    
    name = request.form.get('name')
    username = request.form.get('username').lower()
    email = session.pop('microsoft_user_email', '').lower()

    if not all([name, username, email]):
        flash("Please fill in all fields.", "error")
        return redirect(url_for('auth.show_add_new_user'))


    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'error')
        return redirect(url_for('auth.show_add_new_user'))

    user = User(name=name, username=username, email=email, auth_type='microsoft')
    db.session.add(user)
    db.session.flush()
    db.session.execute(text("SET app.current_user_id = :user_id"), {"user_id": user.id})
    db.session.commit()
    
    current_app.logger.info(f"New user registration: Username = {user.username}, Email = {user.email}")
    return redirect(url_for('auth.login', registration_success=True))

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
        session.pop("ms_authenticated", None)
        session.pop("token", None)

    return redirect(url_for('main.home'))