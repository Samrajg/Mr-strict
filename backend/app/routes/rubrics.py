from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.auth_utils import login_required
from app.models import Rubric
from app import db
import google.generativeai as genai
from flask import current_app

rubrics_bp = Blueprint('rubrics', __name__, url_prefix='/rubrics')

@rubrics_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        # Here we would call Gemini API using current_app.config['GEMINI_API_KEY']
        # Mocking the generation for now
        mock_rubric = f"Generated rubric for: {prompt}\n- Concept: 40%\n- Structure: 30%\n- Grammar: 30%"
        new_rubric = Rubric(title=f"Rubric for {prompt[:20]}", content=mock_rubric)
        db.session.add(new_rubric)
        db.session.commit()
        flash('Rubric generated successfully!')
        return redirect(url_for('dashboard.index'))
    return render_template('rubrics/generate.html')
