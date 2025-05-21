from app.extensions import db

class Applicant(db.Model):
    __tablename__ = 'applicants'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(100))
    phone_number = db.Column(db.Integer)
    age = db.Column(db.Integer)
    experience = db.Column(db.String(100))
    qualification = db.Column(db.String(100))
    location = db.Column(db.String(100))
    gender = db.Column(db.String(100))
    is_kanaka_employee = db.Column(db.Boolean, default = False)
    applied_date = db.Column(db.DateTime)
    current_stage = db.Column(db.String(100))
    cv_file_name = db.Column(db.String(255))
    cv = db.Column(db.LargeBinary)
    comments = db.Column(db.Text)

    history_entries = db.relationship("RecruitmentHistory", back_populates="applicant", cascade="all, delete-orphan")