from myapp import db
from myapp.models import User, RecruitmentHistory
from datetime import date
import io
import pytest

def test_hr_dashboard_access(logged_in_client):
    hr = logged_in_client(role='hr')
    response = hr.get('hr/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'HR Dashboard' in response.data

def test_hr_upload(logged_in_client):
    hr = logged_in_client(role='hr')
    response = hr.get('hr/upload_applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Upload' in response.data

def create_fresher_test_applicant(client):
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

def create_corrupt_cv_test_applicant(client):
    form = {
        'name': 'testcase',
        'dob': date.today(),
        'email': 'test125@example.com',
        'phone': '9001234565',
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
        'cv': (io.BytesIO(b"1.4\n...This is a test CV..."), 'test_cv.pdf'),
        'comments': 'Test comment'
    }
    return client.post('hr/upload_applicants', data=form, content_type='multipart/form-data', follow_redirects=True)

def create_experienced_test_applicant(client):
    form = {
        'name': 'experienced_user',
        'dob': '1990-01-01',
        'email': 'expuser@example.com',
        'phone': '9001234568',
        'gender': 'female',
        'marital_status': 'married',
        'native_place': 'Mumbai',
        'current_location': 'Bangalore',
        'work_location': 'Bangalore',
        'is_fresher': '',
        'current_internship': '',
        'paid_internship': '',
        'graduation_year': '2010',
        'qualification': 'M.Tech',
        'referenced_from': 'LinkedIn',
        'internship_duration': '',
        'stipend': '',
        'cv': (io.BytesIO(b"%PDF-1.4\n...Experienced CV..."), 'exp_cv.pdf'),
        'comments': 'Experienced candidate',
        'experience': '10 years',
        'current_company': 'TechCorp',
        'designation': 'Senior Engineer',
        'current_job_position': 'Lead Developer',
        'current_ctc': '2500000',
        'expected_ctc': '3000000',
        'notice_period': '60',
        'tenure_at_current_company': '5 years',
        'current_offers_yes_no': 'on',
        'current_offers_description': 'Offer from BigTech',
        'reason_for_change': 'Better opportunity',
        'linkedin_profile': 'https://linkedin.com/in/expuser',
        'github_profile': 'https://github.com/expuser',
    }
    return client.post('hr/upload_applicants', data=form, content_type='multipart/form-data', follow_redirects=True)

def create_referred_test_applicant(client, referrer_id):
    form = {
        'name': 'referred_user',
        'dob': '1995-05-05',
        'email': 'referreduser@example.com',
        'phone': '9001234569',
        'gender': 'female',
        'marital_status': 'single',
        'native_place': 'Chennai',
        'current_location': 'Hyderabad',
        'work_location': 'Hyderabad',
        'is_fresher': 'on',
        'current_internship': '',
        'paid_internship': '',
        'graduation_year': '2017',
        'qualification': 'B.Sc',
        'referred_by': str(referrer_id),
        'internship_duration': '',
        'stipend': '',
        'cv': (io.BytesIO(b"%PDF-1.4\n...Referred CV..."), 'referred_cv.pdf'),
        'comments': 'Referred candidate',
    }
    return client.post('hr/upload_applicants', data=form, content_type='multipart/form-data', follow_redirects=True)

def test_hr_upload_validation(logged_in_client, app):
    hr = logged_in_client(role='hr')
    response = create_fresher_test_applicant(hr)
    assert response.status_code == 200
    assert b'New applicant successfully created!' in response.data

    response = create_experienced_test_applicant(hr)
    assert response.status_code == 200
    print(response.data.decode())
    assert b'New applicant successfully created!' in response.data

    with app.app_context():
        ref_user = User(id=100, username='referrer1', email='ref1@example.com', password_hash='test', role='referrer', name='Referrer One')
        db.session.add(ref_user)
        db.session.commit()
        referrer_id = ref_user.id
    response = create_referred_test_applicant(hr, referrer_id)
    assert response.status_code == 200
    assert b'New applicant successfully created!' in response.data

def test_hr_upload_invalid_cv(logged_in_client):
    hr = logged_in_client(role='hr')
    response = create_corrupt_cv_test_applicant(hr)
    assert response.status_code == 200
    assert b'New applicant successfully created!' in response.data

def test_hr_upload_duplicate_applicant(logged_in_client):
    hr = logged_in_client(role='hr')
    # First submission
    response = create_fresher_test_applicant(hr)
    assert response.status_code == 200
    assert b'New applicant successfully created!' in response.data

    # Second submission with the same email (duplicate)
    response2 = create_fresher_test_applicant(hr)
    assert response2.status_code == 200
    assert b'Upload' in response2.data

    # Third submission with a different name but same email (still duplicate)
    form = {
        'name': 'testcase2',
        'dob': date.today(),
        'email': 'test123@example.com',  # same email as before
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
    response3 = hr.post('hr/upload_applicants', data=form, content_type='multipart/form-data', follow_redirects=True)
    assert response3.status_code == 200
    assert b'Upload' in response3.data

def test_applicants(logged_in_client):
    hr = logged_in_client(role='hr')
    response = hr.get('hr/applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicants List' in response.data

def test_applicant_details(logged_in_client):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)
    create_d_test_applicant(hr)
    response = hr.get('hr/view_applicant/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data
    response = hr.get('hr/view_applicant/2', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_schedule_test(logged_in_client):
    hr = logged_in_client(role='hr')
    create_experienced_test_applicant(hr)
    test_date = '2025-06-06'
    response = hr.post('hr/schedule_test/1', data={'test_date': test_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test scheduled' in response.data

def test_reschedule_test(logged_in_client):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)
    test_date = '2025-06-06'
    response = hr.post('hr/reschedule_test/1', data={'test_date': test_date}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Test scheduled' in response.data

def test_schedule_interview(logged_in_client, app):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)
    with app.app_context():
        user = User(id = 20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer')
        db.session.add(user)
        db.session.commit()

    response = hr.post('hr/schedule_interview/1', data={'interview_date': '2025-06-10', 'interview_time': '10:00', 'interviewer_id': 20}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Interview scheduled' in response.data

def test_reschedule_interview(logged_in_client, app):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)
    with app.app_context():
        user = User(id = 20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer')
        db.session.add(user)
        db.session.commit()
    
    hr.post('hr/schedule_interview/1', data={'interview_date': '2025-06-01', 'interview_time': '10:00', 'interviewer_id': 20}, follow_redirects=True)
    
    response = hr.post('hr/reschedule_interview/1', data={'interview_date': '2025-06-10', 'interview_time': '10:00', 'interviewer_id': 20}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Interview round 1 scheduled' in response.data

def test_reject_applicant(logged_in_client):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)
    response = hr.post('hr/reject_application/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Rejected' in response.data

def test_status_tracker(logged_in_client):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)
    create_experienced_test_applicant(hr)

    response = hr.get('/track/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Recruitment Progress' in response.data

    response = hr.get('/track/2', follow_redirects=True)
    assert response.status_code == 200
    assert b'Recruitment Progress' in response.data

def test_test_stage_appears_in_tracker(logged_in_client):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)

    hr.post('hr/schedule_test/1', data={'test_date': '2025-06-11'}, follow_redirects=True)
    response = hr.get('/track/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Test' in response.data

def test_test_passed_in_tracker(logged_in_client, app):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)

    hr.post('hr/schedule_test/1', data={'test_date': '2025-06-01'}, follow_redirects=True)
    with app.app_context():
        history = RecruitmentHistory.query.filter_by(applicant_id=1).first()
        history.test_result = True
        db.session.commit()

    response = hr.get('/track/1', follow_redirects=True)
    assert response.status_code == 200
    print(response.data.decode())
    assert b'Passed' in response.data

def test_test_failed_in_tracker(logged_in_client, app):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)

    hr.post('hr/schedule_test/1', data={'test_date': '2025-06-01'}, follow_redirects=True)
    with app.app_context():
        history = RecruitmentHistory.query.filter_by(applicant_id=1).first()
        history.test_result = False
        db.session.commit()

    response = hr.get('/track/1', follow_redirects=True)
    assert response.status_code == 200
    print(response.data.decode())
    assert b'Failed' in response.data

def test_interview_stage_appears_in_tracker(logged_in_client, app):
    hr = logged_in_client(role='hr')
    create_fresher_test_applicant(hr)

    with app.app_context():
        history = RecruitmentHistory.query.filter_by(applicant_id=1).first()
        history.test_result = True
        db.session.add(User(id=20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer'))
        db.session.commit()

    hr.post('hr/schedule_interview/1', data={
        'interview_date': '2025-06-10',
        'interview_time': '10:00',
        'interviewer_id': 20
    }, follow_redirects=True)

    response = hr.get('/track/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Interview' in response.data

@pytest.mark.parametrize("url, expected_text", [
    ("hr/upload_applicants", b"Upload"),
    ("hr/applicants", b"Applicants List"),
    ("hr/view_applicant/1", b"Applicant Details"),
])
def test_admin_access_to_hr_pages(logged_in_client, url, expected_text):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)
    response = admin.get(url, follow_redirects=True)
    assert response.status_code == 200
    assert expected_text in response.data

def test_admin_can_upload_applicants(logged_in_client):
    admin = logged_in_client(role='admin')
    response = create_fresher_test_applicant(admin)
    assert response.status_code == 200
    assert b'New applicant successfully created!' in response.data
    
    response2 = create_experienced_test_applicant(admin)
    assert response2.status_code == 200
    assert b'New applicant successfully created!' in response2.data

def test_admin_can_view_applicants(logged_in_client):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)
    create_experienced_test_applicant(admin)
    
    response = admin.get('hr/applicants', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicants List' in response.data

def test_admin_can_view_applicant_details(logged_in_client):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)
    create_experienced_test_applicant(admin)
    
    response = admin.get('hr/view_applicant/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data
    
    response = admin.get('hr/view_applicant/2', follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_admin_can_schedule_and_reschedule_test(logged_in_client):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)

    response = admin.post('hr/schedule_test/1', data={'test_date': '2025-06-06'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

    response = admin.post('hr/reschedule_test/1', data={'test_date': '2025-06-08'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_admin_can_schedule_and_reschedule_interview(logged_in_client, app):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)

    with app.app_context():
        db.session.add(User(id=20, username='testinterviewer', email="test@testing.com", password_hash='testcase', role='interviewer'))
        db.session.commit()

    data = {'interview_date': '2025-06-01', 'interview_time': '10:00', 'interviewer_id': 20}
    response = admin.post('hr/schedule_interview/1', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

    data['interview_date'] = '2025-06-10'
    response = admin.post('hr/reschedule_interview/1', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Applicant Details' in response.data

def test_admin_can_reject_applicant(logged_in_client):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)

    response = admin.post('hr/reject_application/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Rejected' in response.data

def test_admin_can_view_status_tracker(logged_in_client):
    admin = logged_in_client(role='admin')
    create_fresher_test_applicant(admin)
    create_experienced_test_applicant(admin)

    response = admin.get('/track/1', follow_redirects=True)
    assert response.status_code == 200
    assert b'Recruitment Progress' in response.data

    response = admin.get('/track/2', follow_redirects=True)
    assert response.status_code == 200
    assert b'Recruitment Progress' in response.data