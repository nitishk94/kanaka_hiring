from flask import Blueprint, render_template, current_app, request, session, redirect, url_for, flash
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.referrals import Referral
from myapp.models.users import User
from myapp.models.jobrequirement import JobRequirement
from myapp.utils import validate_file
from myapp.extensions import db
from werkzeug.utils import secure_filename
from datetime import date
import os

bp = Blueprint('referrer', __name__, url_prefix='/referrer')

@bp.route('/dashboard')
@no_cache
@login_required
@role_required('referrer')
def dashboard():
    return render_template('referrer/dashboard.html')

@bp.route('/referral', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required('referrer')
def refer_candidates():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    # Fetch all job positions (id + position name) for dropdown
    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()

    if request.method == 'POST':
        file = request.files.get('cv')
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('referrer/referral.html', form_data=request.form, job_positions=job_positions)

        name = request.form.get('name')
        is_fresher = bool(request.form.get('is_fresher'))  # True if checkbox is checked
        job_id = request.form.get('position') if not is_fresher else None

        # Validate name
        if not name:
            flash('Name is required.', 'warning')
            return render_template('referrer/referral.html', form_data=request.form, job_positions=job_positions)

        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'referrals')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Create referral object
        new_referral = Referral(
            name=name.title(),
            is_fresher=is_fresher,
            job_id=int(job_id) if job_id else None,
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
            return render_template('referrer/referral.html', form_data=request.form, job_positions=job_positions)

    return render_template('referrer/referral.html', job_positions=job_positions, form_data={})


@bp.route('/referrals')
@no_cache
@login_required
@role_required('referrer', 'admin')
def referrals():
    referrals = Referral.query.filter_by(referrer_id=current_user.id).order_by(Referral.referral_date.desc()).all()
    jobs= JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    return render_template('referrer/candidates.html', referrals=referrals, jobs=jobs)