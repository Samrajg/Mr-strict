from flask import Blueprint, render_template, session
from app.models import Assignment, Submission, Rubric
import json

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
def index():
    rubrics = Rubric.query.order_by(Rubric.id.desc()).all()
    
    # Calculate Live Analytics Data scoped to active workspace (or all if 'default')
    active_ws = session.get('active_workspace', 'default')
    if active_ws == 'default':
        assignments = Assignment.query.order_by(Assignment.id.asc()).all()
    else:
        assignments = Assignment.query.filter_by(workspace_name=active_ws).order_by(Assignment.id.asc()).all()
    
    trend_labels = []
    trend_data = []
    
    q_totals = {}
    q_counts = {}
    
    for assign in assignments:
        submissions = Submission.query.filter_by(assignment_id=assign.id).all()
        if not submissions:
            continue
            
        # Assignment average
        avg = sum([s.score for s in submissions if s.score is not None]) / len(submissions)
        trend_labels.append(assign.title[:15])
        trend_data.append(round(avg, 1))
        
        # Question averages
        for sub in submissions:
            if sub.question_scores:
                try:
                    qs = json.loads(sub.question_scores)
                    for q, score in qs.items():
                        if q not in q_totals:
                            q_totals[q] = 0
                            q_counts[q] = 0
                        q_totals[q] += score
                        q_counts[q] += 1
                except:
                    pass
                    
    q_labels = []
    q_data = []
    for q in sorted(q_totals.keys()):
        q_labels.append(q)
        q_data.append(round(q_totals[q] / max(1, q_counts[q]), 1))
        
    return render_template(
        'dashboard.html', 
        title='Analytics Dashboard', 
        rubrics=rubrics,
        trend_labels=json.dumps(trend_labels),
        trend_data=json.dumps(trend_data),
        q_labels=json.dumps(q_labels),
        q_data=json.dumps(q_data)
    )
