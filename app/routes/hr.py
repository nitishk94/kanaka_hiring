from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.applicants import Applicant


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
    return render_template('hr/applicants.html', applicants=applicants)

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

@bp.route('/applicants/<int:id>/status', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
def update_status(id):
    return f"Update Status for Applicant {id}"

@bp.route('/interviews/schedule', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
def schedule_interview():
    return "Schedule Interview"

@bp.route('/interviews/track')
@login_required
@role_required(*HR_ROLES)
def track_interviews():
    return "Interview Tracking Page"

@bp.route('/feedback/<int:id>')
@login_required
@role_required(*HR_ROLES)
def view_feedback(id):
    return f"View Feedback for Applicant {id}"

@bp.route('/onboarding')
@login_required
@role_required(*HR_ROLES)
def onboarding():
    return "Onboarding and Offer Letter Page"
