from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from myapp.extensions import db
from myapp.models import User  
from myapp.auth.decorators import role_required, no_cache
from myapp.models.applicants import Applicant
from myapp.models.jobrequirement import JobRequirement
from myapp.utils import generate_timeline, update_status

bp = Blueprint('main', __name__)

@bp.route('/')
@no_cache
def home():
    return render_template('home.html')

@bp.route('/profile')
@no_cache
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@bp.route('/track/<int:id>', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required('hr', 'admin', 'referrer')
def track_status(id):
    update_status(id)
    timeline = generate_timeline(id)
    applicant = Applicant.query.get_or_404(id)
    return render_template('track.html', timeline=timeline, applicant=applicant)

@bp.route('/check_session')
def check_session():
    return jsonify({'active': current_user.is_authenticated})

# Job Listing Routes
@bp.route('/view_joblisting')
@no_cache
@login_required
def view_joblisting():
    jobs = JobRequirement.query.options(joinedload(JobRequirement.created_by)).order_by(JobRequirement.job_id.desc()).all()
    hr_users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    return render_template('viewjobs.html', jobs=jobs, users=hr_users)

@bp.route('/filter_joblistings')
@no_cache
@login_required
def filter_joblistings():
    hr_users = User.query.filter(User.role.in_(['hr', 'admin'])).all()
    
    hr_id = request.args.get('hr_id', '')

    if hr_id:
        jobs = JobRequirement.query.filter_by(created_by_id=hr_id).order_by(JobRequirement.job_position.asc()).all()
    else:
        jobs = JobRequirement.query.order_by(JobRequirement.job_position.asc()).all()
    
    return render_template('viewjobs.html', jobs=jobs, users=hr_users, current_user=current_user)

@bp.route('/search_route')
@no_cache
@login_required
def search_job():
    query = request.args.get('q', '')
    if query:
        # Example: search in job_position or job_description (case-insensitive)
        jobs = JobRequirement.query.filter(
            (JobRequirement.job_position.ilike(f'%{query}%')) |
            (JobRequirement.job_description.ilike(f'%{query}%'))
        ).order_by(JobRequirement.job_position.asc()).all()
    else:
        jobs = JobRequirement.query.order_by(JobRequirement.job_position.asc()).all()

    return render_template('viewjobs.html', jobs=jobs, current_user=current_user)
