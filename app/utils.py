from app.extensions import db
from app.models.applicants import Applicant
from app.models.recruitment_history import RecruitmentHistory
import zipfile
import re

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
    applicant = Applicant.query.get_or_404(id)
    
    timeline = [
        {'title': 'Application Received', 'date': applicant.applied_date},
        {'title': 'Test Scheduled', 'date': history.test_scheduled, 'result': history.test_result if history.test_result is not None else None} if history.test_scheduled else None,
        {'title': 'First Interview', 'date': history.interview_round_1_date, 'comments': history.interview_round_1_comments} if history.interview_round_1_date else None,
        {'title': 'Second Interview', 'date': history.interview_round_2_date, 'comments': history.interview_round_2_comments} if history.interview_round_2_date else None,
        {'title': 'HR Interview', 'date': history.hr_round_date, 'comments': history.hr_round_comments} if history.hr_round_date else None,
        {'title': 'Rejected'} if history.rejected else None,
        {'title': 'Onboarding'} if history.interview_round_2_date and not history.rejected else None
    ]

    timeline = [item for item in timeline if item is not None]
    return timeline