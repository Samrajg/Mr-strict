from app import db
from datetime import datetime


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), unique=True)
    candidate_id = db.Column(db.String(50), unique=True, nullable=True) # For Blind Grading
    demographic_group = db.Column(db.String(50), nullable=True) # For Bias Detection
    submissions = db.relationship('Submission', backref='student', lazy=True)

class Rubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    is_blind = db.Column(db.Boolean, default=False)
    rubric_id = db.Column(db.Integer, db.ForeignKey('rubric.id'))
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    content_text = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=True)
    question_scores = db.Column(db.Text, nullable=True) # JSON string of question breakdown
    feedback = db.Column(db.Text, nullable=True)
    plagiarism_flag = db.Column(db.Text, nullable=True) # JSON string or text flag if caught cheating
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
