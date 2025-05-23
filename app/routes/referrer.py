from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.auth.decorators import role_required

bp = Blueprint('referrer', __name__, url_prefix='/referrer')
REFERRAL_ROLES = ('referrer', 'admin')

@bp.route('/dashboard')
@login_required
@role_required('referrer')
def dashboard():
    return render_template('referrer/dashboard.html')

@bp.route('/refer', methods=['POST'])
@login_required
@role_required(*REFERRAL_ROLES)
def refer_candidate():
    return "Refer a Candidate"

@bp.route('/status')
@login_required
@role_required(*REFERRAL_ROLES)
def referral_status():
    return "Track Status of Referred Candidate"