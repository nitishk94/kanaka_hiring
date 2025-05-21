from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.auth.decorators import role_required

bp = Blueprint('referrer', __name__, url_prefix='/referrer')
REFERRAL_ROLES = ('referrer', 'admin')

@bp.route('/dashboard')
@login_required
@role_required(*REFERRAL_ROLES)
def dashboard():
    return "Referrer Dashboard"

@bp.route('/refer', methods=['POST'])
@login_required
@role_required(*REFERRAL_ROLES)
def refer_candidate():
    return "Refer a Candidate"

@bp.route('/status/<int:id>')
@login_required
@role_required(*REFERRAL_ROLES)
def referral_status(id):
    return f"Track Status of Referred Candidate {id}"
