from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.applicants import Applicant
from app.models.recruitment_history import RecruitmentHistory
from app.models.interviews import Interview
from app.models.users import User
from app.extensions import db

bp = Blueprint('hr', __name__, url_prefix='/hr')
HR_ROLES = ('hr', 'admin')

@bp.route('/dashboard')
@login_required
@role_required(*HR_ROLES)
def dashboard():
    return render_template('hr/dashboard.html')

@bp.route('/applicants')
@login_required
@role_required(*HR_ROLES)
def applicants():
    applicants = Applicant.query.order_by(Applicant.applied_date.desc()).all()
    return render_template('applicants.html', candidates=applicants)

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
    return redirect(url_for('main.view_applicant', id=id))

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
    interviewer_id = request.form['interviewer_id']
    history = RecruitmentHistory.query.filter_by(applicant_id = id).first()

    if not history.interview_round_1:
        history.interview_round_1 = date
        round = 1
        interview = Interview(applicant_id=id, date=date, round_number=round, interviewer_id=interviewer_id)
        db.session.add(interview)
    elif not history.interview_round_2:
        history.interview_round_2 = date
        round = 2
        interview = Interview(applicant_id=id, date=date, round_number=round, interviewer_id=interviewer_id)
        db.session.add(interview)
    else:
        history.hr_round = date
        round = 'HR'
        interview = Interview(applicant_id=id, date=date, round_number=round, interviewer_id=interviewer_id)
        db.session.add(interview)
    db.session.commit()
    flash('Interview scheduled successfully', 'success')
    current_app.logger.info(f"Interview round {round} scheduled for applicant {id} on {date} by {current_user.username}")
    return redirect(url_for('main.view_applicant', id=id))

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
    return redirect(url_for('main.view_applicant', id=id))

@bp.route('/onboarding')
@login_required
@role_required(*HR_ROLES)
def onboarding():
    return "Onboarding and Offer Letter Page"
