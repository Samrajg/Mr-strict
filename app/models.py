from app import db
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='admin')

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)


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
    workspace_name = db.Column(db.String(100), default='default', index=True)
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
