from myapp import db
from myapp.models import User, RecruitmentHistory
from datetime import date
import pytest

def test_admin_dashboard(logged_in_client):
    admin = logged_in_client(role='admin')
    response = admin.get('admin/dashboard')
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data

def test_admin_view_users(logged_in_client):
    admin = logged_in_client(role='admin')
    response = admin.get('admin/users')
    assert response.status_code == 200
    assert b'Users' in response.data

def test_admin_edit_user(logged_in_client, app):
    admin = logged_in_client(role='admin')
    with app.app_context():
        user = User(id=20, username='dummyuser', email='dummyuser@example.com', password_hash='test', role='hr', name='Dummy User')
        db.session.add(user)
        db.session.commit()
    response = admin.get('admin/edit_user/20', follow_redirects=True)
    assert response.status_code == 200
    assert b'Edit User' in response.data

def test_admin_change_role(logged_in_client, app):
    admin = logged_in_client(role='admin')
    with app.app_context():
        user = User(id=20, username='dummyuser', email='dummyuser@example.com', password_hash='test', role='hr', name='Dummy User')
        db.session.add(user)
        db.session.commit()
    response = admin.post('admin/change_role/20', data={'role': 'interviewer'}, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'User role updated successfully' in response.data

def test_admin_change_password(logged_in_client, app):
    admin = logged_in_client(role='admin')
    with app.app_context():
        user = User(id=20, username='dummyuser', email='dummyuser@example.com', password_hash='test', role='hr', name='Dummy User')
        db.session.add(user)
        db.session.commit()
    response = admin.post('admin/change_password/20', data={'new_password': 'newpassword', 'confirm_password': 'newpassword'}, content_type='multipart/form-data', follow_redirects=True)
    assert response.status_code == 200
    assert b'User password updated successfully' in response.data

def test_admin_delete_user(logged_in_client, app):
    admin = logged_in_client(role='admin')
    with app.app_context():
        user = User(id=20, username='dummyuser', email='dummyuser@example.com', password_hash='test', role='hr', name='Dummy User')
        db.session.add(user)
        db.session.commit()
    response = admin.post('admin/delete_user/20', follow_redirects=True)
    assert response.status_code == 200
    assert b'User deleted successfully' in response.data