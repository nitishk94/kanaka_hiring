from app.extensions import db
from sqlalchemy import event
from datetime import date
from app.utils import ensure_date

class RecruitmentHistory(db.Model):
    __tablename__ = 'recruitment_history'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'), nullable=False)
    test_scheduled = db.Column(db.Date)
    test_result = db.Column(db.Boolean)
    interview_round_1 = db.Column(db.Date)
    interview_round_1_comments = db.Column(db.Text, default=None)
    interview_round_2 = db.Column(db.Date)
    interview_round_2_comments = db.Column(db.Text, default=None)
    hr_round = db.Column(db.Date)
    hr_round_comments = db.Column(db.Text, default=None)
    rejected = db.Column(db.Boolean, default=False)
    current_stage = db.Column(db.Text, default='Need to schedule test')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    applicant = db.relationship("Applicant", back_populates="history_entries")

    def compute_current_stage(self):
        today = date.today()
        hr_date = ensure_date(self.hr_round)
        round2_date = ensure_date(self.interview_round_2)
        round1_date = ensure_date(self.interview_round_1)
        test_date = ensure_date(self.test_scheduled)

        if self.rejected:
            return "Rejected"
        elif hr_date:
            if hr_date >= today:
                return f"HR round scheduled on {hr_date.strftime('%Y-%m-%d')}"
            else:
                return "HR round completed"
        elif round2_date:
            if round2_date >= today:
                return f"Interview round 2 scheduled on {round2_date.strftime('%Y-%m-%d')}"
            else:
                return "Interview round 2 completed"
        elif round1_date:
            if round1_date >= today:
                return f"Interview round 1 scheduled on {round1_date.strftime('%Y-%m-%d')}"
            else:
                return "Interview round 1 completed"
        elif test_date:
            if self.test_result is not None:
                return "Test passed" if self.test_result else "Test failed"
            elif test_date >= today:
                return f"Test scheduled on {test_date.strftime('%Y-%m-%d')}"
            else:
                return "Test completed"
        else:
            return "Need to schedule test"
        
@event.listens_for(RecruitmentHistory, 'after_update')
def after_history_update(mapper, connection, target):
    from app.models.applicants import Applicant
    new_stage = target.compute_current_stage()
    connection.execute(
        Applicant.__table__.update()
        .where(Applicant.id == target.applicant_id)
        .values(current_stage=new_stage)
    )    