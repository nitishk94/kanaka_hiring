from flask import Blueprint, render_template, current_app, request, session, redirect, url_for, flash
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.referrals import Referral
from myapp.models.users import User
from myapp.models.jobrequirement import JobRequirement
from myapp.utils import validate_file
from myapp.extensions import db
from werkzeug.utils import secure_filename
from datetime import date, datetime
from myapp.utils import validate_file, can_upload_applicant_email, can_upload_applicant_phone
from sqlalchemy.exc import IntegrityError
from myapp.models.recruitment_history import RecruitmentHistory
from myapp.models.applicants import Applicant
import os
 
bp = Blueprint('external_referrer', __name__, url_prefix='/external_referrer')
 
@bp.route('/dashboard')
@no_cache
@login_required
@role_required('external_referrer')
def dashboard():
    return render_template('external_referrer/dashboard.html')
 
 
@bp.route('/upload_applicants', methods=['GET'])
@no_cache
@login_required
@role_required('external_referrer')
def show_upload_form():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
   
    form_data = session.pop('form_data', None)
 
    referrer_names = [
        {'id': user.id, 'name': user.name} for user in User.query.filter_by(role='internal_referrer').all()
    ]
    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()
 
    return render_template('external_referrer/referral.html', referrer_names=referrer_names, job_positions=job_positions, form_data=form_data)
 
 
@bp.route('/referral', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required('external_referrer')
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
            return render_template('external_referrer/referral.html', form_data=request.form, job_positions=job_positions)
 
        name = request.form.get('name')
        is_fresher = bool(request.form.get('is_fresher'))  # True if checkbox is checked
        job_id = request.form.get('position') if not is_fresher else None
 
        # Validate name
        if not name:
            flash('Name is required.', 'warning')
            return render_template('external_referrer/referral.html', form_data=request.form, job_positions=job_positions)
 
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
            return redirect(url_for('external_referrer.referrals'))
 
        except Exception as e:
            db.session.rollback()
            flash('Error creating referral. Please try again.', 'error')
            current_app.logger.error(f"Error creating referral: {str(e)}")
            return render_template('external_referrer/referral.html', form_data=request.form, job_positions=job_positions)
 
    return render_template('external_referrer/referral.html', job_positions=job_positions, form_data={}, referrer_names=[])
   
 
 
@bp.route('/referrals', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required('external_referrer', 'admin')
def referrals():
    referrals = Referral.query.filter_by(referrer_id=current_user.id).order_by(Referral.referral_date.desc()).all()
    jobs= JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    return render_template('external_referrer/candidates.html', referrals=referrals, jobs=jobs)
 
@bp.route('/upload_applicants', methods=['POST'])
@login_required
@role_required('external_referrer')
def handle_upload_applicant():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
 
    file = request.files.get('cv')
    if not validate_file(file):
        flash('File is corrupted.', 'warning')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.show_upload_form'))
 
    email = request.form.get('email').lower()
    if not can_upload_applicant_email(email):
        flash('This candidate is under a 6-month freeze period. Please try later.', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.show_upload_form'))
 
    phone_number = request.form.get('phone_number')
    if not can_upload_applicant_phone(phone_number):
        flash('This candidate is under a 6-month freeze period. Please try later.', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.show_upload_form'))
 
    # Collect and process form data
    def get_bool(key): return bool(request.form.get(key))
 
    try:
        dob = request.form.get('dob')
        dob = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
    except ValueError:
        dob = None
 
    # Convert relevant fields
    int_or_none = lambda x: int(x) if x else None
 
    is_fresher = get_bool('is_fresher')
    experience = request.form.get('experience')
    if not is_fresher and '0' in experience:
        flash("Experience cannot be 0", "error")
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.show_upload_form'))
 
    new_applicant = Applicant(
        name=request.form.get('name').title(),
        email=email,
        phone_number=phone_number,
        dob=dob,
        gender=request.form.get('gender'),
        marital_status=request.form.get('marital_status'),
        native_place=request.form.get('native_place', '').title(),
        current_location=request.form.get('current_location', '').title(),
        work_location=request.form.get('work_location', '').title(),
        graduation_year=int_or_none(request.form.get('graduation_year')),
        is_fresher=is_fresher,
        qualification=request.form.get('qualification'),
        current_internship=get_bool('current_internship'),
        internship_duration=int_or_none(request.form.get('internship_duration')),
        paid_internship=get_bool('paid_internship'),
        stipend=int_or_none(request.form.get('stipend')),
        experience=experience,
        referenced_from=request.form.get('referenced_from'),
        linkedin_profile=request.form.get('linkedin_profile') or 'Not Provided',
        github_profile=request.form.get('github_profile') or 'Not Provided',
        is_kanaka_employee=get_bool('is_kanaka_employee'),
        current_company=request.form.get('current_company'),
        current_job_position=request.form.get('current_job_position', '').title(),
        current_ctc=int_or_none(request.form.get('current_ctc')),
        expected_ctc=int_or_none(request.form.get('expected_ctc')),
        notice_period=int_or_none(request.form.get('notice_period')),
        tenure_at_current_company=request.form.get('tenure_at_current_company'),
        current_offers_yes_no=get_bool('current_offers_yes_no'),
        current_offers_description=request.form.get('current_offers_description') or None,
        reason_for_change=request.form.get('reason_for_change') or 'Not Provided',
        comments=request.form.get('comments') or 'No comments',
        last_applied=date.today(),
        current_stage='Need to schedule test/interview',
        uploaded_by=current_user.id,
        is_referred=get_bool('is_referred'),
        referred_by=int_or_none(request.form.get('referred_by')) if get_bool('is_referred') else None,
        job_id=int_or_none(request.form.get('position')) if not get_bool('is_fresher') else None,
    )
 
    # Save file
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'applicants')
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    new_applicant.cv_file_path = file_path
 
    # Insert into DB
    try:
        db.session.add(new_applicant)
        db.session.commit()
 
        history = RecruitmentHistory(
            applicant_id=new_applicant.id,
            applied_date=date.today()
        )
        db.session.add(history)
        db.session.commit()
 
        flash('New applicant successfully created!', 'success')
        current_app.logger.info(f"New applicant (Name: {new_applicant.name}) added by {current_user.username}")
        return redirect(url_for('hr.show_upload_form'))
 
    except IntegrityError as e:
        db.session.rollback()
        if 'email' in str(e.orig):
            flash('This email is already registered.', 'error')
        elif 'phone_number' in str(e.orig):
            flash('This phone number is already registered.', 'error')
        else:
            flash('Database error. Please try again.', 'error')
        current_app.logger.error(f"IntegrityError: {e}")
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.show_upload_form'))