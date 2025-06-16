from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.users import User
from myapp.models.applicants import Applicant
from myapp.models.recruitment_history import RecruitmentHistory
from myapp.models.interviews import Interview
from myapp.models.referrals import Referral
from myapp.models.jobrequirement import JobRequirement
from myapp.utils import validate_file, update_status, can_upload_applicant
from myapp.extensions import db
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import requests
import os
import tempfile

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
        

@bp.route('/upload_applicants', methods=['GET'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def show_upload_form():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401

    referrer_names = [
        {'id': user.id, 'name': user.name} for user in User.query.filter_by(role='referrer').all()
    ]
    job_positions = JobRequirement.query.with_entities(JobRequirement.id, JobRequirement.position).filter(JobRequirement.is_open == True).all()

    return render_template('hr/upload.html', referrer_names=referrer_names, job_positions=job_positions)

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
        return redirect(url_for('hr.show_upload_form'))

    email = request.form.get('email')
    if not can_upload_applicant(email):
        flash('This candidate is under a 6-month freeze period. Please try later.', 'error')
        return redirect(url_for('hr.show_upload_form'))

    applicant = Applicant.query.filter_by(email=email).first()
    if applicant:
        applicant.last_applied = date.today()
        applicant.status = 'Applied'

    # Collect and process form data
    def get_bool(key): return bool(request.form.get(key))

    try:
        dob = request.form.get('dob')
        dob = datetime.strptime(dob, '%Y-%m-%d').date() if dob else None
    except ValueError:
        dob = None

    # Convert relevant fields
    int_or_none = lambda x: int(x) if x else None

    new_applicant = Applicant(
        name=request.form.get('name').title(),
        email=email,
        phone_number=request.form.get('phone_number'),
        dob=dob,
        gender=request.form.get('gender'),
        marital_status=request.form.get('marital_status'),
        native_place=request.form.get('native_place', '').title(),
        current_location=request.form.get('current_location', '').title(),
        work_location=request.form.get('work_location', '').title(),
        graduation_year=int_or_none(request.form.get('graduation_year')),
        is_fresher=get_bool('is_fresher'),
        qualification=request.form.get('qualification'),
        current_internship=get_bool('current_internship'),
        internship_duration=int_or_none(request.form.get('internship_duration')),
        paid_internship=get_bool('paid_internship'),
        stipend=int_or_none(request.form.get('stipend')),
        experience=request.form.get('experience'),
        referenced_from=request.form.get('referenced_from'),
        linkedin_profile=request.form.get('linkedin_profile') or 'Not Provided',
        github_profile=request.form.get('github_profile') or 'Not Provided',
        is_kanaka_employee=get_bool('is_kanaka_employee'),
        current_company=request.form.get('current_company'),
        designation=request.form.get('designation'),
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
        current_stage='Need to schedule test',
        uploaded_by=current_user.id,
        is_referred=get_bool('is_referred'),
        referred_by=int_or_none(request.form.get('referred_by')) if get_bool('is_referred') else None,
        job_id=request.form.get('position') if not get_bool('is_fresher') else None,
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
        return redirect(url_for('hr.show_upload_form'))

@bp.route('/view_applicant/<int:id>')
@no_cache
@login_required
@role_required(*HR_ROLES)
def view_applicant(id):
    update_status(id)
    applicant = Applicant.query.get_or_404(id)
    interviewers = User.query.filter_by(role='interviewer').all()

    return render_template('hr/view_applicant.html', applicant=applicant, interviewers=interviewers)

@bp.route('/schedule_test/<int:id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def schedule_test(id):
    date = request.form.get('test_date')
    time = request.form.get('test_time')

    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            date = None

    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    history.test_date = date
    history.test_time = time
    history.test_date = date
    db.session.commit()
    flash('Test scheduled successfully', 'success')
    current_app.logger.info(f"Test scheduled for applicant {id} on {date} by {current_user.username}")
    return redirect(url_for('hr.view_applicant', id=id))

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
        history.test_date = date
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
        jobs = JobRequirement.query.filter_by(id=job_id).order_by(JobRequirement.position).all()
    else:
        jobs = JobRequirement.query.order_by(JobRequirement.position).all()

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
    if "token" not in session:
        flash("You must be logged in through Microsoft to schedule interviews.", "error")
        return redirect(url_for('auth.login'))
    
    access_token = session["token"]["access_token"]
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
    
    if not date or not time:
        flash('Invalid date or time format.', 'error')
        return redirect(url_for('hr.view_applicant', id=id))
    
    applicant = Applicant.query.get_or_404(id)
    interviewer = User.query.get_or_404(interviewer_id)
    history = RecruitmentHistory.query.filter_by(applicant_id = id).first()
    start_datetime = datetime.combine(date, time)
    end_datetime = start_datetime + timedelta(hours=1)

    if not history.interview_round_1_date:
        round = 1
        history.interview_round_1_date = date
        history.interview_round_1_time = time
    elif not history.interview_round_2_date:
        round = 2
        history.interview_round_2_date = date
        history.interview_round_2_time = time
    else:
        round = 3
        history.hr_round_date = date
        history.hr_round_time = time
    
    existing = Interview.query.filter_by(applicant_id=id, round_number=round).first()
    if existing:
        flash("This interview round has already been scheduled.", "warning")
        return redirect(url_for('hr.view_applicant', id=id))

    interview = Interview(
        applicant_id=id,
        date=date,
        time=time,
        round_number=round,
        interviewer_id=interviewer_id
    )
    db.session.add(interview)
    db.session.commit()

    graph_endpoint = 'https://graph.microsoft.com/v1.0/me/events'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    body = {
        "subject": f"Interview Round {'HR' if round == 3 else round} with {applicant.name}",
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
        "attendees": [
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
        ],
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    response = requests.post(graph_endpoint, headers=headers, json=body)

    if response.status_code == 201:
        flash('Interview scheduled and calendar invite sent.', 'success')
        current_app.logger.info(f"Meeting created for round {'HR' if round == 3 else round} for applicant {id}")
    else:
        flash('Interview saved, but failed to schedule calendar meeting.', 'warning')
        current_app.logger.error(f"Graph API error: {response.status_code}, {response.text}")

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
    return render_template('hr/view_referrals.html', referrals=referrals)

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
    if "token" not in session:
        flash("You must be logged in through Microsoft to schedule interviews.", "error")
        return redirect(url_for('auth.login'))
    
    access_token = session["token"]["access_token"]
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
    
    applicant = Applicant.query.get_or_404(id=interview.applicant_id)
    interviewer = User.query.get_or_404(interviewer_id)
    history = RecruitmentHistory.query.filter_by(applicant_id = applicant.id).first()
    start_datetime = datetime.combine(date, time)
    end_datetime = start_datetime + timedelta(hours=1)

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

    graph_endpoint = 'https://graph.microsoft.com/v1.0/me/events'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    body = {
        "subject": f"Rescheduled Interview Round {'HR' if round == 3 else round} with {applicant.name}",
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
        "attendees": [
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
        ],
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    response = requests.post(graph_endpoint, headers=headers, json=body)

    if response.status_code == 201:
        flash('Interview scheduled and calendar invite sent.', 'success')
        current_app.logger.info(f"Meeting created for round {'HR' if round == 3 else round} for applicant {id}")
    else:
        flash('Interview rescheduling saved, but failed to schedule calendar meeting.', 'warning')
        current_app.logger.error(f"Graph API error: {response.status_code}, {response.text}")

    referrer = request.referrer
    if referrer and 'view_interviews' in referrer:
        return redirect(url_for('hr.view_interviews'))
    return redirect(url_for('hr.view_applicant', id=applicant.id))

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

    if not job_position or not job_description:
        return render_template('hr/addjob.html', form_data=request.form)

    new_jobrequirement = JobRequirement(
        position=job_position,
        description=job_description,
        created_by=current_user,
        skillset=job_skillset,
        clients=job_clients,
        budget=job_budget,
        experience=job_experience
    )

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

        if not position or not description:
            flash('Job position and description cannot be empty!', 'error')
            return redirect(url_for('hr.joblisting_update', id=id))

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