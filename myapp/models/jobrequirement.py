from app.extensions import db

class JobRequirement(db.Model):
    __tablename__ = 'jobrequirement'

    job_id = db.Column(db.Integer, primary_key=True)
    job_position = db.Column(db.String(50), nullable = False)
    job_desc = db.Column(db.Text, nullable = False)
    
