from app.extensions import db

class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'))
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    round_number = db.Column(db.Integer)
    time = db.Column(db.DateTime)

    applicant = db.relationship("Applicant", backref="interviews")
    interviewer = db.relationship("User", backref="interviews")