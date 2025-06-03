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

    applicant = db.relationship("Applicant", backref="interviews")
    interviewer = db.relationship("User", backref="interviews_as_interviewer", foreign_keys=[interviewer_id])
    scheduler = db.relationship("User", backref="interviews_as_scheduler", foreign_keys=[scheduler_id])