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
        
        current_app.logger.info(f"Role assigned to user {user.username}: {role} by Admin {current_user.username}")
        flash(f'Role {role.title()} assigned successfully', 'success')
        return redirect(url_for('admin.manage_users'))

    # Handle role filtering for GET requests
    role = request.args.get('role', '')
    if role:
        users = User.query.filter_by(role=role).all()
    else:
        users = User.query.all()
        
    return render_template('admin/manage_users.html', users=users, selected_role=role)

@bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        role = request.form.get('role')
        
        if not role:
            flash('Role is required', 'error')
            return redirect(url_for('admin.edit_user', user_id=user_id))
            
        if role not in ['admin', 'hr', 'interviewer', 'referrer']:
            flash('Invalid role selected', 'error')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        user.role = role
        db.session.commit()
        
        current_app.logger.info(f"Role updated for user {user.username}: {role} by Admin {current_user.username}")
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', user=user)

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

@bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    current_app.logger.info(f"User {user.username} deleted by Admin {current_user.username}")
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.manage_users'))