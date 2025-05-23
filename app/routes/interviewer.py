from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.auth.decorators import role_required

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
    return "View Interviews Page"

@bp.route('/interviews/submit', methods=['POST'])
@login_required
@role_required(*INTERVIEWER_ROLES)
def submit_feedbacks():
    return f"Submit Feedback for Applicant"