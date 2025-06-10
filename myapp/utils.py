from myapp.extensions import db
from myapp.models.applicants import Applicant
from myapp.models.recruitment_history import RecruitmentHistory
from datetime import datetime, timedelta
import zipfile
import re
import os
import pdfplumber
import docx

def can_upload_applicant(email):
    applicant = Applicant.query.filter_by(email=email).first()
    if not applicant:
        return True
    
    six_months = (datetime.now() - timedelta(days=180)).date()
    if applicant.last_applied < six_months:
        return True
    return False

def validate_file(file):
    header = file.read(1024)
    file.seek(0)
    if b'%PDF-' in header:
        return True
    elif b'PK\x03\x04' in header:
        if not zipfile.is_zipfile(file):
            return False
        with zipfile.ZipFile(file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            if '[Content_Types].xml' in file_list and 'word/document.xml' in file_list:
                return True
        return False
    else:
        return False
    
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def update_status(id):
    applicant = Applicant.query.get_or_404(id)
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()

    if history:
        new_stage = history.compute_current_stage()
        if history.current_stage != new_stage or applicant.current_stage != new_stage:
            history.current_stage = new_stage
            applicant.current_stage = new_stage
            db.session.commit()

def generate_timeline(id):
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    
    timeline = [
        {'title': 'Application Received', 'date': history.applied_date}
    ]
    
    # Test scheduling history
    if history.test_scheduled:
        timeline.append({
            'title': 'Test Scheduled',
            'date': history.test_scheduled,
            'result': history.test_result if history.test_result is not None else None,
            'status': 'Completed' if history.test_result is not None else 'Scheduled'
        })
    
    # Interview Round 1 history
    if history.interview_round_1_date:
        timeline.append({
            'title': 'First Interview',
            'date': history.interview_round_1_date,
            'time': history.interview_round_1_time,
            'comments': history.interview_round_1_comments,
            'status': 'Completed' if history.interview_round_1_comments else 'Scheduled'
        })
    
    # Interview Round 2 history
    if history.interview_round_2_date:
        timeline.append({
            'title': 'Second Interview',
            'date': history.interview_round_2_date,
            'time': history.interview_round_2_time,
            'comments': history.interview_round_2_comments,
            'status': 'Completed' if history.interview_round_2_comments else 'Scheduled'
        })
    
    # HR Round history
    if history.hr_round_date:
        timeline.append({
            'title': 'HR Interview',
            'date': history.hr_round_date,
            'time': history.hr_round_time,
            'comments': history.hr_round_comments,
            'status': 'Completed' if history.hr_round_comments else 'Scheduled'
        })
    
    # Final status
    if history.rejected:
        timeline.append({'title': 'Application Rejected', 'date': history.updated_at.date()})
    elif history.interview_round_2_date and history.interview_round_2_comments and not history.rejected:
        if not history.hr_round_date:
            timeline.append({'title': 'Pending HR Round'})
        elif history.hr_round_comments and not history.rejected:
            timeline.append({'title': 'Hired', 'date': history.updated_at.date()})
    
    # Sort timeline by date
    #timeline.sort(key=lambda x: (x.get('date') or datetime.max.date()))
    return timeline

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        return '\n'.join(page.extract_text() or '' for page in pdf.pages)

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return '\n'.join([p.text for p in doc.paragraphs])

def extract_cv_info(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    text = ''
    if ext == '.pdf':
        text = extract_text_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        text = extract_text_from_docx(file_path)
    else:
        return {}

    return {
        "name": _extract_name(text),
        "email": _extract_email(text),
        "phone": _extract_phone(text),
        "dob": _extract_dob(text),
        "gender": _extract_gender(text),
        "marital_status": _extract_marital_status(text),
        "linkedin_profile": _extract_linkedin_profile(text),
        "github_profile": _extract_github_profile(text),
        "work_location": _extract_work_location(text),
        "current_location": _extract_current_location(text),
        "native_place": _extract_native_place(text)
    }

def _extract_name(text):
    match = re.search(r'(?i)name[:\s]*([A-Z][a-z]+(?: [A-Z][a-z]+)*)', text)
    return match.group(1).strip() if match else ''

def _extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else ''

def _extract_phone(text):
    match = re.search(r'\b(?:\+91[-\s]?)?[789]\d{9}\b', text)
    return match.group(0) if match else ''

def _extract_dob(text):
    match = re.search(r'\b(?:dob|date of birth)[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', text, re.IGNORECASE)
    if match:
        dob_str = match.group(1)
        try:
            return datetime.strptime(dob_str, '%d-%m-%Y').date()
        except ValueError:
            try:
                return datetime.strptime(dob_str, '%d/%m/%Y').date()
            except ValueError:
                return ''
    return ''

def _extract_gender(text):
    match = re.search(r'(?i)gender[:\s]*([a-zA-Z]+)', text)
    if match:
        gender = match.group(1).strip().lower()
        if gender in ['male', 'female', 'other']:
            return gender.capitalize()
    if re.search(r'\bmale\b', text, re.IGNORECASE):
        return 'Male'
    if re.search(r'\bfemale\b', text, re.IGNORECASE):
        return 'Female'
    return ''

def _extract_marital_status(text):
    match = re.search(r'(?i)marital status[:\s]*([a-zA-Z]+)', text)
    if match:
        status = match.group(1).strip().lower()
        if status in ['single', 'married']:
            return status.capitalize()
    for status in ['Single', 'Married']:
        if re.search(rf'\b{status}\b', text, re.IGNORECASE):
            return status
    return ''

def _extract_linkedin_profile(text):
    match = re.search(r'(https?://[\w\.]*linkedin\.com/[\w\-/\?=&#%\.]+)', text)
    return match.group(1) if match else ''

def _extract_github_profile(text):
    match = re.search(r'(https?://[\w\.]*github\.com/[\w\-/\?=&#%\.]+)', text)
    return match.group(1) if match else ''

def _extract_work_location(text):
    match = re.search(r'(?i)work location[:\s]*([\w\s,]+)', text)
    if match:
        return match.group(1).strip()
    match = re.search(r'(?i)location[:\s]*([\w\s,]+)', text)
    if match:
        return match.group(1).strip()
    return ''

def _extract_current_location(text):
    match = re.search(r'(?i)current location[:\s]*([\w\s,]+)', text)
    if match:
        return match.group(1).strip()
    match = re.search(r'(?i)present location[:\s]*([\w\s,]+)', text)
    if match:
        return match.group(1).strip()
    return ''

def _extract_native_place(text):
    match = re.search(r'(?i)native place[:\s]*([\w\s,]+)', text)
    if match:
        return match.group(1).strip()
    match = re.search(r'(?i)hometown[:\s]*([\w\s,]+)', text)
    if match:
        return match.group(1).strip()
    return ''