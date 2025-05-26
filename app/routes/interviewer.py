from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.interviews import Interview
from app.models.applicants import Applicant

bp = Blueprint('interviewer', __name__, url_prefix='/interviewer')
INTERVIEWER_ROLES = ('interviewer', 'admin')

@bp.route('/dashboard')
@login_required
@role_required('interviewer')
def dashboard():
    return render_template('interviewer/dashboard.html')

@bp.route('/interviews')
@login_required
@role_required(*INTERVIEWER_ROLES)
def view_interviews():
    interviews = Interview.query.all()
    return render_template('interviewer/interviews.html', interviews=interviews)

@bp.route('/view_interviewee/<int:id>')
@login_required
@role_required(*INTERVIEWER_ROLES)
def view_interviewee(id):
    interviewee = Applicant.query.get_or_404(id)
    return render_template('interviewer/view_interviewee.html', interviewee=interviewee)

@bp.route('/interviews/submit', methods=['POST'])
@login_required
@role_required(*INTERVIEWER_ROLES)
def submit_feedback():
    if request.method == 'POST':
        feedback = request.form['feedback']