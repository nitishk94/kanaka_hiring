from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.users import User
from app.extensions import db

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/users', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_users():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        role = request.form.get('role')
        
        if not user_id or not role:
            flash('Missing user ID or role', 'error')
            return redirect(url_for('admin.manage_users'))
            
        if role not in ['admin', 'hr', 'interviewer', 'referrer']:
            flash('Invalid role selected', 'error')
            return redirect(url_for('admin.manage_users'))
        
        user = User.query.get_or_404(user_id)
        user.role = role
        db.session.commit()
        
        current_app.logger.info(f"Role assigned to user {user.username}: {role}")
        flash(f'Role {role.title()} assigned successfully', 'success')
        return redirect(url_for('admin.manage_users'))

    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

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