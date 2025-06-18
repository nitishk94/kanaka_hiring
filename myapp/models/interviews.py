from myapp.extensions import db
from sqlalchemy import Time

class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'))
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    scheduler_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    round_number = db.Column(db.Integer)
    date = db.Column(db.Date)
    time = db.Column(Time)
    completed = db.Column(db.Boolean, default=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobrequirement.id'))
    
    job = db.relationship("JobRequirement", back_populates="interviews")
    applicant = db.relationship("Applicant", back_populates="interviews")
    interviewer = db.relationship("User", foreign_keys=[interviewer_id], back_populates="interviews_as_interviewer")
    scheduler = db.relationship("User", foreign_keys=[scheduler_id], back_populates="scheduled_interviews")