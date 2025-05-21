from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.applicants import Applicant
from app.extensions import db
from datetime import date

bp = Blueprint('hr', __name__, url_prefix='/hr')
HR_ROLES = ('hr', 'admin')

@bp.route('/dashboard')
@login_required
@role_required(*HR_ROLES)
def dashboard():
    return "HR Dashboard"

@bp.route('/upload', methods=['POST'])
@login_required
@role_required(*HR_ROLES)
def upload_applicants():
    if request.method == 'POST':
        required_fields = ['name', 'email', 'phone_number', 'age', 'experience', 'qualification', 'location', 'gender',
                           'is_kanaka_employee']
        missing = [field for field in required_fields if not request.form.get(field)]
        file = request.files.get('cv')

        if missing or not file:
            flash(f'Missing required fields: {", ".join(missing)}', 'warning')
            current_app.logger.info(f"Incomplete form")
            return redirect(request.url)

        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        age = request.form['age']
        experience = request.form['experience']
        qualification = request.form['qualification']
        location = request.form['location']
        gender = request.form['gender']
        is_kanaka_employee = request.form['is_kanaka_employee'].lower() in ['true', '1', 'yes', 'on']

        new_applicant = Applicant(
            name=name,
            email=email,
            phone_number=phone_number,
            age=age,
            experience=experience,
            qualification=qualification,
            location=location,
            gender=gender,
            is_kanaka_employee=is_kanaka_employee,
            applied_date=date.today(),
            current_stage='Need to schedule test',
            cv_file_name=secure_filename(file.filename),
            cv = file.read()
        )

        db.session.add(new_applicant)
        db.session.commit()

        flash('New applicant successfully created!')
        current_app.logger.info(f"New applicant (Name = {new_applicant.name}) added by {current_user.username}")
        return redirect(request.url)

    return render_template('hr/upload.html')

@bp.route('/applicants')
@login_required
@role_required(*HR_ROLES)
def applicants():
    return "List of Applicants"

@bp.route('/applicants/filter')
@login_required
@role_required(*HR_ROLES)
def filter_applicants():
    return "Filter Applicants"

@bp.route('/applicants/<int:id>')
@login_required
@role_required(*HR_ROLES)
def view_applicant(id):
    return f"View Applicant {id}"

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
