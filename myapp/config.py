from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import secrets
import os

env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

class Config:
    SECRET_KEY = secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_REFRESH_EACH_REQUEST = True

    MS_CLIENT_ID = os.getenv("CLIENT_ID")
    MS_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    MS_TENANT_ID = os.getenv("TENANT_ID")
    MS_AUTHORITY = f"https://login.microsoftonline.com/{MS_TENANT_ID}"

    MS_SCOPE = [
        "User.Read",
        "Calendars.ReadWrite",
        "Mail.Send",
        "OnlineMeetings.ReadWrite"
    ]

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-key'