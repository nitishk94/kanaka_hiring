from myapp.extensions import db

class Referral(db.Model):
    __tablename__ = 'referrals'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id'))
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    referred_by = db.Column(db.Text)
    referral_date = db.Column(db.Date)
    cv_file_path = db.Column(db.Text)
    job_id = db.Column(db.Integer, db.ForeignKey('jobrequirement.id'), nullable = True)
    is_fresher = db.Column(db.Boolean, default = False)
    
    job = db.relationship("JobRequirement", backref="referrals")
    applicant = db.relationship("Applicant", back_populates="referred_candidate")