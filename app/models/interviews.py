from app.extensions import db
from sqlalchemy import Time

class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'))
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    round_number = db.Column(db.Integer)
    date = db.Column(db.Date)
    time = db.Column(Time)
    completed = db.Column(db.Boolean, default=False)

    applicant = db.relationship("Applicant", backref="interviews")
    interviewer = db.relationship("User", backref="interviews")