from myapp.extensions import db
from sqlalchemy import event, Time
from myapp.models.applicants import Applicant

class TestResult(db.Model):
    __tablename__ = 'testresult'

    testlink_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable = False)
    email = db.Column(db.String(100), nullable = False, unique=True)
    date = db.Column(db.Date, nullable = False)
    score = db.Column(db.Integer, nullable = False)
    total_score = db.Column(db.Integer, nullable = False)
    time_taken = db.Column(db.Integer, nullable = False) 
    test_time = db.Column(db.Integer, nullable = False)
    test_name  = db.Column(db.String(100), nullable = False)
    pdf_link = db.Column(db.String(200), nullable = False)
    sections = db.Column(db.Text, nullable = False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'), nullable=False)

    applicant = db.relationship("Applicant", back_populates="test_results")

