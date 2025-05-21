from app.extensions import db

class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interviews.id'))
    comments = db.Column(db.Text, db.ForeignKey('applicants.comments'))
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    interview = db.relationship("Interview", backref="feedback")
    submitter = db.relationship("User", backref="submitted_feedback")