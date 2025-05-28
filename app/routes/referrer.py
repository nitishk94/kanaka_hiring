from flask import Blueprint, render_template, current_app, request, session, redirect, url_for, flash
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.referrals import Referral
from app.models.users import User
from app.utils import validate_file
from app.extensions import db
from werkzeug.utils import secure_filename
from datetime import date
import os

bp = Blueprint('referrer', __name__, url_prefix='/referrer')

@bp.route('/dashboard')
@login_required
@role_required('referrer')
def dashboard():
    return render_template('referrer/dashboard.html')

@bp.route('/referral', methods=['GET', 'POST'])
@login_required
@role_required('referrer')
def refer_candidates():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
        
    if request.method == 'POST':
        file = request.files.get('cv')
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('referrer/refferal.html', form_data=request.form)

        # Get all form data
        name = request.form['name']

        # Handle file upload
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'referrals')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Create new referral
        new_referral = Referral(
            name=name.title(),
            referrer_id=current_user.id,
            referred_by=User.query.get(current_user.id).name,
            referral_date=date.today(),
            cv_file_path=file_path
        )
        
        try:
            db.session.add(new_referral)
            db.session.commit()

            flash('New referral successfully created!', 'success')
            current_app.logger.info(f"New referral (Name = {new_referral.name.title()}) added by {current_user.username}")
            return redirect(url_for('referrer.referrals'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating referral. Please try again.', 'error')
            current_app.logger.error(f"Error creating referral: {str(e)}")
            return render_template('referrer/referral.html', form_data=request.form)

    return render_template('referrer/referral.html')

@bp.route('/referrals')
@login_required
@role_required('referrer', 'admin')
def referrals():
    referrals = Referral.query.filter_by(referrer_id=current_user.id).order_by(Referral.applied_date.desc()).all()
    return render_template('referrer/candidates.html', referrals=referrals)