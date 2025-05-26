from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.auth.decorators import role_required
from app.models.applicants import Applicant
from app.models.recruitment_history import RecruitmentHistory
from app.models.users import User
from app.utils import allowed_file, validate_file
from werkzeug.utils import secure_filename
from datetime import date
import os

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return render_template('home.html')

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return redirect(url_for('main.profile'))

        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('main.profile'))

        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully', 'success')
        current_app.logger.info(f"Password changed for user {current_user.username}")
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html', user=current_user)

@bp.route('/upload_applicants', methods=['GET', 'POST'])
@login_required
@role_required('hr', 'admin', 'referrer')
def upload_applicants():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
        
    if request.method == 'POST':
        required_fields = ['name', 'email', 'phone_number', 'age', 'experience', 'qualification', 'location', 'gender',
                           'is_kanaka_employee']
        missing = [field for field in required_fields if not request.form.get(field)]
        file = request.files.get('cv')

        if missing or not file:
            flash(f'Missing required fields: {", ".join(missing)}', 'warning')
            current_app.logger.info(f"Incomplete form")
            return render_template('hr/upload.html', form_data=request.form)

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload PDF or DOCX files only.', 'warning')
            current_app.logger.info(f"Invalid file type: {file.filename}")
            return render_template('hr/upload.html', form_data=request.form)
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('hr/upload.html', form_data=request.form)

        MAX_FILE_SIZE = 5 * 1024 * 1024
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            flash('File size exceeds 5MB limit.', 'warning')
            current_app.logger.info(f"File too large: {file.filename} ({file_size} bytes) uploaded by {current_user.username}")
            return render_template('hr/upload.html', form_data=request.form)

        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        age = request.form['age']
        experience = request.form['experience']
        qualification = request.form['qualification']
        location = request.form['location']
        gender = request.form['gender']
        is_kanaka_employee = request.form['is_kanaka_employee'] == 'yes'
        if current_user.role in ['hr', 'admin']:
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'applicants')
        elif current_user.role == 'referrer':
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'referrals')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        new_applicant = Applicant(
            name=name.capitalize(),
            email=email,
            phone_number=phone_number,
            age=age,
            experience=experience,
            qualification=qualification,
            location=location,
            gender=gender,
            is_kanaka_employee=is_kanaka_employee,
            applied_date=date.today().strftime('%Y-%m-%d'),
            current_stage='Need to schedule test',
            cv_file_path=file_path,
            is_referred=current_user.role == 'referrer',
            referred_by=current_user.id if current_user.role == 'referrer' else None
            )

        db.session.add(new_applicant)
        db.session.commit()

        if current_user.role in ['hr', 'admin']:
            flash('New applicant successfully created!', 'success')
            current_app.logger.info(f"New applicant (Name = {new_applicant.name.capitalize()}) added by {current_user.username}")
        elif current_user.role == 'referrer':
            flash('New referral successfully created!', 'success')
            current_app.logger.info(f"New referral (Name = {new_applicant.name.capitalize()}) added by {current_user.username}")
        return redirect(url_for('main.upload_applicants'))

    return render_template('upload.html')

@bp.route('/view_applicant/<int:id>')
@login_required
@role_required('hr', 'admin', 'interviewer')
def view_applicant(id):
    applicant = Applicant.query.get_or_404(id)
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    interviewers = User.query.filter_by(role='interviewer').all()

    if history:
        new_stage = history.compute_current_stage()
        if history.current_stage != new_stage or applicant.current_stage != new_stage:
            history.current_stage = new_stage
            applicant.current_stage = new_stage
            db.session.commit()

    return render_template('view_applicant.html', applicant=applicant, interviewers=interviewers)

@bp.route('/check_session')
def check_session():
    return jsonify({'active': current_user.is_authenticated})