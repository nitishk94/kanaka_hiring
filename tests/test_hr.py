from myapp import db
from myapp.models import User, Interview
from datetime import date
import io

def test_hr_dashboard_access(logged_in_client):
    client = logged_in_client(role='hr')
    response = client.get('hr/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'HR Dashboard' in response.data

def test_hr_upload(logged_in_client):
    client = logged_in_client(role='hr')
    response = client.get('hr/upload_applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Upload' in response.data

def create_test_applicant(client):
    form = {
        'name': 'testcase',
        'dob': date.today(),
        'email': 'test123@example.com',
        'phone': '9001234567',
        'gender': 'male',
        'marital_status': 'single',
        'native_place': 'Test City',
        'current_location': 'Test Location',
        'work_location': 'Test City',
        'is_fresher': 'on',
        'current_internship': 'on',
        'paid_internship': 'on',
        'graduation_year': '2012',
        'qualification': 'B.Tech',
        'referenced_from': 'Naukri',
        'internship_duration': '6',
        'stipend': '90000',
        'cv': (io.BytesIO(b"%PDF-1.4\n...This is a test CV..."), 'test_cv.pdf'),
        'comments': 'Test comment'
    }
    return client.post('hr/upload_applicants', data=form, content_type='multipart/form-data', follow_redirects=True)

def test_hr_upload_validation(logged_in_client):
    client = logged_in_client(role='hr')
    response = create_test_applicant(client)
    assert response.status_code == 200
    assert b'New applicant successfully created!' in response.data

def test_applicants(logged_in_client):
    client = logged_in_client(role='hr')
    response = client.get('hr/applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicants List' in response.data

def test_applicant_details(logged_in_client):
    client = logged_in_client(role='hr')
    create_test_applicant(client)
    response = client.get('hr/view_applicant/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_schedule_test(logged_in_client):
    client = logged_in_client(role='hr')
    create_test_applicant(client)
    test_date = '2025-06-06'
    response = client.post('hr/schedule_test/1', data={'test_date': test_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_reschedule_test(logged_in_client):
    client = logged_in_client(role='hr')
    create_test_applicant(client)
    test_date = '2025-06-06'
    response = client.post('hr/reschedule_test/1', data={'test_date': test_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_schedule_interview(logged_in_client, app):
    client = logged_in_client(role='hr')
    create_test_applicant(client)
    with app.app_context():
        user = User(id = 20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer')
        db.session.add(user)
        db.session.commit()
    
    interview_date = '2025-06-10'
    interview_time = '10:00'
    interviewer_id = 20
    response = client.post('hr/schedule_interview/1', data={'interview_date': interview_date, 'interview_time': interview_time, 'interviewer_id': interviewer_id}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_reschedule_interview(logged_in_client, app):
    client = logged_in_client(role='hr')
    create_test_applicant(client)
    with app.app_context():
        user = User(id = 20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer')
        db.session.add(user)
        db.session.commit()
    
    client.post('hr/schedule_interview/1', data={'interview_date': '2025-06-01', 'interview_time': '10:00', 'interviewer_id': 20}, follow_redirects=True)
    
    interview_date = '2025-06-10'
    interview_time = '10:00'
    interviewer_id = 20
    response = client.post('hr/reschedule_interview/1', data={'interview_date': interview_date, 'interview_time': interview_time, 'interviewer_id': interviewer_id}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_admin_access_to_hr_functions(logged_in_client, app):
    client = logged_in_client(role='admin')
    # Upload page
    response = client.get('hr/upload_applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Upload' in response.data
    # Create applicant
    create_test_applicant(client)
    # Applicants list
    response = client.get('hr/applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicants List' in response.data
    # Applicant details
    response = client.get('hr/view_applicant/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data
    # Schedule test
    test_date = '2025-06-06'
    response = client.post('hr/schedule_test/1', data={'test_date': test_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

    response = client.post('hr/reschedule_test/1', data={'test_date': test_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

    with app.app_context():
        user = User(id = 20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer')
        db.session.add(user)
        db.session.commit()
    
    response = client.post('hr/schedule_interview/1', data={'interview_date': '2025-06-01', 'interview_time': '10:00', 'interviewer_id': 20}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

    response = client.post('hr/reschedule_interview/1', data={'interview_date': '2025-06-10', 'interview_time': '10:00', 'interviewer_id': 20}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data
