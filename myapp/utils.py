from myapp.extensions import db
from myapp.models.applicants import Applicant
from myapp.models.recruitment_history import RecruitmentHistory
from datetime import datetime, timedelta
import zipfile
import re

def can_upload_applicant(email):
    applicant = Applicant.query.filter_by(email=email).first()
    if not applicant:
        return True
    
    six_months = (datetime.now() - timedelta(days=180)).date()
    if applicant.last_applied < six_months:
        return True
    return False

def can_update_applicant(id, email):
    applicant = Applicant.query.filter_by(email=email).first()
    if applicant.id == id:
        return True
    else:
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