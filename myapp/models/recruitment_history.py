from myapp.extensions import db
from sqlalchemy import event, Time
from datetime import date, datetime, time
from myapp.models.interviews import Interview

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
    applied_date = db.Column(db.Date)
    test_date = db.Column(db.Date)
    test_time = db.Column(Time)
    test_id = db.Column(db.Integer)
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

    def get_interviewer_name(self, interview):
        return interview.interviewer.username if interview else 'TBD'

    def format_scheduled_interview(self, date, time, interview_type, interviewer):
        time_str = time.strftime('%H:%M')
        return f"{interview_type} scheduled on {date.strftime('%Y-%m-%d')} at {time_str} with {interviewer}"

    def compute_current_stage(self):
        today = date.today()
        hr_date = ensure_date(self.hr_round_date)
        round2_date = ensure_date(self.interview_round_2_date)
        round1_date = ensure_date(self.interview_round_1_date)
        test_date = ensure_date(self.test_date)

        hr_time = ensure_time(self.hr_round_time)
        round2_time = ensure_time(self.interview_round_2_time)
        round1_time = ensure_time(self.interview_round_1_time)

        latest_hr = Interview.query.filter_by(applicant_id=self.applicant_id, round_number=3).order_by(Interview.id.desc()).first()
        latest_round2 = Interview.query.filter_by(applicant_id=self.applicant_id, round_number=2).order_by(Interview.id.desc()).first()
        latest_round1 = Interview.query.filter_by(applicant_id=self.applicant_id, round_number=1).order_by(Interview.id.desc()).first()

        if self.rejected:
            return "Rejected - Test Failed" if not self.test_result else "Rejected"
            
        interview_rounds = [
            (hr_date, hr_time, latest_hr, "HR round"),
            (round2_date, round2_time, latest_round2, "Interview round 2"),
            (round1_date, round1_time, latest_round1, "Interview round 1")
        ]
        
        for interview_date, interview_time, interview, round_name in interview_rounds:
            if interview_date:
                if interview_date >= today and not interview.completed:
                    interviewer_name = self.get_interviewer_name(interview)
                    return self.format_scheduled_interview(interview_date, interview_time, round_name, interviewer_name)
                else:
                    return f"{round_name} completed"

        if test_date:
            if self.test_result is not None:
                if not self.test_result:
                    self.rejected = True
                    return "Test Failed"
                return "Test Passed"
            elif test_date >= today or self.test_result is not None:
                return f"Test scheduled on {test_date.strftime('%Y-%m-%d')}"
            return "Test completed"
            
        return "Need to schedule test"
        
@event.listens_for(RecruitmentHistory, 'after_update')
def after_history_update(mapper, connection, target):
    from myapp.models.applicants import Applicant
    new_stage = target.compute_current_stage()
    connection.execute(
        Applicant.__table__.update()
        .where(Applicant.id == target.applicant_id)
        .values(current_stage=new_stage)
    )    