from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from app.auth.decorators import role_required, no_cache
from app.models.users import User
from app.models.applicants import Applicant
from app.models.recruitment_history import RecruitmentHistory
from app.models.interviews import Interview
from app.models.referrals import Referral
from app.utils import validate_file, update_status
from app.extensions import db
from werkzeug.utils import secure_filename
from datetime import date
import os

bp = Blueprint('hr', __name__, url_prefix='/hr')
HR_ROLES = ('hr', 'admin')

@bp.route('/dashboard')
@no_cache
@login_required
@role_required(*HR_ROLES)
def dashboard():
    return render_template('hr/dashboard.html')

@bp.route('/applicants')
@no_cache
@login_required
@role_required(*HR_ROLES)
def applicants():
    if current_user.role == 'hr':
        applicants = Applicant.query.filter_by(uploaded_by=current_user.id).order_by(Applicant.applied_date.desc()).all()
        for applicant in applicants:
            update_status(applicant.id)
        return render_template('hr/applicants.html', applicants=applicants)
    else:
        applicants = Applicant.query.order_by(Applicant.applied_date.desc()).all()
        hrs = User.query.filter_by(role='hr').all()
        for applicant in applicants:
            update_status(applicant.id)
        return render_template('hr/applicants.html', applicants=applicants, users=hrs)

@bp.route('/upload_applicants', methods=['GET', 'POST'])
@login_required
@role_required(*HR_ROLES)
def upload_applicants():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
        
    if request.method == 'POST':
        file = request.files.get('cv')
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('hr/upload.html', form_data=request.form)

        # Get all form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        dob = request.form.get('dob')
        gender = request.form.get('gender')
        marital_status = request.form.get('marital_status')
        location = request.form.get('location')
        
        # Professional Information
        is_fresher = request.form.get('is_fresher') == 'yes'
        is_referred = request.form.get('is_referred') == 'yes'
        referred_by = request.form.get('referred_by')
        qualification = request.form.get('qualification')
        referenced_from = request.form.get('referenced_from')
        linkedin_profile = request.form.get('linkedin')
        github_profile = request.form.get('github')
        
        # Current Employment Information (if not fresher)
        experience = request.form.get('experience')
        is_kanaka_employee = request.form.get('is_kanaka_employee') == 'yes'
        current_company = request.form.get('current_company')
        designation = request.form.get('designation')
        current_job_position = request.form.get('job_position')
        current_ctc = request.form.get('current_ctc')
        expected_ctc = request.form.get('expected_ctc')
        notice_period = request.form.get('notice_period')
        tenure_at_current_company = request.form.get('tenure')
        current_offers = request.form.get('current_offers', 0)
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
            location=location.title(),
            is_fresher=is_fresher,
            qualification=qualification,
            experience=experience,
            referenced_from=referenced_from,
            linkedin_profile=linkedin_profile if linkedin_profile else 'Not Provided',
            github_profile=github_profile if github_profile else 'Not Provided',
            is_kanaka_employee=is_kanaka_employee,
            current_company=current_company,
            designation=designation,
            current_job_position=current_job_position.title() if current_job_position else None,
            current_ctc=current_ctc,
            expected_ctc=int(expected_ctc) if expected_ctc else None,
            notice_period=notice_period,
            tenure_at_current_company=tenure_at_current_company,
            current_offers=int(current_offers) if current_offers else None,
            reason_for_change=reason_for_change if reason_for_change else 'Not Provided',
            comments=comments if comments else 'No comments',
            applied_date=date.today(),
            current_stage='Need to schedule test',
            cv_file_path=file_path,
            uploaded_by=current_user.id,
            is_referred=is_referred,
            referred_by=referred_by if is_referred else None
        )
        
        try:
            db.session.add(new_applicant)
            db.session.commit()
            
            history = RecruitmentHistory(
                applicant_id=new_applicant.id
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
            return render_template('hr/upload.html', form_data=request.form)

    return render_template('hr/upload.html')

@bp.route('/view_applicant/<int:id>')
@login_required
@role_required(*HR_ROLES)
def view_applicant(id):
    update_status(id)
    applicant = Applicant.query.get_or_404(id)
    interviewers = User.query.filter_by(role='interviewer').all()

    return render_template('hr/view_applicant.html', applicant=applicant, interviewers=interviewers)

@bp.route('/schedule_test/<int:id>', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
def schedule_test(id):
    date = request.form['test_date']

    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    history.test_scheduled = date
    db.session.commit()
    flash('Test scheduled successfully', 'success')
    current_app.logger.info(f"Test scheduled for applicant {id} on {date} by {current_user.username}")
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/reschedule_test/<int:id>', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
def reschedule_test(id):
    date = request.form['test_date']
    
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    if history and history.test_result is None:
        history.test_scheduled = date
        db.session.commit()
        flash('Test rescheduled successfully', 'success')
        current_app.logger.info(f"Test rescheduled for applicant {id} to {date} by {current_user.username}")
    else:
        flash('Cannot reschedule test - test result already exists', 'error')
        
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/applicants/filter')
@login_required
@role_required(*HR_ROLES)
def filter_applicants():
    return "Filter Applicants"

@bp.route('/applicants/<int:id>/download_cv')
@login_required
@role_required(*HR_ROLES)
def download_cv(id):
    return f"Download CV for Applicant {id}"

@bp.route('/schedule_interview/<int:id>', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
def schedule_interview(id):
    date = request.form['interview_date']
    time = request.form['interview_time']
    interviewer_id = request.form['interviewer_id']
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
@login_required
@role_required(*HR_ROLES)
def reject_application(id):
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    history.rejected = True
    applicant = Applicant.query.get_or_404(id)
    db.session.commit()
    current_app.logger.info(f"Candidate {applicant.name} rejected")
    flash('Candidate rejected', 'error')
    return redirect(url_for('hr.view_applicant', id=id))

@bp.route('/view_referrals')
@login_required
@role_required(*HR_ROLES)
def view_referrals():
    referrals = Referral.query.all()
    return render_template('hr/view_referrals.html', referrals=referrals)

@bp.route('/onboarding')
@login_required
@role_required(*HR_ROLES)
def onboarding():
    return "Onboarding and Offer Letter Page"

@bp.route('/filter_interviews')
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
@login_required
@role_required(*HR_ROLES)
def reschedule_interview(id):
    date = request.form['interview_date']
    time = request.form['interview_time']
    interviewer_id = request.form['interviewer_id']
    
    # Find the interview to reschedule
    interview = Interview.query.get_or_404(id)
    
    # Update the interview details
    interview.date = date
    interview.time = time
    interview.interviewer_id = interviewer_id
    
    # Update the corresponding history entry
    history = RecruitmentHistory.query.filter_by(applicant_id=interview.applicant_id).first()
    if interview.round_number == 1:
        history.interview_round_1_date = date
        history.interview_round_1_time = time
    elif interview.round_number == 2:
        history.interview_round_2_date = date
        history.interview_round_2_time = time
    else:  # HR round
        history.hr_round_date = date
        history.hr_round_time = time
    
    db.session.commit()
    flash('Interview rescheduled successfully', 'success')
    current_app.logger.info(f"Interview round {interview.round_number} rescheduled for applicant {interview.applicant_id} to {date} by {current_user.username}")
    
    # Determine which page to redirect back to based on the referrer
    referrer = request.referrer
    if referrer and 'view_interviews' in referrer:
        return redirect(url_for('hr.view_interviews'))
    return redirect(url_for('hr.view_applicant', id=interview.applicant_id))
