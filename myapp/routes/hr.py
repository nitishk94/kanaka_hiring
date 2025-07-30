from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app, session, jsonify, send_file
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.users import User
from myapp.models.applicants import Applicant
from myapp.models.recruitment_history import RecruitmentHistory
from myapp.models.interviews import Interview
from myapp.models.referrals import Referral
from myapp.models.jobrequirement import JobRequirement
from myapp.utils import validate_file, update_status, can_upload_applicant_email, can_upload_applicant_phone, is_future_or_today, get_json_info, can_update_applicant, store_result
from myapp.extensions import db
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from pytz import timezone, utc
import requests
import re
from flask import send_from_directory, abort
import os

bp = Blueprint('hr', __name__, url_prefix='/hr')
HR_ROLES = ('hr', 'admin')

excluded_stages = ['Rejected', 'On Hold', 'Joined']

@bp.route('/dashboard')
@no_cache
@login_required
@role_required('hr')
def dashboard():
    return render_template('hr/dashboard.html')

@bp.route('/applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def applicants():
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    if search_query:
        return redirect(url_for('hr.search_applicants', query=search_query))
    
    excluded_stages = ['Rejected', 'On Hold', 'Joined']
    applicants_pagination = Applicant.query.options(joinedload(Applicant.uploader))\
        .filter(~Applicant.status.in_(excluded_stages))\
        .order_by(Applicant.last_applied.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    applicants = applicants_pagination.items
    jobs = JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    hrs = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    for applicant in applicants:
        update_status(applicant.id)
    return render_template('hr/applicants.html', applicants=applicants, users=hrs, jobs=jobs, pagination=applicants_pagination)

@bp.route('/all_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def all_applicants():
    search_query = request.args.get('search', '').strip()
    stages = ['Applied','On Hold','Offered','Joined','Rejected']

    
    
    if search_query:
        return redirect(url_for('hr.search_applicants', query=search_query))
    
    applicants = Applicant.query.options(joinedload(Applicant.uploader)).order_by(Applicant.last_applied.desc()).all()
    jobs = JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    hrs = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    for applicant in applicants:
        update_status(applicant.id)
    return render_template('hr/applicants_all.html', users=hrs, jobs=jobs, all_stages=stages)

@bp.route('/upload_applicants', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def show_upload_form():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
    
    form_data = session.pop('form_data', None)

    referrer_names = [
        {
            'id': user.id,
            'name': f"{user.name} ({user.role.capitalize()})"
        }
        for user in User.query.filter(func.lower(User.role).in_(['referrer', 'hr', 'admin'])).all()
    ]
    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()
    return render_template('hr/upload.html', referrer_names=referrer_names, job_positions=job_positions, form_data=form_data)

def is_valid_mobile(phone_number):
    # Must be 10 digits and start with 6-9
    if not re.fullmatch(r'^(?!([6-9])\1{9})[6-9][0-9]{9}$', phone_number):
        return False
    # Reject if all digits are the same (like 9999999999)
    if len(set(phone_number)) == 1:
        return False
    return True

def upload_applicant_form():
    referrer_users = User.query.filter(User.role.in_(['referrer', 'hr', 'admin'])).all()
    
    # Format for Vue multiselect
    referrer_names = [
        {
            "id": user.id,
            "name": user.name or user.username,
            "role": user.role
        }
        for user in referrer_users
    ]

    max_dob = date.today().replace(year=date.today().year - 18).isoformat()

    return render_template(
        "hr/upload.html",
        referrer_names=referrer_names,
        max_dob=max_dob)




    
@bp.route('/upload_applicants', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
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
    
    dob_str = request.form.get('dob')
    if dob_str:
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            flash("Invalid DOB, the candidate must be at least 18 years old.", "error")
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

@bp.route('/update_applicants/<int:id>', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def show_update_form(id):
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
    
    
    form_data = session.pop('form_data', None)

    applicant = Applicant.query.get_or_404(id)

    referrer_names = [
        {'id': user.id, 'name': user.name} for user in User.query.filter_by(role='internal_referrer').all()
    ]
    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()

    return render_template('hr/update_applicant.html', applicant=applicant, referrer_names=referrer_names, job_positions=job_positions, form_data=form_data)



@bp.route('/update_applicants/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def update_applicant(id):
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
    
    applicant = Applicant.query.get_or_404(id)
    file = request.files.get('cv')
    if file and file.filename:
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            session['form_data'] = request.form.to_dict()
            return redirect(url_for('show_update_form'), id=id)
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'applicants')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        applicant.cv_file_path = file_path
    else:
        if not applicant.cv_file_path or not os.path.exists(applicant.cv_file_path):
            flash('No existing CV found. Please upload a new one.', 'warning')
            session['form_data'] = request.form.to_dict()
            return redirect(url_for('show_update_form', id=id))


    email = request.form.get('email').lower()
    if not can_update_applicant(id,email):
        flash('The entered email already exists. Please enter a different email.', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('show_update_form'), id=id)
    
    dob_str = request.form.get('dob')
    if dob_str:
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            flash("Invalid DOB, the candidate must be at least 18 years old.", "error")
            return redirect(url_for('hr.show_update_form', id=applicant.id))
    

    def get_bool(key): return bool(request.form.get(key))
    int_or_none = lambda x: int(x) if x else None

    is_fresher = get_bool('is_fresher')
    experience = request.form.get('experience')
    if not is_fresher and '0' in experience:
        flash("Experience cannot be 0", "error")
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('show_update_form'), id=id)

    try:
        dob = request.form.get('dob')
        dob = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
    except ValueError:
        dob = None

    applicant.name = request.form.get('name').title()
    applicant.email = email
    applicant.phone_number = request.form.get('phone_number')
    applicant.dob = dob
    applicant.gender = request.form.get('gender')
    applicant.marital_status = request.form.get('marital_status')
    applicant.native_place = request.form.get('native_place', '').title()
    applicant.current_location = request.form.get('current_location', '').title()
    applicant.work_location = request.form.get('work_location', '').title()
    applicant.graduation_year = int_or_none(request.form.get('graduation_year'))
    applicant.is_fresher = is_fresher
    applicant.qualification = request.form.get('qualification')
    applicant.current_internship = get_bool('current_internship')
    applicant.internship_duration = int_or_none(request.form.get('internship_duration'))
    applicant.paid_internship = get_bool('paid_internship')
    applicant.stipend = int_or_none(request.form.get('stipend'))
    applicant.experience = experience
    applicant.referenced_from = request.form.get('referenced_from')
    applicant.linkedin_profile = request.form.get('linkedin_profile') or 'Not Provided'
    applicant.github_profile = request.form.get('github_profile') or 'Not Provided'
    applicant.is_kanaka_employee = get_bool('is_kanaka_employee')
    applicant.current_company = request.form.get('current_company')
    applicant.current_job_position = request.form.get('current_job_position', '').title()
    applicant.current_ctc = int_or_none(request.form.get('current_ctc'))
    applicant.expected_ctc = int_or_none(request.form.get('expected_ctc'))
    applicant.notice_period = int_or_none(request.form.get('notice_period'))
    applicant.tenure_at_current_company = request.form.get('tenure_at_current_company')
    applicant.current_offers_yes_no = get_bool('current_offers_yes_no')
    applicant.current_offers_description = request.form.get('current_offers_description') or None
    applicant.reason_for_change = request.form.get('reason_for_change') or 'Not Provided'
    applicant.comments = request.form.get('comments') or 'No comments'
    applicant.job_id = int_or_none(request.form.get('position')) if not get_bool('is_fresher') else None
    applicant.is_referred = get_bool('is_referred')
    applicant.referred_by = int_or_none(request.form.get('referred_by')) if get_bool('is_referred') else None

    
    try:
        db.session.commit()

        flash('Applicant details successfully updated!', 'success')
        current_app.logger.info(f"Applicant (Name: {applicant.name.title()}) details updated by {current_user.username}")
        return redirect(url_for('hr.view_applicant', id=applicant.id))
        
    except IntegrityError as e:
        db.session.rollback()
        if 'email' in str(e.orig):
            flash('This email is already registered. Please use a different one.', 'error')
        elif 'phone_number' in str(e.orig):
            flash('This phone number is already registered. Please use a different one.', 'error')
        else:
            flash('Database error. Please try again.', 'error')
        current_app.logger.error(f"IntegrityError creating applicant: {str(e)}")
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('show_update_form'), id=id)

# @bp.route('/view_applicant/<int:id>')
# @no_cache
# @login_required
# @role_required(*HR_ROLES)
# def view_applicant(id):
#     update_status(id)
#     applicant = Applicant.query.get_or_404(id)
#     interviewers = User.query.filter_by(role='interviewer').all()
#     current_date = date.today().isoformat() 
#     return render_template('hr/view_applicant.html', applicant=applicant, interviewers=interviewers, current_date = current_date)

@bp.route('/view_applicant/<int:id>')
@no_cache
@login_required
@role_required(*HR_ROLES)
def view_applicant(id):
    update_status(id)
    applicant = Applicant.query.get_or_404(id)
    interviewers = User.query.filter_by(role='interviewer').all()
    current_date = date.today().isoformat() 
    
    # Get the recruitment history record
    recruitment_history = (
        db.session.query(RecruitmentHistory)
        .filter_by(applicant_id=id)
        .order_by(RecruitmentHistory.updated_at.desc())
        .first()
    )
    return render_template('hr/view_applicant.html', applicant=applicant, interviewers=interviewers, current_date = current_date, recruitment_history = recruitment_history)


@bp.route('/filter_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def filter_applicants():
    hr_users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    jobs = JobRequirement.query.order_by(JobRequirement.position).all()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    hr_id = request.args.get('hr_id', '').strip()
    job_id = request.args.get('job_id', '').strip()
    status_id = request.args.get('status', '').strip()

    excluded_stages = ['Rejected','On Hold' ,'Joined']  

    query = Applicant.query.options(
        joinedload(Applicant.uploader),
        joinedload(Applicant.job)
    )

    # Apply filters
    if hr_id:
        query = query.filter(Applicant.uploaded_by == int(hr_id))
    if job_id:
        query = query.filter(Applicant.job_id == int(job_id))
    if status_id == 'fresher':
        query = query.filter(Applicant.is_fresher.is_(True))
    elif status_id == 'experienced':
        query = query.filter(Applicant.is_fresher.is_(False))

    # Apply stage exclusion
    if excluded_stages:
        query = query.filter(~Applicant.status.in_(excluded_stages))

    # Order and paginate
    query = query.order_by(Applicant.last_applied.desc())
    applicants_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    applicants = applicants_pagination.items

    return render_template(
        'hr/applicants.html',
        applicants=applicants,
        users=hr_users,
        jobs=jobs,
        pagination=applicants_pagination,
        hr_id=hr_id,
        job_id=job_id,
        status_id=status_id
    )


@bp.route('/sort_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def sort_applicants():
    sort_by = request.args.get('sort_by', 'date')
    
    # Eager load uploader and job for display
    query = Applicant.query.options(
        joinedload(Applicant.uploader),
        joinedload(Applicant.job)
    )

    if sort_by == 'name':
        query = query.order_by(Applicant.name.asc())
    elif sort_by == 'hr':
        # join uploader explicitly and order by User.name
        query = query.join(Applicant.uploader).order_by(User.name.asc())
    else:  # Default to sorting by latest application
        query = query.order_by(Applicant.last_applied.desc())

    applicants = query.all()

    # For filter dropdowns
    users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    jobs = JobRequirement.query.all()

    return render_template(
        'hr/applicants_all.html',
        applicants=applicants,
        users=users,
        jobs=jobs,
        search_query='' )


@bp.route('/search_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def search_applicants():
    search_query = request.args.get('query', '').strip()
    sort_by = request.args.get('sort_by', 'date')

    if not search_query:
        return redirect(url_for('hr.applicants'))

    base_query = Applicant.query.options(joinedload(Applicant.uploader))

    if '@' in search_query:
        base_query = base_query.filter(Applicant.email.ilike(f'%{search_query}%'))
    else:
        base_query = base_query.filter(Applicant.name.ilike(f'%{search_query}%'))

    if excluded_stages:
        base_query = base_query.filter(~Applicant.status.in_(excluded_stages))

    applicants = base_query.order_by(Applicant.last_applied.desc()).all()

    jobs = JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    hrs = User.query.filter(User.role.in_(['hr', 'admin'])).all()

    return render_template(
        'hr/applicants.html',
        applicants=applicants,
        users=hrs,
        jobs=jobs,
        search_query=search_query,
        sort_by=sort_by
    )

#cv download
@bp.route('/applicants/<int:id>/download_cv')
@no_cache
@login_required
@role_required(*HR_ROLES)
def download_applicant_cv(id):
    applicant = Applicant.query.get_or_404(id)
    if not applicant.cv_file_path or not os.path.exists(applicant.cv_file_path):
        flash("CV file not found.", "error")
        return redirect(url_for('hr.show_upload_form'))
    return send_file(applicant.cv_file_path, as_attachment=True)
 

@bp.route('/schedule_interview/<int:id>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_interview(id):
    if request.method == 'GET':
        current_date = date.today().isoformat()
        return render_template('hr/schedule_interview.html', current_date=current_date)

    if "token" not in session:
        flash("You must be logged in through Microsoft to schedule interviews.", "error")
        return redirect(url_for('auth.login'))
    
    access_token = session["token"]["access_token"]
    interview_date = request.form.get('interview_date')
    interview_time = request.form.get('interview_time')
    interviewer_id = request.form.get('interviewer_id')

    if isinstance(interview_date, str):
        try:
            date = datetime.strptime(interview_date, '%Y-%m-%d').date()
        except ValueError:
            date = None

    if isinstance(interview_time, str):
        try:
            time = datetime.strptime(interview_time, '%H:%M').time()
        except ValueError:
            time = None
    
    if not date or not time:
        flash('Invalid date or time format.', 'error')
        return redirect(url_for('hr.view_applicant', id=id))

    if not is_future_or_today(date):
        flash('Interview date must be today or in the future.', 'error')
        return redirect(url_for('hr.view_applicant', id=id))
    
    applicant = Applicant.query.get_or_404(id)
    interviewer = User.query.get_or_404(interviewer_id)
    history = RecruitmentHistory.query.filter_by(applicant_id = id).first()
    start_datetime = datetime.combine(date, time)
    end_datetime = start_datetime + timedelta(hours=1)

    if interviewer.auth_type == 'local':
        if not history.interview_round_1_date:
            round = 'Client Round 1'            
            history.interview_round_1_date = date
            history.interview_round_1_time = time
        elif not history.interview_round_2_date:
            round = 'Client Round 2'
            history.interview_round_2_date = date
            history.interview_round_2_time = time
        elif not history.hr_round_date:
            round = 'HR Round'
            history.hr_round_date = date
            history.hr_round_time = time
    else:
        if not history.interview_round_1_date:
            round = 'Client Round 1'
            history.interview_round_1_date = date
            history.interview_round_1_time = time
        elif not history.interview_round_2_date:
            round = 'Client Round 2'
            history.interview_round_2_date = date
            history.interview_round_2_time = time
        else:
            round = 'HR Round'
            history.hr_round_date = date
            history.hr_round_time = time
    
    existing = Interview.query.filter_by(applicant_id=id, round_number=str(round)).first()
    if existing:
        flash("This interview round has already been scheduled.", "warning")
        return redirect(url_for('hr.view_applicant', id=id))

    interview = Interview(
        applicant_id=id,
        date=date,
        time=time,
        round_number=round,
        interviewer_id=interviewer_id,
        scheduler_id=current_user.id
    )
    db.session.add(interview)
    db.session.commit()

    attendees = [
        {
            "emailAddress": {
                "address": interviewer.email,
                "name": interviewer.name
            },
            "type": "required"
        },
        {
            "emailAddress": {
                "address": applicant.email,
                "name": applicant.name
            },
            "type": "required"
        }
    ]

    hrs = User.query.filter_by(role='hr').all()
    for hr in hrs:
        if hr.id != current_user.id:
            attendees.append({
                "emailAddress": {
                    "address": hr.email,
                    "name": hr.name
                },
                "type": "optional"
            })
    
    attendees.append(get_json_info())

    graph_endpoint = 'https://graph.microsoft.com/v1.0/me/events'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    body = {
        "subject": f"Interview Round {round} with {applicant.name}",
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": "Asia/Kolkata"
        },
        "location": {
            "displayName": "Microsoft Teams Meeting"
        },
        "attendees": attendees,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    response = requests.post(graph_endpoint, headers=headers, json=body)

    if response.status_code == 201:
        flash(f'Interview round {round} scheduled and calendar invite sent.', 'success')
        current_app.logger.info(f"Meeting created for round {round} for applicant {id}")
        if history.test_result and history.test_date and not history.interview_round_1_comments:
            store_result(id)
    else:
        flash('Interview saved, but failed to schedule calendar meeting.', 'warning')
        current_app.logger.error(f"Graph API error: {response.status_code}, {response.text}")
    


    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/offered_application/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def offered_application(id):
    applicant = Applicant.query.get_or_404(id)
    applicant.status = 'Offered'
    db.session.commit()
    current_app.logger.info(f"Candidate {applicant.name} is offered a job")
    flash('Applicant has been offered a job.', 'success')
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/joined_application/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def joined_application(id):
    applicant = Applicant.query.get_or_404(id)
    applicant.status = 'Joined'
    db.session.commit()
    current_app.logger.info(f"Candidate {applicant.name} has joined")
    flash('Applicant has joined.', 'success')
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/on_hold_application/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def put_on_hold_application(id):
    applicant = Applicant.query.get_or_404(id)
    applicant.status = 'On Hold'
    db.session.commit()
    current_app.logger.info(f"Candidate {applicant.name} put on hold")
    flash('Applicant has been put on hold.', 'warning')
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/off_hold_application/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def put_off_hold_application(id):
    applicant = Applicant.query.get_or_404(id)
    applicant.status = 'Applied'
    db.session.commit()
    current_app.logger.info(f"Candidate {applicant.name} is off on-hold")
    flash('Applicant is now off on-hold.', 'success')
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/reject_application/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def reject_application(id):
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    history.rejected = True
    applicant = Applicant.query.get_or_404(id)
    applicant.status = 'Rejected'
    db.session.commit()
    current_app.logger.info(f"Candidate {applicant.name} rejected")
    flash('Candidate rejected', 'error')
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/view_referrals')
@no_cache
@login_required
@role_required(*HR_ROLES)
def view_referrals():
    referrals = Referral.query.all()
    users =User.query.filter(User.role.in_(['referrer', 'hr', 'admin'])).all()
    jobs= JobRequirement.query.order_by(JobRequirement.position).all()
    return render_template('hr/view_referrals.html', referrals=referrals,jobs=jobs,users=users)

@bp.route('/filter_referrals')
@no_cache
@login_required
@role_required(*HR_ROLES)
def filter_referrals():
    referral_id = request.args.get('referral_id', type=int)
    job_id = request.args.get('job_id', type=int)
    referral_users = User.query.filter(User.role.in_(['referrer', 'hr', 'admin'])).all()
    jobs = JobRequirement.query.order_by(JobRequirement.position).all()
    query = Referral.query.outerjoin(Referral.job).options(joinedload(Referral.job))

    if referral_id:
        query = query.filter(Referral.referrer_id == referral_id)
    if job_id:
        query = query.filter(Referral.job_id == job_id)
    referrals = query.order_by(Referral.id.desc()).all()
    return render_template('hr/view_referrals.html', referrals=referrals, jobs=jobs, users=referral_users)


@bp.route('/upload_referral_applicant/<int:referral_id>/<int:referrer_id>/<name>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def upload_referral_applicant(referral_id,referrer_id, name):
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    if request.method == 'GET':
        form_data = session.pop('form_data', None)
        job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position)\
                                            .filter(JobRequirement.is_open == True).all()
        referral = Referral.query.get_or_404(referral_id)
        if not form_data:
            form_data = {}
        form_data['name'] = name
        form_data['is_fresher'] = referral.is_fresher

        return render_template('hr/upload_referral_applicant.html',
            job_positions=job_positions,
            form_data=form_data,
            referral_id=referral_id,
            referrer_id=referrer_id,
            name=name,
            referral= referral
            )


    # ---- POST logic begins ----

    dob_str = request.form.get('dob')
    if dob_str:
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            flash("Invalid DOB, the candidate must be at least 18 years old.", "error")
            return redirect(url_for('hr.upload_referral_applicant', referral_id=referral_id, referrer_id=referrer_id, name=name))
        

    file = request.files.get('cv')
    referral = Referral.query.get_or_404(referral_id)

    if file and file.filename:
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            session['form_data'] = request.form.to_dict()
            return redirect(url_for('hr.upload_referral_applicant', referral_id=referral_id, referrer_id=referrer_id, name=name))
        use_referral_cv = False
    elif referral.cv_file_path and os.path.exists(referral.cv_file_path):
        use_referral_cv = True
    else:
        flash("Please upload a valid CV or ensure a referral CV is available.", "warning")
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.upload_referral_applicant', referral_id=referral_id, referrer_id=referrer_id, name=name))


    email = request.form.get('email').lower()
    if not can_upload_applicant_email(email):
        flash('This candidate is under a 6-month freeze period. Please try later.', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.view_referrals'))

    phone_number = request.form.get('phone_number')
    if not can_upload_applicant_phone(phone_number):
        flash('This candidate is under a 6-month freeze period. Please try later.', 'error')
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.view_referrals'))

    def get_bool(key): return bool(request.form.get(key))
    int_or_none = lambda x: int(x) if x else None

    try:
        dob = request.form.get('dob')
        dob = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
    except ValueError:
        dob = None

    is_fresher = get_bool('is_fresher')
    experience = request.form.get('experience')
    if not is_fresher and '0' in experience:
        flash("Experience cannot be 0", "error")
        session['form_data'] = request.form.to_dict()
        return redirect(url_for('hr.upload_referral_applicant', referral_id=referral_id, referrer_id=referrer_id, name=name))
    
    new_applicant = Applicant(
        name=name,
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
        is_referred=True,
        referred_by=int(referrer_id),
        job_id=int_or_none(request.form.get('position')) if not is_fresher else None,
    )

    # Save file
    if file and validate_file(file):
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'applicants')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        new_applicant.cv_file_path = file_path
    else:
        referral = Referral.query.get_or_404(referral_id)
        if referral.cv_file_path:
            new_applicant.cv_file_path = referral.cv_file_path
        else:
            flash("No CV was uploaded. Please upload a CV or check with the referrer.", "error")
            return redirect(url_for('hr.upload_referral_applicant', referral_id=referral_id, referrer_id=referrer_id, name=name))

    try:
        db.session.add(new_applicant)
        db.session.flush()

        history = RecruitmentHistory(applicant_id=new_applicant.id, applied_date=date.today())
        db.session.add(history)

        referral = Referral.query.get_or_404(referral_id)
        referral.applicant_id = int(new_applicant.id)
        
        db.session.commit()
        
        flash('New applicant successfully created!', 'success')
        current_app.logger.info(f"New applicant (Name: {new_applicant.name}) added by {current_user.username}")
        return redirect(url_for('hr.view_referrals'))

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
        return redirect(url_for('hr.view_referrals'))




@bp.route('/onboarding')
@no_cache
@login_required
@role_required(*HR_ROLES)
def onboarding():
    return "Onboarding and Offer Letter Page"


@bp.route('/filter_interviews')
@no_cache
@login_required
@role_required(*HR_ROLES)
def filter_interviews_by_hr():
    hr_users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    hr_id = request.args.get('hr_id', '')
    if hr_id:
        interviews = Interview.query\
            .filter_by(completed=False, scheduler_id=hr_id)\
            .options(
                joinedload(Interview.applicant),
                joinedload(Interview.interviewer),
                joinedload(Interview.scheduler)
            )\
            .all()
    else:
        interviews = Interview.query\
            .filter_by(completed=False)\
            .options(
                joinedload(Interview.applicant),
                joinedload(Interview.interviewer),
                joinedload(Interview.scheduler)
            )\
            .all()
    return render_template('hr/view_interviews.html', interviews=interviews, users=hr_users)

#filter by interviewers
@bp.route('/filter_interviews')
@no_cache
@login_required
@role_required(*HR_ROLES)
def filter_interviews_by_interviewer():
    interviewer_users = User.query.filter(User.role.in_(['interviewer'])).all()
    interviewer_id = request.args.get('interviewer_id', '')
    if interviewer_id:
        interviews = Interview.query\
            .filter_by(completed=False, scheduler_id=interviewer_id)\
            .options(
                joinedload(Interview.applicant),
                joinedload(Interview.interviewer),
                joinedload(Interview.scheduler)
            )\
            .all()
    else:
        interviews = Interview.query\
            .filter_by(completed=False)\
            .options(
                joinedload(Interview.applicant),
                joinedload(Interview.interviewer),
                joinedload(Interview.scheduler)
            )\
            .all()
    return render_template('hr/view_interviews.html', interviews=interviews, interviewers=interviewer_users)

@bp.route('/reschedule_interview/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def reschedule_interview(id):
    if "token" not in session:
        flash("You must be logged in through Microsoft to schedule interviews.", "error")
        return redirect(url_for('auth.login'))
    
    access_token = session["token"]["access_token"]
    date = request.form.get('interview_date')
    time = request.form.get('interview_time')
    interviewer_ids = [int(id) for id in request.form.getlist('interviewer_ids')]

    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            date = None

    if isinstance(time, str):
        try:
            time = datetime.strptime(time, '%H:%M').time()
        except ValueError:
            try:
                time = datetime.strptime(time, '%H:%M:%S').time()
            except ValueError:
                time = None
    
    if not is_future_or_today(date):
        flash("Choose a proper date", "error")
        referrer = request.referrer
        if referrer and 'view_interviews' in referrer:
            return redirect(url_for('hr.view_interviews'))
        return redirect(url_for('hr.view_applicant', id=id))
        
    if not interviewer_ids:
        flash('Please select at least one interviewer.', 'error')
        referrer = request.referrer
        if referrer and 'view_interviews' in referrer:
            return redirect(url_for('hr.view_interviews'))
        return redirect(url_for('hr.view_applicant', id=id))

    applicant = Applicant.query.get_or_404(id)
    
    existing_interviews = Interview.query.filter_by(applicant_id=id, completed=False).all()
    if not existing_interviews:
        flash('No active interviews found to reschedule.', 'error')
        return redirect(url_for('hr.view_applicant', id=id))
    
    round_number = str(existing_interviews[0].round_number)
    
    interviewers = User.query.filter(User.id.in_(interviewer_ids)).all()
    if len(interviewers) != len(interviewer_ids):
        flash('One or more selected interviewers could not be found.', 'error')
        return redirect(url_for('hr.view_applicant', id=id))
    
    for i, interview in enumerate(existing_interviews):
        if i < len(interviewers):
            interview.date = date
            interview.time = time
            interview.interviewer_id = interviewers[i].id
            interview.scheduler_id = current_user.id
    
    for i in range(len(existing_interviews), len(interviewers)):
        new_interview = Interview(
            applicant_id=id,
            date=date,
            time=time,
            round_number=str(round_number),
            interviewer_id=interviewers[i].id,
            scheduler_id=current_user.id
        )
        db.session.add(new_interview)
    
    history = RecruitmentHistory.query.filter_by(applicant_id=applicant.id).first()
    start_datetime = datetime.combine(date, time)
    end_datetime = start_datetime + timedelta(hours=1)

    if round_number == 1 or round_number == 'Client Round 1':
        history.interview_round_1_date = date
        history.interview_round_1_time = time
    elif round_number == 2 or round_number == 'Client Round 2':
        history.interview_round_2_date = date
        history.interview_round_2_time = time
    else:
        history.hr_round_date = date
        history.hr_round_time = time

    db.session.commit()

    attendees = []

    for interviewer in interviewers:
        attendees.append({
            "emailAddress": {
                "address": interviewer.email,
                "name": interviewer.name
            },
            "type": "required"
        })

    attendees.append({
        "emailAddress": {
            "address": applicant.email,
            "name": applicant.name
        },
        "type": "required"
    })


    hrs = User.query.filter_by(role='hr').filter(User.id != current_user.id).all()
    for hr in hrs:
        attendees.append({
            "emailAddress": {
                "address": hr.email,
                "name": hr.name
            },
            "type": "optional"
        })
    
    attendees.append(get_json_info())

    graph_endpoint = 'https://graph.microsoft.com/v1.0/me/events'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }


    body = {
        "subject": f"Rescheduled {round} with {applicant.name}",
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": "Asia/Kolkata"
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": "Asia/Kolkata"
        },
        "location": {
            "displayName": "Microsoft Teams Meeting"
        },
        "attendees": attendees,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    response = requests.post(graph_endpoint, headers=headers, json=body)

    if response.status_code == 201:
        flash(f'Interview rescheduled with {len(interviewers)} interviewer(s) and calendar invite sent.', 'success')
        current_app.logger.info(f"Meeting rescheduled for {round} for applicant {id} with {len(interviewers)} interviewers")
    else:
        flash('Interview rescheduling saved, but failed to schedule calendar meeting.', 'warning')
        current_app.logger.error(f"Graph API error: {response.status_code}, {response.text}")

    referrer = request.referrer
    if referrer and 'view_interviews' in referrer:
        return redirect(url_for('hr.view_interviews'))
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/upload_joblistings', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def show_job_form():
    return render_template('hr/addjob.html')

@bp.route('/upload_joblistings', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def submit_job_form():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    # Extract form data
    job_position = request.form.get('position_name') 
    job_description = request.form.get('job_description')
    job_skillset = request.form.get('job_skillset')
    job_clients = request.form.get('job_clients')
    job_budget = request.form.get('job_budget')
    job_experience = request.form.get('job_experience')  
    for_vendor = bool(request.form.get('for_vendor'))

    # Validate required fields
    if not job_position or not job_description:
        flash('Position name and description are required.', 'error')
        return render_template('hr/addjob.html', form_data=request.form)

    new_jobrequirement = JobRequirement(
        position=job_position,
        description=job_description,
        created_by=current_user,
        skillset=job_skillset,
        clients=job_clients or None ,
        budget=job_budget,
        experience=job_experience,
        for_vendor=for_vendor
    )

    db.session.add(new_jobrequirement)
    db.session.commit()

    flash('New job listing successfully created!', 'success')
    current_app.logger.info(f"New job listing (Posting: {new_jobrequirement.position}) added by {current_user.name}")
    
    return redirect(url_for('main.view_joblisting'))

# Show the job update form
@bp.route('/update_joblisting/<int:id>', methods=['GET'])
@no_cache
@login_required
@role_required('hr', 'admin')
def show_joblisting_update(id):
    job = JobRequirement.query.get_or_404(id)
    return render_template('hr/detailsjob.html', joblisting=job)

# Handle the form submission to update job details
@bp.route('/update_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required('hr', 'admin')
def submit_joblisting_update(id):
    job = JobRequirement.query.get_or_404(id)

    position = request.form.get('job_position')
    description = request.form.get('job_description')
    skillset = request.form.get('job_skillset')
    clients = request.form.get('job_clients')
    budget = request.form.get('job_budget')
    experience = request.form.get('job_experience')
    for_vendor = bool(request.form.get('open_for_vendor'))


    if not position or not description:
        flash('Job position and description cannot be empty!', 'error')
        return redirect(url_for('hr.show_joblisting_update', id=id))

    job.position = position
    job.description = description
    job.skillset = skillset
    job.clients = clients or None
    job.budget = budget
    job.experience = experience
    job.for_vendor = for_vendor

    db.session.commit()

    flash('Job listing updated successfully!', 'success')
    return redirect(url_for('main.view_details_joblisting', id=id))

@bp.route('/close_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def close_joblisting(id):
    joblisting = JobRequirement.query.get_or_404(id)
    joblisting.is_open = False
    joblisting.for_vendor = False
    db.session.commit()
    current_app.logger.info(f"Job listing {joblisting.position} closed by {current_user.username}")
    flash('Job listing closed successfully', 'success')
    return redirect(url_for('main.view_joblisting'))

@bp.route('/open_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def open_joblisting(id):
    joblisting = JobRequirement.query.get_or_404(id)
    joblisting.is_open = True
    db.session.commit()
    current_app.logger.info(f"Job listing {joblisting.position} opened by {current_user.username}")
    flash('Job listing reopened successfully', 'success')
    return redirect(url_for('main.view_joblisting'))

@bp.route('/for_vendor_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def for_vendor_joblisting(id):
    joblisting = JobRequirement.query.get_or_404(id)
    joblisting.for_vendor = True
    db.session.commit()
    current_app.logger.info(f"Job listing {joblisting.position} opened for external vendors by {current_user.username}")
    flash('Job listing opened for external vendors successfully', 'success')
    return redirect(url_for('main.view_joblisting'))

@bp.route('/not_for_vendor_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def not_for_vendor_joblisting(id):
    joblisting = JobRequirement.query.get_or_404(id)
    joblisting.for_vendor = False
    db.session.commit()
    current_app.logger.info(f"Job listing {joblisting.position} closed for external vendors by {current_user.username}")
    flash('Job listing closed for external vendors successfully', 'error')
    return redirect(url_for('main.view_joblisting'))

@bp.route('/delete_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def delete_joblisting(id):
    joblisting = JobRequirement.query.get_or_404(id)
    db.session.delete(joblisting)
    db.session.commit()
    current_app.logger.info(f"Job listing {joblisting.position} deleted by Admin {current_user.username}")
    flash('Job listing deleted successfully', 'success')
    return redirect(url_for('main.view_joblisting'))

def get_test_ids():
    url_for="https://apiv3.imocha.io/v3/tests"
    headers = {
        "X-API-KEY":"MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type":"application/json"
    }
    response = requests.get(url_for, headers=headers)
    result=response.json()
    test_dict = {test["testId"]: test["testName"] for test in result["tests"]}
    return test_dict

@bp.route('/schedule_test/<int:id>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_test(id):
    applicant = Applicant.query.get_or_404(id)

    if request.method == 'POST':
        test_id = request.form.get('test_id')
        test_link = request.form.get('test_link')
        
        today = datetime.today()
        day_str = today.strftime('%A')           
        time_str = today.strftime('%H:%M:%S')   

        if day_str == 'Friday':
            end_datetime = today + timedelta(days=2)
        else:
            end_datetime = today + timedelta(days=1)

        start_date = today.strftime('%Y-%m-%d')      
        end_date = end_datetime.strftime('%Y-%m-%d')


        if not test_link:
            return redirect(url_for('hr.schedule_default',id=id,testId=test_id,start_test_date=start_date,end_test_date=end_date,test_time=time_str))
        else:
            return redirect(url_for('hr.schedule_linkid',id=id,testId=test_id,testLinkId=test_link,start_test_date=start_date,end_test_date=end_date,test_time=time_str))

    url = "https://apiv3.imocha.io/v3/tests"
    headers = {
        "X-API-KEY": "MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    result = response.json()
    test_dict = {test["testId"]: test["testName"] for test in result["tests"]}

    selected_test_id = request.args.get('test_id', type=int)
    test_links = {}

    if selected_test_id:
        link_url = f"https://apiv3.imocha.io/v3/tests/{selected_test_id}/testlinks"
        link_response = requests.get(link_url, headers=headers)
        if link_response.status_code == 200:
            link_data = link_response.json()
            test_links = {
                link["testLinkId"]: link.get("testLinkName", "Unnamed Link")
                for link in link_data.get("testLinks", [])
            }

    return render_template(
        'hr/test_schedule.html',
        tests=test_dict,
        applicant=applicant,
        selected_test_id=selected_test_id,
        test_links=test_links
    )

@bp.route('/schedule_default/<int:id>/<int:testId>/<start_test_date>/<test_time>/<end_test_date>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_default(id,testId,start_test_date,end_test_date,test_time):
    api_url="https://apiv3.imocha.io/v3/tests/"+str(testId)+"/invite"
    headers = {
        "X-API-KEY": "MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }
    
    applicant = Applicant.query.get_or_404(id)
    history= RecruitmentHistory.query.filter_by(applicant_id=applicant.id).first()
    if history.test_id:
        flash('Test already scheduled for this applicant.', 'warning')
        return redirect(url_for('hr.view_applicant', id=applicant.id))
    history.test_date = start_test_date
    history.test_time = test_time
    data = {
        "name": applicant.name,
        "email": applicant.email,
        "sendEmail" : "yes",
        "startDateTime": format_date(start_test_date, test_time),
        "endDateTime": format_date(end_test_date, test_time),
        "timeZoneId": 1720,
        "ProctoringMode": "image",
    }
    response = requests.post(api_url, headers=headers, json=data)  

    try:
        response_data = response.json()
        history.test_id = response_data['testInvitationId']

        db.session.commit()
        flash('Test scheduled successfully.', 'success')

    except (ValueError, KeyError) as e:
        current_app.logger.error(f"Failed to parse response or missing testInvitationId: {e}")
        flash('Test scheduled but response could not be processed fully.', 'warning')

    return redirect(url_for('hr.view_applicant', id=applicant.id))

@bp.route('/schedule_linkid/<int:id>/<int:testId>/<testLinkId>/<start_test_date>/<test_time>/<end_test_date>', methods=['GET', 'POST'])   
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_linkid(id, testId, testLinkId, start_test_date, end_test_date, test_time):
    applicant= Applicant.query.get_or_404(id)
    history= RecruitmentHistory.query.filter_by(applicant_id=applicant.id).first()
    if history.test_id:
        flash('Test already scheduled for this applicant.', 'warning')
        return redirect(url_for('hr.view_applicant', id=applicant.id))
    history.test_date = start_test_date
    history.test_time = test_time
    data = {
        "name": applicant.name,
        "email": applicant.email,
        "sendEmail": "yes",
        "startDateTime": format_date(start_test_date, test_time),
        "endDateTime": format_date(end_test_date, test_time),
        "timeZoneId": 1720,
        "ProctoringMode": "image",
    }

    api_url = f"https://apiv3.imocha.io/v3/tests/{testId}/testlinks/{testLinkId}/invite"
    headers = {
        "X-API-KEY": "MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }

    response = requests.post(api_url, headers=headers, json=data)

    if response.status_code != 200:
        flash('Failed to schedule test with link. Please try again later.', 'error')
        current_app.logger.error(f"Failed to schedule test with link for applicant {applicant.id}: {response.text}")
    else:
        response_data = response.json()
        history = RecruitmentHistory.query.filter_by(applicant_id=applicant.id).first()
        if history:
            history.test_id = response_data.get('testInvitationId')
            db.session.commit()
        flash('Test scheduled successfully via link.', 'success')
        current_app.logger.info(f"Test scheduled (link) for applicant {applicant.id} by {current_user.username}")

    return redirect(url_for('hr.view_applicant', id=applicant.id))

#Convert to ISO Date format
def format_date(date_input, time_input):
    
    if isinstance(date_input, str):
        date_input = datetime.strptime(date_input, '%Y-%m-%d').date()
    if isinstance(time_input, str):
        time_input = datetime.strptime(time_input, '%H:%M:%S').time()

    dt = datetime.combine(date_input, time_input)

    local_tz = timezone('Asia/Kolkata')

    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(utc)

    return utc_dt.isoformat().replace('+00:00', 'Z')

@bp.route('/view_test_result/<int:id>')
@no_cache
@login_required
@role_required(*HR_ROLES)
def test_result(id):
    applicant= Applicant.query.get_or_404(id)
    history = RecruitmentHistory.query.filter_by(applicant_id=applicant.id).first()
    testInviteid = history.test_id
    api_url="https://apiv3.imocha.io/v3/reports/"+str(testInviteid)+"?reportType=1"
    headers = {
        "X-API-KEY": "MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        flash('Failed to fetch test results. Please try again later.', 'error')
        current_app.logger.error(f"Failed to fetch test results for applicant {id}: {response.text}")
        return redirect(url_for('hr.view_applicant', id=id))
    
    result = response.json()
    #check pass/fail criteria based on test result.
    if result['status'] == None:
        flash('Test still in progress. Please check back later.', 'warning')
        current_app.logger.info(f"Test result for applicant {id} is not complete.")
        return redirect(url_for('hr.view_applicant', id=id))
    
    else:
        history.test_result=True
        db.session.commit()
        return render_template('hr/test_result.html',id=id, result=result)

@bp.route('/available_interviewers', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def available_interviewers():
    date_str = request.args.get('date')
    time_str = request.args.get('time')

    if not date_str or not time_str:
        return jsonify([])

    try:
        interview_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if not is_future_or_today(interview_datetime.date()):
            return jsonify([])

        interviewers = User.query.filter_by(role='interviewer').all()
        interviewer_ids = [i.id for i in interviewers]

        scheduled_interviews = Interview.query.filter(
            Interview.date == interview_datetime.date(),
            Interview.interviewer_id.in_(interviewer_ids)
        ).all()

        busy_interviewers = set()

        for interview in scheduled_interviews:
            scheduled_datetime = datetime.combine(interview.date, interview.time)
            time_diff = abs((scheduled_datetime - interview_datetime))

            if time_diff < timedelta(hours=1):
                busy_interviewers.add(interview.interviewer_id)

        available_interviewers = [
            {"id": interviewer.id, "name": interviewer.name}
            for interviewer in interviewers
            if interviewer.id not in busy_interviewers
        ]

        return jsonify(available_interviewers)

    except ValueError:
        return jsonify([])
    
#View all applicants
@bp.route('/filter_all_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def filter_all_applicants():
    hr_users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    jobs = JobRequirement.query.order_by(JobRequirement.position).all()
    stages = ['Applied','On Hold','Offered','Joined','Rejected']
    page = request.args.get('page', 1, type=int)
    per_page = 20

    hr_id = request.args.get('hr_id', '')
    job_id = request.args.get('job_id', '')
    status_id = request.args.get('status', '')
    stage = request.args.get('all_stages','').strip()

    query = Applicant.query

    if hr_id:
        query = query.filter(Applicant.uploaded_by == int(hr_id))

    if job_id:
        query = query.filter(Applicant.job_id == int(job_id))

    if status_id == 'fresher':
        query = query.filter(Applicant.is_fresher == True)
    elif status_id == 'experienced':
        query = query.filter(Applicant.is_fresher == False)

    if stage:
        query = query.filter(Applicant.status==stage)

    applicants_pagination = query.order_by(Applicant.last_applied.desc()).paginate(page=page, per_page=per_page, error_out=False)
    applicants = applicants_pagination.items

    return render_template('hr/applicants_all.html', applicants=applicants, users=hr_users, jobs=jobs, all_stages=stages, selected_stage=stage, pagination=applicants_pagination)

@bp.route('/sort_all_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def sort_all_applicants():
    sort_by = request.args.get('sort_by', 'date')
    
    # Eager load uploader and job for display
    query = Applicant.query.options(
        joinedload(Applicant.uploader),
        joinedload(Applicant.job)
    )

    if sort_by == 'name':
        query = query.order_by(Applicant.name.asc())
    elif sort_by == 'hr':
        # join uploader explicitly and order by User.name
        query = query.join(Applicant.uploader).order_by(User.name.asc())
    else:  # Default to sorting by latest application
        query = query.order_by(Applicant.last_applied.desc())

    applicants = query.all()

    # For filter dropdowns
    users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    jobs = JobRequirement.query.all()

    return render_template(
        'hr/applicants_all.html',
        applicants=applicants,
        users=users,
        jobs=jobs,
        search_query='' 
    )

@bp.route('/search_all_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def search_all_applicants():
    search_query = request.args.get('query', '').strip()
    
    if not search_query:
        return redirect(url_for('hr.applicants'))
    
    if '@' in search_query:
        applicants = Applicant.query.filter(
            Applicant.email.ilike(f'%{search_query}%')
        ).options(joinedload(Applicant.uploader)).order_by(Applicant.last_applied.desc()).all()
    else:
        applicants = Applicant.query.filter(
            Applicant.name.ilike(f'%{search_query}%'),
        ).options(joinedload(Applicant.uploader)).order_by(Applicant.last_applied.desc()).all()
    
    
    jobs = JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    hrs = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    
    return render_template('hr/applicants_all.html', applicants=applicants, users=hrs, jobs=jobs, search_query=search_query)


@bp.route('/search_sort_filter_all_applicants', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def search_sort_filter_all_applicants():
    search_query = request.args.get('query', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    hr_id = request.args.get('hr_id', '')
    job_id = request.args.get('job_id', '')
    status_id = request.args.get('status', '')
    stage = request.args.get('all_stages', '').strip()

    query = Applicant.query.options(
        joinedload(Applicant.uploader),
        joinedload(Applicant.job)
    )

    # Apply search filter
    if search_query:
        if '@' in search_query:
            query = query.filter(Applicant.email.ilike(f'%{search_query}%'))
        else:
            query = query.filter(Applicant.name.ilike(f'%{search_query}%'))

    # Apply additional filters
    if hr_id:
        query = query.filter(Applicant.uploaded_by == int(hr_id))
    if job_id:
        query = query.filter(Applicant.job_id == int(job_id))
    if status_id == 'fresher':
        query = query.filter(Applicant.is_fresher == True)
    elif status_id == 'experienced':
        query = query.filter(Applicant.is_fresher == False)
    if stage:
        query = query.filter(Applicant.status == stage)

    # Apply sort filter
    if sort_by == 'name':
        query = query.order_by(Applicant.name.asc())
    elif sort_by == 'hr':
        query = query.join(Applicant.uploader).order_by(User.name.asc())
    else:
        query = query.order_by(Applicant.last_applied.desc())

    applicants_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    applicants = applicants_pagination.items

    # For the dropdowns (HR, Jobs)
    users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    jobs = JobRequirement.query.all()
    stages = ['Applied','On Hold','Offered','Joined','Rejected']
    selected_stage = stage

    return render_template(
        'hr/applicants_all.html',
        applicants=applicants,
        search_query=search_query,
        sort_by=sort_by,
        users=users,
        jobs=jobs,
        all_stages=stages,
        selected_stage=selected_stage,
        pagination=applicants_pagination
    )

@bp.route('/search_sort_filter_applicants', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def search_sort_filter_applicants():
    search_query = request.args.get('query', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    hr_id = request.args.get('hr_id', '')
    job_id = request.args.get('job_id', '')
    status_id = request.args.get('status', '')
    stage = request.args.get('all_stages', '').strip()

    query = Applicant.query.options(
        joinedload(Applicant.uploader),
        joinedload(Applicant.job)
    )

    # Apply search filter
    if search_query:
        if '@' in search_query:
            query = query.filter(Applicant.email.ilike(f'%{search_query}%'))
        else:
            query = query.filter(Applicant.name.ilike(f'%{search_query}%'))

    query = query.filter(~Applicant.status.in_(excluded_stages))

    # Apply additional filters
    if hr_id:
        query = query.filter(Applicant.uploaded_by == int(hr_id))
    if job_id:
        query = query.filter(Applicant.job_id == int(job_id))
    if status_id == 'fresher':
        query = query.filter(Applicant.is_fresher == True)
    elif status_id == 'experienced':
        query = query.filter(Applicant.is_fresher == False)
    if stage:
        query = query.filter(Applicant.status == stage)

    # Apply sort filter
    if sort_by == 'name':
        query = query.order_by(Applicant.name.asc())
    elif sort_by == 'hr':
        query = query.join(Applicant.uploader).order_by(User.name.asc())
    else:
        query = query.order_by(Applicant.last_applied.desc())

    applicants_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    applicants = applicants_pagination.items

    # For the dropdowns (HR, Jobs)
    users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    jobs = JobRequirement.query.all()
    stages = ['Applied','On Hold','Offered','Joined','Rejected']
    selected_stage = stage

    return render_template(
        'hr/applicants.html',
        applicants=applicants,
        search_query=search_query,
        sort_by=sort_by,
        users=users,
        jobs=jobs,
        all_stages=stages,
        selected_stage=selected_stage,
        pagination=applicants_pagination
    )




