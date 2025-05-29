from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.auth.decorators import role_required, no_cache
from app.models.interviews import Interview
from app.models.applicants import Applicant
from app.models.recruitment_history import RecruitmentHistory
from app.extensions import db

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
@role_required(*INTERVIEWER_ROLES)
def view_interviews():
    interviews = Interview.query.filter_by(interviewer_id=current_user.id).filter_by(completed=False).all()
    applicant_ids = [interview.applicant_id for interview in interviews]
    applicants = Applicant.query.filter(Applicant.id.in_(applicant_ids)).all()
    print(applicants)
    return render_template('interviewer/interviews.html', interviews=interviews, applicants=applicants)

@bp.route('/view_interviewee/<int:id>')
@login_required
@role_required(*INTERVIEWER_ROLES)
def view_interviewee(id):
    interviewee = Applicant.query.get_or_404(id)
    return render_template('interviewer/interviewee.html', applicant=interviewee)

@bp.route('/submit_feedback/<int:id>', methods=['GET', 'POST'])
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