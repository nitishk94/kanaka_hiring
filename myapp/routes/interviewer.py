from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.interviews import Interview
from myapp.models.applicants import Applicant
from myapp.models.users import User
from myapp.models.jobrequirement import JobRequirement
from myapp.models.recruitment_history import RecruitmentHistory
from myapp.extensions import db
from sqlalchemy.orm import joinedload

bp = Blueprint('interviewer', __name__, url_prefix='/interviewer')
INTERVIEWER_ROLES = ('interviewer', 'admin')

@bp.route('/dashboard')
@no_cache
@login_required
@role_required('interviewer')
def dashboard():
    return render_template('interviewer/dashboard.html')

@bp.route('/interviews')
@no_cache
@login_required
@role_required(*INTERVIEWER_ROLES, 'hr')
def view_interviews():
    jobs= JobRequirement.query.filter(JobRequirement.is_open == True).order_by(JobRequirement.position).all()
    if current_user.role == 'interviewer':
        interviews = Interview.query.filter_by(interviewer_id=current_user.id).filter_by(completed=False).all()
        applicant_ids = [interview.applicant_id for interview in interviews]
        applicants = Applicant.query.filter(Applicant.id.in_(applicant_ids)).all()
        return render_template('interviewer/interviews.html', interviews=interviews, applicants=applicants)
    else:
        hr_users = User.query.filter_by(role='hr').all()
        interviewers = User.query.filter_by(role='interviewer').all()
        interviews = Interview.query\
            .filter_by(completed=False)\
            .options(
                joinedload(Interview.applicant),
                joinedload(Interview.interviewer),
                joinedload(Interview.scheduler)
            )\
            .all()

        return render_template('hr/view_interviews.html',jobs=jobs ,interviews=interviews, users=hr_users, interviewers=interviewers)

@bp.route('/view_interviewee/<int:id>')
@no_cache
@login_required
@role_required(*INTERVIEWER_ROLES)
def view_interviewee(id):
    interviewee = Applicant.query.get_or_404(id)
    return render_template('interviewer/interviewee.html', applicant=interviewee)

@bp.route('/submit_feedback/<int:id>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*INTERVIEWER_ROLES)
def submit_feedback(id):
    feedback = request.form.get('feedback')
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    interview = Interview.query.filter_by(applicant_id=id).filter_by(interviewer_id=current_user.id).filter_by(completed=False).first()

    if history.interview_round_1_comments is None:
        history.interview_round_1_comments = feedback
        interview.completed = True
        flash('Feedback submitted successfully', 'success')
        current_app.logger.info(f"Feedback submitted for applicant {id} by {current_user.username}")
    elif history.interview_round_2_comments is None:
        history.interview_round_2_comments = feedback
        interview.completed = True
        flash('Feedback submitted successfully', 'success')
        current_app.logger.info(f"Feedback submitted for applicant {id} by {current_user.username}")
    else:
        history.hr_round_comments = feedback
        interview.completed = True
        flash('Feedback submitted successfully', 'success')
        current_app.logger.info(f"Feedback submitted for applicant {id} by {current_user.username}")

    db.session.commit()
    return redirect(url_for('interviewer.view_interviews'))