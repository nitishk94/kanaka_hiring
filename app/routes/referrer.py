from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from app.auth.decorators import role_required
from app.models.applicants import Applicant
from app.extensions import db
from datetime import date
import os
from werkzeug.utils import secure_filename
import zipfile

bp = Blueprint('referrer', __name__, url_prefix='/referrer')
REFERRAL_ROLES = ('referrer', 'admin')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}

def validate_file(file):
    header = file.read(4)
    file.seek(0)
    if header == b'%PDF-':
        return True
    elif header == b'PK\x03\x04':
        z = zipfile.ZipFile(file)
        if 'word/document.xml' in z.namelist():
            return True
        else:
            return False
    else:
        return False

@bp.route('/dashboard')
@login_required
@role_required('referrer')
def dashboard():
    return render_template('referrer/dashboard.html')

@bp.route('/refer_candidate', methods=['GET', 'POST'])
@login_required
def refer_candidate():
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
            return render_template('referrer/refer.html', form_data=request.form)

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload PDF or DOCX files only.', 'warning')
            current_app.logger.info(f"Invalid file type: {file.filename}")
            return render_template('referrer/refer.html', form_data=request.form)
        
        if not validate_file(file):
            flash('File is corrupted.', 'warning')
            current_app.logger.warning(f"File is corrupted: {file.filename}")
            return render_template('referrer/refer.html', form_data=request.form)

        MAX_FILE_SIZE = 5 * 1024 * 1024
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            flash('File size exceeds 5MB limit.', 'warning')
            current_app.logger.info(f"File too large: {file.filename} ({file_size} bytes) uploaded by {current_user.username}")
            return render_template('referrer/refer.html', form_data=request.form)

        name = request.form['name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        age = request.form['age']
        experience = request.form['experience']
        qualification = request.form['qualification']
        location = request.form['location']
        gender = request.form['gender']
        
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'referrals')
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(file.filename)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        new_applicant = Applicant(
            name=name,
            email=email,
            phone_number=phone_number,
            age=age,
            experience=experience,
            qualification=qualification,
            location=location,
            gender=gender,
            is_kanaka_employee=False,
            is_referred=True,
            applied_date=date.today().strftime('%Y-%m-%d'),
            current_stage='Need to schedule test',
            cv_file_path=file_path,
            referred_by=current_user.id
        )

        db.session.add(new_applicant)
        db.session.commit()

        flash('Candidate referral submitted successfully!', 'success')
        current_app.logger.info(f"New referral (Name = {new_applicant.name}) added by {current_user.username}")
        return redirect(url_for('referrer.dashboard'))

    return render_template('referrer/refer.html')

@bp.route('/status')
@login_required
@role_required(*REFERRAL_ROLES)
def referral_status():
    return "Track Status of Referred Candidate"