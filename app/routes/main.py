from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.auth.decorators import role_required, no_cache
from app.models.applicants import Applicant
from app.utils import generate_timeline, update_status

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