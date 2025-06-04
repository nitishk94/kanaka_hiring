import pytest
from myapp.config import TestingConfig
from myapp.models import User
from myapp import create_app, db

class TestingConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret'

@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def logged_in_client(client, app):
    def _login(role=None):
        with app.app_context():
            user = User(username='testuser', email='test@example.com', role=role)
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()

        client = app.test_client()
        client.post('/auth/login', data={
            'username_or_email': 'test@example.com',
            'password': 'testpass'
        }, follow_redirects=True)
        return client
    return _login

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()