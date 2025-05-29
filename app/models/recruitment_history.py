from app.extensions import db
from sqlalchemy import event, Time
from datetime import date, datetime, time
from app.models.interviews import Interview

def ensure_date(value):
    if value == None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d').date()

def ensure_time(value):
    if value == None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, '%H:%M').time()
        except ValueError:
            return datetime.strptime(value, '%H:%M:%S').time()
    if isinstance(value, datetime):
        return value.time()
    return value

class RecruitmentHistory(db.Model):
    __tablename__ = 'recruitment_history'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'), nullable=False)
    test_scheduled = db.Column(db.Date)
    test_result = db.Column(db.Boolean)
    interview_round_1_date = db.Column(db.Date)
    interview_round_1_time = db.Column(Time)
    interview_round_1_comments = db.Column(db.Text, default=None)
    interview_round_2_date = db.Column(db.Date)
    interview_round_2_time = db.Column(Time)
    interview_round_2_comments = db.Column(db.Text, default=None)
    hr_round_date = db.Column(db.Date)
    hr_round_time = db.Column(Time)
    hr_round_comments = db.Column(db.Text, default=None)
    rejected = db.Column(db.Boolean, default=False)
    current_stage = db.Column(db.Text, default='Need to schedule test')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    applicant = db.relationship("Applicant", back_populates="history_entries")

    def compute_current_stage(self):
        today = date.today()
        hr_date = ensure_date(self.hr_round_date)
        round2_date = ensure_date(self.interview_round_2_date)
        round1_date = ensure_date(self.interview_round_1_date)
        test_date = ensure_date(self.test_scheduled)

        hr_time = ensure_time(self.hr_round_time)
        round2_time = ensure_time(self.interview_round_2_time)
        round1_time = ensure_time(self.interview_round_1_time)

        latest_hr = Interview.query.filter_by(applicant_id=self.applicant_id, round_number=3).order_by(Interview.id.desc()).first()
        latest_round2 = Interview.query.filter_by(applicant_id=self.applicant_id, round_number=2).order_by(Interview.id.desc()).first()
        latest_round1 = Interview.query.filter_by(applicant_id=self.applicant_id, round_number=1).order_by(Interview.id.desc()).first()

        if self.rejected:
            return "Rejected"
        elif hr_date:
            if hr_date >= today:
                time_str = hr_time.strftime('%H:%M')
                interviewer_name = latest_hr.interviewer.username if latest_hr else 'TBD'
                return f"HR round scheduled on {hr_date.strftime('%Y-%m-%d')} at {time_str} with {interviewer_name}"
            else:
                return "HR round completed"
        elif round2_date:
            if round2_date >= today:
                time_str = round2_time.strftime('%H:%M')
                interviewer_name = latest_round2.interviewer.username if latest_round2 else 'TBD'
                return f"Interview round 2 scheduled on {round2_date.strftime('%Y-%m-%d')} at {time_str} with {interviewer_name}"
            else:
                return "Interview round 2 completed"
        elif round1_date:
            if round1_date >= today:
                time_str = round1_time.strftime('%H:%M')
                interviewer_name = latest_round1.interviewer.username if latest_round1 else 'TBD'
                return f"Interview round 1 scheduled on {round1_date.strftime('%Y-%m-%d')} at {time_str} with {interviewer_name}"
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