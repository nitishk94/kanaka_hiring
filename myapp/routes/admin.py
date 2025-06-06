from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.users import User
from myapp.extensions import db

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@no_cache
@login_required
@role_required('admin')
def dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/users')
@no_cache
@login_required
@role_required('admin')
def manage_users():
    role = request.args.get('role', '')
    if role:
        users = User.query.filter_by(role=role).all()
    else:
        users = User.query.all()
        
    return render_template('admin/manage_users.html', users=users, selected_role=role)

@bp.route('/edit_user/<int:user_id>', methods=['GET'])
@no_cache
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('admin/edit_user.html', user=user)

@bp.route('/change_role/<int:user_id>', methods=['POST'])
@no_cache
@login_required
@role_required('admin')
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get('role')
    
    if not role:
        flash('Role is required', 'error')
        return redirect(url_for('admin.edit_user', user_id=user_id))
    
    user.role = role
    db.session.commit()
    
    current_app.logger.info(f"Role updated for user {user.username}: {role.capitalize() if role != 'hr' else 'HR'} by Admin {current_user.username}")
    flash('User role updated successfully', 'success')
    if request.referrer and request.referrer.endswith(url_for('admin.manage_users')):
        return redirect(url_for('admin.manage_users'))
    else:
        return redirect(url_for('admin.edit_user', user_id=user_id))

@bp.route('/change_password/<int:user_id>', methods=['POST'])
@no_cache
@login_required
@role_required('admin')
def change_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not new_password or not confirm_password:
        flash('Both password fields are required', 'error')
        return redirect(url_for('admin.edit_user', user_id=user_id))
        
    if new_password != confirm_password:
        flash('Passwords do not match', 'error')
        return redirect(url_for('admin.edit_user', user_id=user_id))
        
    if len(new_password) < 8:
        flash('Password must be at least 8 characters long', 'error')
        return redirect(url_for('admin.edit_user', user_id=user_id))
    
    user.set_password(new_password)
    if user.role != 'admin':
        user.password_changed = True
    db.session.commit()
    
    current_app.logger.info(f"Password updated for user {user.username} by Admin {current_user.username}")
    flash('User password updated successfully', 'success')
    if request.referrer and request.referrer.endswith(url_for('main.profile')):
        return redirect(url_for('main.profile', user=current_user))
    else:
        return redirect(url_for('admin.edit_user', user_id=user_id))

@bp.route('/delete_user/<int:user_id>', methods=['POST'])
@no_cache
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    current_app.logger.info(f"User {user.username} deleted by Admin {current_user.username}")
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin.manage_users'))

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