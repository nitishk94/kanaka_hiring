from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_required, current_user
from app.models.users import User
from app.extensions import db

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return render_template('home.html')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('main.profile'))

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('main.profile'))

        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully', 'success')
        current_app.logger.info(f"Password changed for user {current_user.username}")
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html', user=current_user)

@bp.route('/check_session')
def check_session():
    return jsonify({'active': current_user.is_authenticated})