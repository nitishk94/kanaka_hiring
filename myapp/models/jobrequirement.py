from myapp.extensions import db

class JobRequirement(db.Model):
    __tablename__ = 'jobrequirement'

    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(50), nullable = False)
    desc = db.Column(db.Text, nullable = False)
    
