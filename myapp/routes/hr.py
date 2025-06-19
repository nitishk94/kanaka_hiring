from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.users import User
from myapp.models.applicants import Applicant
from myapp.models.recruitment_history import RecruitmentHistory
from myapp.models.interviews import Interview
from myapp.models.referrals import Referral
from myapp.models.jobrequirement import JobRequirement
from myapp.utils import can_update_applicant, validate_file, update_status, can_upload_applicant
from myapp.extensions import db
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta, timezone
from pytz import timezone, utc
import requests
import os

bp = Blueprint('hr', __name__, url_prefix='/hr')
HR_ROLES = ('hr', 'admin')

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
    applicants = Applicant.query.options(joinedload(Applicant.uploader)).order_by(Applicant.last_applied.desc()).all()
    jobs= JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    hrs = User.query.filter_by(role='hr').all()
    for applicant in applicants:
        update_status(applicant.id)
    return render_template('hr/applicants.html', applicants=applicants, users=hrs, jobs=jobs)
        

@bp.route('/upload_applicants', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def upload_applicants():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    referrer_names = [
        {'id': user.id, 'name': user.name} for user in User.query.filter_by(role='referrer').all()
    ]

    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()
    

    if request.method == 'POST':
        file = request.files.get('cv')
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('hr/upload.html', form_data=request.form)

        # Get all form data
        name = request.form.get('name')
        email = request.form.get('email')

        if not can_upload_applicant(email):
            flash('This candidate is under a 6-month freeze period. Please try later.', 'error')
            return redirect(url_for('hr.upload_applicants'))
        
        applicant = Applicant.query.filter_by(email=email).first()
        if applicant:
            applicant.last_applied = date.today()
            applicant.status = 'Applied'

        phone_number = request.form.get('phone_number')
        dob = request.form.get('dob')
        # Convert dob to date object if it's a string
        if isinstance(dob, str):
            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                # fallback for other formats or None
                dob = None
        gender = request.form.get('gender')
        marital_status = request.form.get('marital_status')
        native_place = request.form.get('native_place')
        current_location = request.form.get('current_location')
        work_location = request.form.get('work_location')
        
        # Professional Information
        is_fresher = bool(request.form.get('is_fresher'))
        job_id = request.form.get('position') if not is_fresher else None
        is_referred = bool(request.form.get('is_referred'))
        referred_by = int(request.form.get('referred_by')) if is_referred else None
        qualification = request.form.get('qualification')
        graduation_year = request.form.get('graduation_year')
        if graduation_year:
            graduation_year = int(graduation_year)
            
        # Internship Information
        current_internship = bool(request.form.get('current_internship'))
        internship_duration = request.form.get('internship_duration')
        if internship_duration:
            internship_duration = int(internship_duration)
        paid_internship = bool(request.form.get('paid_internship'))
        stipend = request.form.get('stipend')
        if stipend:
            stipend = int(stipend)
            
        referenced_from = request.form.get('referenced_from')
        linkedin_profile = request.form.get('linkedin_profile')
        github_profile = request.form.get('github_profile')
        
        # Current Employment Information (if not fresher)
        experience = request.form.get('experience')
        is_kanaka_employee = bool(request.form.get('is_kanaka_employee'))
        current_company = request.form.get('current_company')
        designation = request.form.get('designation')
        current_job_position = request.form.get('current_job_position')
        current_ctc = request.form.get('current_ctc')
        if current_ctc:
            current_ctc = int(current_ctc)
        expected_ctc = request.form.get('expected_ctc')
        if expected_ctc:
            expected_ctc = int(expected_ctc)
        notice_period = request.form.get('notice_period')
        if notice_period:
            notice_period = int(notice_period)
        tenure_at_current_company = request.form.get('tenure_at_current_company')
        current_offers_yes_no = bool(request.form.get('current_offers_yes_no'))
        current_offers_description = request.form.get('current_offers_description')
        reason_for_change = request.form.get('reason_for_change')
        comments = request.form.get('comments')

        # Handle file upload
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'applicants')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Create new applicant
        new_applicant = Applicant(
            name=name.title(),
            email=email,
            phone_number=phone_number,
            dob=dob,
            gender=gender,
            marital_status=marital_status,
            native_place=native_place.title() if native_place else None,
            current_location=current_location.title() if current_location else None,
            work_location=work_location.title() if work_location else None,
            graduation_year=graduation_year,
            is_fresher=is_fresher,
            qualification=qualification,
            current_internship=current_internship,
            internship_duration=internship_duration,
            paid_internship=paid_internship,
            stipend=stipend,
            experience=experience,
            referenced_from=referenced_from,
            linkedin_profile=linkedin_profile if linkedin_profile else ' ',
            github_profile=github_profile if github_profile else ' ',
            is_kanaka_employee=is_kanaka_employee,
            current_company=current_company,
            designation=designation,
            current_job_position=current_job_position.title() if current_job_position else None,
            current_ctc=current_ctc,
            expected_ctc=expected_ctc,
            notice_period=notice_period,
            tenure_at_current_company=tenure_at_current_company,
            current_offers_yes_no=current_offers_yes_no,
            current_offers_description=current_offers_description if current_offers_description else None,
            reason_for_change=reason_for_change if reason_for_change else 'Not Provided',
            comments=comments if comments else 'No comments',
            last_applied=date.today(),
            current_stage='Need to schedule test',
            cv_file_path=file_path,
            uploaded_by=current_user.id,
            is_referred=is_referred,
            referred_by=referred_by,
            job_id=job_id if job_id else None ,
        )
        
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
            current_app.logger.info(f"New applicant (Name: {new_applicant.name.title()}) added by {current_user.username}")
            return redirect(url_for('hr.upload_applicants'))
            
        except IntegrityError as e:
            db.session.rollback()
            if 'email' in str(e.orig):
                flash('This email is already registered. Please use a different one.', 'error')
            elif 'phone_number' in str(e.orig):
                flash('This phone number is already registered. Please use a different one.', 'error')
            else:
                flash('Database error. Please try again.', 'error')
            current_app.logger.error(f"IntegrityError creating applicant: {str(e)}")
            return render_template('hr/upload.html', referrer_names=referrer_names, form_data=request.form)

    return render_template('hr/upload.html', referrer_names=referrer_names, job_positions=job_positions)

@bp.route('/update_applicants/<int:id>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def update_applicant(id):
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    referrer_names = [
        {'id': user.id, 'name': user.name} for user in User.query.filter_by(role='referrer').all()
    ]

    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()
    applicant = Applicant.query.get_or_404(id)
    

    if request.method == 'POST':
        file = request.files.get('cv')
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('hr/upload.html', form_data=request.form)

        # Get all form data
        name = request.form.get('name')
        email = request.form.get('email')

        if not can_update_applicant(id,email):
            flash('This candidate email already exists or is under a 6-month freeze period. Please try later.', 'error')
            return redirect(url_for('hr.upload_applicants'))
        
        applicant = Applicant.query.filter_by(email=email).first()
        if applicant:
            applicant.last_applied = date.today()
            applicant.status = 'Applied'

        phone_number = request.form.get('phone_number')
        dob = request.form.get('dob')
        # Convert dob to date object if it's a string
        if isinstance(dob, str):
            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                # fallback for other formats or None
                dob = None
        gender = request.form.get('gender')
        marital_status = request.form.get('marital_status')
        native_place = request.form.get('native_place')
        current_location = request.form.get('current_location')
        work_location = request.form.get('work_location')
        
        # Professional Information
        is_fresher = bool(request.form.get('is_fresher'))
        job_id = request.form.get('position') if not is_fresher else None
        is_referred = bool(request.form.get('is_referred'))
        referred_by = int(request.form.get('referred_by')) if is_referred else None
        qualification = request.form.get('qualification')
        graduation_year = request.form.get('graduation_year')
        if graduation_year:
            graduation_year = int(graduation_year)
            
        # Internship Information
        current_internship = bool(request.form.get('current_internship'))
        internship_duration = request.form.get('internship_duration')
        if internship_duration:
            internship_duration = int(internship_duration)
        paid_internship = bool(request.form.get('paid_internship'))
        stipend = request.form.get('stipend')
        if stipend:
            stipend = int(stipend)
            
        referenced_from = request.form.get('referenced_from')
        linkedin_profile = request.form.get('linkedin_profile')
        github_profile = request.form.get('github_profile')
        
        # Current Employment Information (if not fresher)
        experience = request.form.get('experience')
        is_kanaka_employee = bool(request.form.get('is_kanaka_employee'))
        current_company = request.form.get('current_company')
        designation = request.form.get('designation')
        current_job_position = request.form.get('current_job_position')
        current_ctc = request.form.get('current_ctc')
        if current_ctc:
            current_ctc = int(current_ctc)
        expected_ctc = request.form.get('expected_ctc')
        if expected_ctc:
            expected_ctc = int(expected_ctc)
        notice_period = request.form.get('notice_period')
        if notice_period:
            notice_period = int(notice_period)
        tenure_at_current_company = request.form.get('tenure_at_current_company')
        current_offers_yes_no = bool(request.form.get('current_offers_yes_no'))
        current_offers_description = request.form.get('current_offers_description')
        reason_for_change = request.form.get('reason_for_change')
        comments = request.form.get('comments')

        if int(experience)<1:
            flash('Experience cannot be less than one','error')

        # Handle file upload
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'applicants')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        applicant.name=name.title()
        applicant.email=email
        applicant.phone_number=phone_number
        applicant.dob=dob
        applicant.gender=gender
        applicant.marital_status=marital_status
        applicant.native_place=native_place.title() if native_place else None
        applicant.current_location=current_location.title() if current_location else None
        applicant.work_location=work_location.title() if work_location else None
        applicant.graduation_year=graduation_year
        applicant.is_fresher=is_fresher
        applicant.qualification=qualification
        applicant.current_internship=current_internship
        applicant.internship_duration=internship_duration
        applicant.paid_internship=paid_internship
        applicant.stipend=stipend
        applicant.experience=experience
        applicant.referenced_from=referenced_from
        applicant.linkedin_profile=linkedin_profile if linkedin_profile else ' '
        applicant.github_profile=github_profile if github_profile else ' '
        applicant.is_kanaka_employee=is_kanaka_employee
        applicant.current_company=current_company
        applicant.designation=designation
        applicant.current_job_position=current_job_position.title() if current_job_position else None
        applicant.current_ctc=current_ctc
        applicant.expected_ctc=expected_ctc
        applicant.notice_period=notice_period
        applicant.tenure_at_current_company=tenure_at_current_company
        applicant.current_offers_yes_no=current_offers_yes_no
        applicant.current_offers_description=current_offers_description if current_offers_description else None
        applicant.reason_for_change=reason_for_change if reason_for_change else 'Not Provided'
        applicant.comments=comments if comments else 'No comments'
        applicant.job_id=job_id if job_id else None
        applicant.is_referred=is_referred
        applicant.referred_by=referred_by
        
        try:
            db.session.commit()

            flash('Applicant details successfully updated!', 'success')
            current_app.logger.info(f"Applicant (Name: {applicant.name.title()}) details updates by {current_user.username}")
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
            return render_template('hr/view_applicant.html', referrer_names=referrer_names, form_data=request.form)

    return render_template('hr/update_applicant.html', applicant=applicant, job_positions=job_positions, referrer_names=referrer_names)


@bp.route('/view_applicant/<int:id>')
@no_cache
@login_required
@role_required(*HR_ROLES)
def view_applicant(id):
    update_status(id)
    applicant = Applicant.query.get_or_404(id)
    interviewers = User.query.filter_by(role='interviewer').all()

    return render_template('hr/view_applicant.html', applicant=applicant, interviewers=interviewers)

@no_cache
@login_required
@role_required(*HR_ROLES)
def view_applicant(id):
    applicant = Applicant.query.get_or_404(id)
    interviewers = User.query.filter_by(role='interviewer').all()

    return render_template('hr/view_applicant.html', applicant=applicant, interviewers=interviewers)

@bp.route('/reschedule_test/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def reschedule_test(id):
    date = request.form.get('retest_date')
    time = request.form.get('retest_time')
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            date = None
    
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    if history and history.test_result is None:
        history.test_date = date
        history.test_time = time
        db.session.commit()
        flash('Test rescheduled successfully', 'success')
        current_app.logger.info(f"Test rescheduled for applicant {id} to {date} by {current_user.username}")
    else:
        flash('Cannot reschedule test - test result already exists', 'error')
        
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/filter_applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def filter_applicants():
    hr_users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    
    hr_id = request.args.get('hr_id', '')
    job_id = request.args.get('job_id', '')
    status_id = request.args.get('status', '')
    
    query = Applicant.query

    if hr_id:
        query = query.filter(Applicant.uploaded_by == int(hr_id))

    if job_id:

        query = query.filter(Applicant.job_id.isnot(None))

    jobs = (
        JobRequirement.query.filter_by(id=job_id).order_by(JobRequirement.position).all()
        if job_id else
        JobRequirement.query.order_by(JobRequirement.position).all()
    )
    

    if status_id == 'fresher':
        query = query.filter(Applicant.is_fresher == True)
    elif status_id == 'experienced':
        query = query.filter(Applicant.is_fresher == False)

    applicants = query.order_by(Applicant.last_applied.desc()).all()
    return render_template('hr/applicants.html', applicants=applicants, users=hr_users, jobs=jobs)

@bp.route('/applicants/<int:id>/download_cv')
@no_cache
@login_required
@role_required(*HR_ROLES)
def download_cv(id):
    return f"Download CV for Applicant {id}"

@bp.route('/schedule_interview/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_interview(id):
    date = request.form.get('interview_date')
    time = request.form.get('interview_time')
    interviewer_id = request.form.get('interviewer_id')

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
    
    history = RecruitmentHistory.query.filter_by(applicant_id = id).first()

    if not history.interview_round_1_date:
        round = 1
        interview = Interview(applicant_id=id, date=date, time=time, round_number=round, interviewer_id=interviewer_id)
        db.session.add(interview)
        db.session.commit()
        history.interview_round_1_date = date
        history.interview_round_1_time = time
        
    elif not history.interview_round_2_date:
        round = 2
        interview = Interview(applicant_id=id, date=date, time=time, round_number=round, interviewer_id=interviewer_id)
        db.session.add(interview)
        db.session.commit()
        history.interview_round_2_date = date
        history.interview_round_2_time = time
        
    else:
        round = 3
        interview = Interview(applicant_id=id, date=date, time=time, round_number=round, interviewer_id=interviewer_id)
        db.session.add(interview)
        db.session.commit()
        history.hr_round_date = date
        history.hr_round_time = time
        
    db.session.commit()
    flash('Interview scheduled successfully', 'success')
    current_app.logger.info(f"Interview round {round} scheduled for applicant {id} on {date} by {current_user.username}")
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
    jobs= JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    return render_template('hr/view_referrals.html', referrals=referrals,jobs=jobs)

@bp.route('/filter_referrals')
@no_cache
@login_required
def filter_referrals():
    referral_id = request.args.get('referral_id')
    job_id = request.args.get('job_id')
    referral_users = User.query.filter_by(role='referral').all()


    query = JobRequirement.query

    # Apply HR filter if provided
    if referral_id:
        query = query.filter(Referral.id == referral_id)
    

    # Apply Status filter if provided
    if job_id:
        jobs = JobRequirement.query.filter_by(id=job_id).order_by(JobRequirement.position).all()
    else:
        jobs = JobRequirement.query.order_by(JobRequirement.position).all()

    # Fetch results
    jobs = query.order_by(JobRequirement.id.desc()).all()
   
    return render_template('hr/view_referrals.html', jobs=jobs, users=referral_users)

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
def filter_interviews():
    hr_users = User.query.filter_by(role='hr').all()
    
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

@bp.route('/reschedule_interview/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def reschedule_interview(id):
    date = request.form.get('interview_date')
    time = request.form.get('interview_time')
    interviewer_id = request.form.get('interviewer_id')

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
    
    interview = Interview.query.get_or_404(id)
    
    interview.date = date
    interview.time = time
    interview.interviewer_id = interviewer_id
    
    history = RecruitmentHistory.query.filter_by(applicant_id=interview.applicant_id).first()
    if interview.round_number == 1:
        history.interview_round_1_date = date
        history.interview_round_1_time = time
    elif interview.round_number == 2:
        history.interview_round_2_date = date
        history.interview_round_2_time = time
    else:
        history.hr_round_date = date
        history.hr_round_time = time
    
    db.session.commit()
    flash('Interview rescheduled successfully', 'success')
    current_app.logger.info(f"Interview round {interview.round_number} rescheduled for applicant {interview.applicant_id} to {date} by {current_user.username}")
    
    referrer = request.referrer
    if referrer and 'view_interviews' in referrer:
        return redirect(url_for('hr.view_interviews'))
    return redirect(url_for('hr.view_applicant', id=interview.applicant_id))

@bp.route('/upload_joblistings', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def upload_joblistings():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    job_position = request.form.get('position_name') 
    job_description = request.form.get('job_description')
    job_skillset= request.form.get('job_skillset')
    job_clients = request.form.get('job_clients')
    job_budget = request.form.get('job_budget')
    job_experience = request.form.get('job_experience')  

    new_jobrequirement = JobRequirement(
        position=job_position,
        description=job_description,
        created_by=current_user,
        skillset=job_skillset,
        clients=job_clients,
        budget=job_budget,
        experience=job_experience
    )

    if not job_position or not job_description:
        return render_template('hr/addjob.html', form_data=request.form)

    db.session.add(new_jobrequirement)
    db.session.commit()

    flash('New job listing successfully created!', 'success')
    current_app.logger.info(f"New job listing (Posting: {new_jobrequirement.position}) added by {current_user.name}")
    
    return redirect(url_for('main.view_joblisting'))

@bp.route('/update_joblisting/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('hr', 'admin')
def joblisting_update(id):
    job = JobRequirement.query.get_or_404(id)

    if request.method == 'POST':
        position = request.form.get('job_position')
        description = request.form.get('job_description')
        skillset= request.form.get('job_skillset')
        clients = request.form.get('job_clients')
        budget = request.form.get('job_budget')
        experience = request.form.get('job_experience')  

        job.position = position
        job.description = description
        job.skillset = skillset
        job.clients = clients       
        job.budget = budget
        job.experience = experience

        db.session.commit()
        flash('Job listing updated successfully!', 'success')
        return redirect(url_for('main.view_details_joblisting', id=id ))

    return render_template('hr/detailsjob.html', joblisting=job)

@bp.route('/close_joblisting/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def close_joblisting(id):
    joblisting = JobRequirement.query.get_or_404(id)
    joblisting.is_open = False
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


@bp.route('/schedule_test/<int:id>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_test(id):
    applicant = Applicant.query.get_or_404(id)

    if request.method == 'POST':
        start_date = request.form.get('start_test_date')
        time = request.form.get('test_time')
        end_date=request.form.get('end_test_date')
        test_id = request.form.get('test_id')
        test_link = request.form.get('test_link')

        if not test_link:
            return redirect(url_for('hr.schedule_default',id=id,testId=test_id,start_test_date=start_date,end_test_date=end_date,test_time=time))
        else:
            return redirect(url_for('hr.schedule_linkid',id=id,testId=test_id,testLinkId=test_link,start_test_date=start_date,end_test_date=end_date,test_time=time))

    
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
        time_input = datetime.strptime(time_input, '%H:%M').time()

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
    if result['status'] == 'Complete' or result['status']=='TestLeft' or result['status']=='None':
        return render_template('hr/test_result.html',id=id, result=result)
    
    else:
        flash('Test still in progress. Please check back later.', 'warning')
        current_app.logger.info(f"Test result for applicant {id} is not complete.")
        return redirect(url_for('hr.view_applicant', id=id))
    
    
@no_cache
@login_required
@role_required(*HR_ROLES)
def get_status(data):
    status=data['status']
    if status == 'Complete':
        testInvitationId=data['testInvitationId']
        return test_result(testInvitationId)

#@bp.route('/api/callback', methods=['POST'])
#@no_cache
#@login_required
#def api_callback():
   # data = request.json
    #get_status(data)
    #return jsonify({"status": "received"}), 200



