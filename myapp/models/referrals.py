from myapp.extensions import db

class Referral(db.Model):
    __tablename__ = 'referrals'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    referred_by = db.Column(db.Text)
    referral_date = db.Column(db.Date)
    cv_file_path = db.Column(db.Text)