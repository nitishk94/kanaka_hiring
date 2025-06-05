from myapp import db
from myapp.models import Interview, Applicant, RecruitmentHistory
from datetime import date

def test_interviewer_dashboard_access(logged_in_client):
    client = logged_in_client(role='interviewer')
    response = client.get('/interviewer/dashboard')
    assert response.status_code == 200
    assert b'Interviewer Dashboard' in response.data

def test_view_interviews(logged_in_client):
    client = logged_in_client(role='interviewer')
    response = client.get('/interviewer/interviews')
    assert response.status_code == 200
    assert b'Interviews' in response.data

def test_interviewee_details(logged_in_client, app):
    interviewer = logged_in_client(role='interviewer')
    with app.app_context():
        db.session.add(
            Applicant(
                id=20, 
                name='testcase',
                dob=date.today(),
                email='test123@example.com',
                phone_number='9001234567',
                gender='male',
                marital_status='single',
                native_place='Test City',
                current_location='Test Location',
                work_location='Test City',
                is_fresher=True,
                current_internship=True,
                paid_internship=True,
                graduation_year='2012',
                qualification='B.Tech',
                referenced_from='Naukri',
                internship_duration='6',
                stipend='90000',
                cv_file_path='/Users/shrivatsanaik/Desktop/Internship/Project/app/uploads/applicants/dummy_cv.docx',
                comments='Test comment'
            )
        )
        db.session.commit()

    response = interviewer.get('/interviewer/view_interviewee/20')
    assert response.status_code == 200
    assert b'Details' in response.data

def test_submit_feedback(logged_in_client, app):
    interviewer = logged_in_client(role='interviewer')
    with app.app_context():
        db.session.add(
            Applicant(
                id=20,
                name='Test Applicant'
            )
        )
        db.session.add(
            RecruitmentHistory(
                id=1,
                applicant_id=20,
                test_scheduled=date.today(),
                test_result=True,
                interview_round_1_date=date.today()
            )
        )
        db.session.add(
            Interview(
                id=1,
                applicant_id=20,
                interviewer_id=1,
                round_number=1,
                date=date.today()
            )
        )
        db.session.commit()

    data = {
        'interview_completed': 'on',
        'feedback': 'Great performance'
    }
    response = interviewer.post('/interviewer/submit_feedback/20', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Feedback submitted successfully' in response.data

def test_admin_view_interviews(logged_in_client, app):
    admin = logged_in_client(role='admin')
    response = admin.get('interviewer/interviews')
    assert response.status_code == 200
    assert b'Interviews' in response.data

def test_admin_view_interviewee(logged_in_client, app):
    admin = logged_in_client(role='admin')
    with app.app_context():
        db.session.add(
            Applicant(
                id=20, 
                name='testcase',
                dob=date.today(),
                email='test123@example.com',
                phone_number='9001234567',
                gender='male',
                marital_status='single',
                native_place='Test City',
                current_location='Test Location',
                work_location='Test City',
                is_fresher=True,
                current_internship=True,
                paid_internship=True,
                graduation_year='2012',
                qualification='B.Tech',
                referenced_from='Naukri',
                internship_duration='6',
                stipend='90000',
                cv_file_path='/Users/shrivatsanaik/Desktop/Internship/Project/app/uploads/applicants/dummy_cv.docx',
                comments='Test comment'
            )
        )
        db.session.commit()

    response = admin.get('/interviewer/view_interviewee/20')
    assert response.status_code == 200
    assert b'Details' in response.data

def test_admin_submit_feedback(logged_in_client, app):
    admin = logged_in_client(role='admin')
    with app.app_context():
        db.session.add(
            Applicant(
                id=20,
                name='Test Applicant'
            )
        )
        db.session.add(
            RecruitmentHistory(
                id=1,
                applicant_id=20,
                test_scheduled=date.today(),
                test_result=True,
                interview_round_1_date=date.today()
            )
        )
        db.session.add(
            Interview(
                id=1,
                applicant_id=20,
                interviewer_id=1,
                round_number=1,
                date=date.today()
            )
        )
        db.session.commit()

    data = {
        'interview_completed': 'on',
        'feedback': 'Great performance'
    }
    response = admin.post('/interviewer/submit_feedback/20', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Feedback submitted successfully' in response.data