from app.extensions import db

class RecruitmentHistory(db.Model):
    __tablename__ = 'recruitment_history'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'), nullable=False)
    stage = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50))
    comments = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, server_default=db.func.now())

    applicant = db.relationship("Applicant", back_populates="history_entries")