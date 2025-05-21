from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.auth.decorators import role_required

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    return "Admin Dashboard"

@bp.route('/users')
@login_required
@role_required('admin')
def manage_users():
    return "Manage Users Page"

@bp.route('/logs')
@login_required
@role_required('admin')
def view_logs():
    return "System Logs Page"

@bp.route('/settings')
@login_required
@role_required('admin')
def settings():
    return "Admin Settings Page"

@bp.route('/reports')
@login_required
@role_required('admin')
def reports():
    return "Hiring Reports Page"