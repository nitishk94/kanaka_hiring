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
    test_id = db.Column(db.Integer, nullable=True)
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
    current_stage = db.Column(db.Text, default='Need to Schedule Test or Interview')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    applicant = db.relationship("Applicant", back_populates="history_entries")

    def get_interviewer_name(self, interview):
        return interview.interviewer.username if interview else 'TBD'

    def format_scheduled_interview(self, date, time, interview_type, interviewer):
        time_str = time.strftime('%H:%M')
        return f"{interview_type} scheduled on {date.strftime('%Y-%m-%d')} at {time_str} with {interviewer}"

    def compute_current_stage(self):
        today = date.today()
        applicant = self.applicant

        # Priority overrides
        if applicant.status == "Rejected" or self.rejected:
            return "Rejected"
        if applicant.status == "Joined":
            return "Joined"
        if applicant.status == "Offered":
            return "Offered"
        if applicant.status == "On Hold":
            return "On Hold"

        # Latest interviews
        latest_hr = Interview.query.filter_by(applicant_id=self.applicant_id, round_number='HR') \
            .order_by(Interview.id.desc()).first()
        latest_round2 = Interview.query.filter(
            Interview.applicant_id == self.applicant_id,
            Interview.round_number.in_(['Round 2', 'Client Round 2'])
        ).order_by(Interview.id.desc()).first()
        latest_round1 = Interview.query.filter(
            Interview.applicant_id == self.applicant_id,
            Interview.round_number.in_(['Round 1', 'Client Round 1'])
        ).order_by(Interview.id.desc()).first()

        # HR Round
        if self.hr_round_date and not self.hr_round_comments:
            return "HR Round Scheduled"
        if self.hr_round_comments:
            return "HR Round Completed"

        # Interview Round 2
        if self.interview_round_2_date and not self.interview_round_2_comments:
            return "Interview Round 2 Scheduled"
        if self.interview_round_2_comments and not self.hr_round_date:
            return "Interview Round 2 Completed"

        # Interview Round 1
        if self.interview_round_1_date and not self.interview_round_1_comments:
            return "Interview Round 1 Scheduled"
        if self.interview_round_1_comments and not self.interview_round_2_date:
            return "Interview Round 1 Completed"

        # Test
        if self.test_date:
            if not self.test_result:
                return "Test Scheduled"
            elif self.test_result and not self.interview_round_1_date:
                return "Test Completed"

        # Fallbacks
        if not self.test_date and not self.interview_round_1_date:
            return "Need to Schedule Test or Interview"

        return "In Progress"

@event.listens_for(RecruitmentHistory, 'after_update')
def after_history_update(mapper, connection, target):
    from myapp.models.applicants import Applicant
    new_stage = target.compute_current_stage()
    connection.execute(
        Applicant.__table__.update()
        .where(Applicant.id == target.applicant_id)
        .values(current_stage=new_stage)
    )   