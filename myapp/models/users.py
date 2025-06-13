from myapp.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    username =db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    auth_type = db.Column(db.String(20))
    linkedin_profile = db.Column(db.Text)
    designation = db.Column(db.String(100))
    role = db.Column(db.String(20))
    is_superuser = db.Column(db.Boolean, default=False)
    password_changed = db.Column(db.Boolean, default=False)
    is_superuser = db.Column(db.Boolean, default=False)

    referred_applicants = db.relationship("Applicant", back_populates="referrer", foreign_keys="Applicant.referred_by")
    uploaded_applicants = db.relationship("Applicant", back_populates="uploader", foreign_keys="Applicant.uploaded_by")
    job_listings = db.relationship('JobRequirement', back_populates='created_by', foreign_keys='JobRequirement.created_by_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)