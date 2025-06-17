from myapp.extensions import db

class JobRequirement(db.Model):
    __tablename__ = 'jobrequirement'

    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.String(50), nullable = False)
    description = db.Column(db.Text, nullable = False)
    skillset = db.Column(db.String(100), nullable = False)
    experience = db.Column(db.Text, nullable = True)
    clients = db.Column(db.Text, nullable = True)
    budget = db.Column(db.String(50), nullable = False)
    is_open = db.Column(db.Boolean, default=True, nullable=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', back_populates='job_listings')