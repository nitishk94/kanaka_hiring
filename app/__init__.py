from flask import Flask, session, flash, redirect, url_for
from app.extensions import db, login_manager, migrate
from app.routes import register_routes
from logging.handlers import RotatingFileHandler
from app.models.users import User
import logging
import secrets
import os
from datetime import timedelta

login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if session.get('_user_id'):
        session.clear()
        flash('Your session has timed out. Please log in again.', 'session_timeout')
    return redirect(url_for('auth.login'))

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres@localhost:5432/kanaka_hiring'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    app.permanent_session_lifetime = timedelta(minutes=10)
    migrate.init_app(app, db)

    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=5)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    file_handler.setFormatter(formatter)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Flask application startup')

    register_routes(app)

    return app