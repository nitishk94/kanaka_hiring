from flask import Flask, session, flash, redirect, url_for, got_request_exception
from myapp.extensions import db, login_manager, migrate
from myapp.routes import register_routes
from logging.handlers import RotatingFileHandler
from myapp.models.users import User
from myapp import config
import logging
import os

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

def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or config.Config)
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = "basic"
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

    def log_exception(sender, exception, **extra):
        sender.logger.error('Unhandled Exception', exc_info=exception)

    got_request_exception.connect(log_exception, app)

    register_routes(app)

    return app