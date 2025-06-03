from myapp import db
from myapp.models import User

def test_register_user(client, app):
    response = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'securepass',
        'confirm': 'securepass'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Registration Successful!' in response.data

    # Confirm user was added to db
    with app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.username == 'newuser'

def test_login_user(client, app):
    # First, manually create a user
    with app.app_context():
        user = User(username='testlogin', email='test@example.com', role='hr')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

    # Then test login
    response = client.post('/auth/login', data={
        'username_or_email': 'test@example.com',
        'password': 'testpass'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Welcome' in response.data

    response = client.post('/auth/login', data={
        'username_or_email': 'testlogin',
        'password': 'testpass'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Welcome' in response.data
