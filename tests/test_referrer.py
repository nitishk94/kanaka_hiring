from myapp import db
from myapp.models import RecruitmentHistory, Applicant, Interview
from datetime import date
import io

def test_referrer_dashboard_access(logged_in_client):
    referrer = logged_in_client(role='referrer')
    response = referrer.get('/referrer/dashboard')
    assert response.status_code == 200
    assert b'Referrer Dashboard' in response.data

def test_referrer_upload(logged_in_client):
    referrer = logged_in_client(role='referrer')
    data = {
        'name': 'Test Referral',
        'cv': (io.BytesIO(b"%PDF-1.4\n...This is a test CV..."), 'referral.pdf')
    }
    response = referrer.post('/referrer/referral', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'New referral successfully created!' in response.data

def test_referrer_check_status(logged_in_client, app):
    referrer = logged_in_client(role='referrer')
    with app.app_context():
        db.session.add(
            Applicant(
                id=100,
                name='Test Applicant'
            )
        )
        db.session.add(
            RecruitmentHistory(
                id=1,
                applicant_id=100,
                test_scheduled=date.today(),
                test_result=True,
                interview_round_1_date=date.today()
            )
        )
        db.session.add(
            Interview(
                id=1,
                applicant_id=100,
                interviewer_id=15,
                round_number=1,
                date=date.today(),
                completed=True
            )
        )
        db.session.commit()
    
    response = referrer.get('/track/100')
    assert response.status_code == 200
    assert b'Passed' in response.data