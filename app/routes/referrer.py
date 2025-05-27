from flask import Blueprint, render_template
from flask_login import login_required
from app.auth.decorators import role_required
from app.models.applicants import Applicant

bp = Blueprint('referrer', __name__, url_prefix='/referrer')
REFERRAL_ROLES = ('referrer', 'admin')

@bp.route('/dashboard')
@login_required
@role_required('referrer')
def dashboard():
    return render_template('referrer/dashboard.html')

@bp.route('/referrals')
@login_required
@role_required(*REFERRAL_ROLES)
def referrals():
    referrals = Applicant.query.filter_by(is_referred=True).order_by(Applicant.applied_date.desc()).all()
    return render_template('applicants.html', candidates=referrals)