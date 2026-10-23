from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response, session
from werkzeug.utils import secure_filename
from app.auth_utils import login_required
from app.services.evaluator import extract_text_from_pdf, preprocess_text, evaluate_assignment, detect_plagiarism, parse_questions
from app.services import workspace_service
from app.models import Assignment, Submission, Student
from app import db
import json
import csv
import io
import os
import uuid
import shutil
import random
from fpdf import FPDF # fpdf2 uses FPDF

grading_bp = Blueprint('grading', __name__, url_prefix='/grading')

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_active_workspace_name():
    ws = session.get('active_workspace', 'default')
    if not workspace_service.workspace_exists(ws):
        try:
            workspace_service.create_workspace(ws, "Default Workspace")
        except:
            pass
    return ws

@grading_bp.route('/evaluate', methods=['GET', 'POST'])
@login_required
def evaluate():
    active_ws = get_active_workspace_name()
    ws_dir = workspace_service.ensure_workspace_layout(active_ws)

    if request.method == 'POST':
        student_files = request.files.getlist('student_pdfs')
        teacher_file = request.files.get('teacher_pdf')
        assignment_title = (request.form.get('assignment_title') or '').strip()
        is_blind = True if request.form.get('is_blind') else False
        
        if not student_files or not teacher_file or not assignment_title:
            flash('Please provide an assignment title, the Teacher Rubric, and at least one Student PDF.')
            return redirect(url_for('grading.evaluate'))
            
        if not teacher_file.filename or not allowed_file(teacher_file.filename):
            flash('Invalid Teacher Rubric file. Only valid .pdf files are accepted.')
            return redirect(url_for('grading.evaluate'))

        valid_student_files = [f for f in student_files if f.filename and allowed_file(f.filename)]
        if not valid_student_files:
            flash('No valid student PDF files selected. Please upload files ending in .pdf.')
            return redirect(url_for('grading.evaluate'))

        batch_id = str(uuid.uuid4())
        # Store in workspace uploads folder so it is preserved across restarts
        batch_dir = os.path.join(ws_dir, 'uploads', batch_id)
        os.makedirs(batch_dir, exist_ok=True)
        
        # Save Teacher File in batch_dir and archive to answer_keys
        teacher_path = os.path.join(batch_dir, 'teacher.pdf')
        teacher_file.save(teacher_path)
        try:
            shutil.copy2(teacher_path, os.path.join(ws_dir, 'uploads', 'answer_keys', f"{batch_id}_teacher.pdf"))
        except:
            pass
        
        # Extract teacher questions immediately for the Weights UI
        with open(teacher_path, 'rb') as f:
            teacher_raw = extract_text_from_pdf(f)
            teacher_clean = preprocess_text(teacher_raw)
            teacher_qs = parse_questions(teacher_clean)
            
        if not teacher_qs:
            flash('Could not extract any questions or text from the teacher rubric. Ensure the PDF contains text.')
            shutil.rmtree(batch_dir, ignore_errors=True)
            return redirect(url_for('grading.evaluate'))
            
        # Save Student Files and build metadata
        metadata = {
            "assignment_title": assignment_title,
            "is_blind": is_blind,
            "workspace_name": active_ws,
            "students": []
        }
        
        for idx, student_file in enumerate(valid_student_files):
            clean_name = secure_filename(student_file.filename)
            student_name = clean_name.rsplit('.', 1)[0] or f"student_{idx}"
            safe_filename = f"student_{idx}.pdf"
            student_save_path = os.path.join(batch_dir, safe_filename)
            student_file.save(student_save_path)
            try:
                shutil.copy2(student_save_path, os.path.join(ws_dir, 'uploads', 'student_submissions', f"{batch_id}_{safe_filename}"))
            except:
                pass

            metadata["students"].append({
                "real_name": student_name,
                "file": safe_filename
            })
            
        with open(os.path.join(batch_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        # Proceed to step 2: Weight Assignment
        return render_template('grading/set_weights.html', batch_id=batch_id, questions=teacher_qs.keys(), title=assignment_title)

    return render_template('grading/evaluate.html', active_workspace=active_ws)


@grading_bp.route('/weights/<batch_id>', methods=['POST'])
@login_required
def process_weights(batch_id):
    active_ws = get_active_workspace_name()
    ws_dir = workspace_service.get_workspace_dir(active_ws)
    batch_dir = os.path.join(ws_dir, 'uploads', batch_id)
    
    # Fallback to check default upload folder if batch was created previously
    if not os.path.exists(batch_dir):
        fallback_dir = os.path.join('uploads', batch_id)
        if os.path.exists(fallback_dir):
            batch_dir = fallback_dir
        else:
            flash('Session expired or batch not found in the active workspace.')
            return redirect(url_for('grading.evaluate'))
        
    with open(os.path.join(batch_dir, 'metadata.json'), 'r', encoding='utf-8') as f:
        metadata = json.load(f)
        
    assignment_title = metadata['assignment_title']
    is_blind = metadata['is_blind']
    
    # Collect weights from form
    weights = {}
    total_weight = 0
    for key, val in request.form.items():
        if key.startswith('weight_'):
            q_id = key.replace('weight_', '')
            try:
                w = float(val)
                weights[q_id] = w
                total_weight += w
            except ValueError:
                pass
                
    if total_weight == 0:
        # Default to equal distribution if they somehow submitted 0s
        weights = {}
        
    new_assignment = Assignment(title=assignment_title, is_blind=is_blind, workspace_name=active_ws)
    db.session.add(new_assignment)
    db.session.commit()
    
    # Read Teacher
    with open(os.path.join(batch_dir, 'teacher.pdf'), 'rb') as f:
        teacher_raw = extract_text_from_pdf(f)
        teacher_clean = preprocess_text(teacher_raw)
        
    processed_count = 0
    student_data = []
    student_texts_dict = {}
    
    for s_meta in metadata['students']:
        real_name = s_meta['real_name']
        filename = s_meta['file']
        
        student = Student.query.filter_by(student_id=real_name).first()
        if not student:
            candidate_id = f"Candidate {random.randint(1000, 9999)}" if is_blind else None
            student = Student(name=real_name, student_id=real_name, candidate_id=candidate_id)
            db.session.add(student)
            db.session.commit()
        elif is_blind and not student.candidate_id:
            # Assign candidate ID retroactively if missing and blind mode is on
            student.candidate_id = f"Candidate {random.randint(1000, 9999)}"
            db.session.commit()
            
        with open(os.path.join(batch_dir, filename), 'rb') as f:
            student_raw = extract_text_from_pdf(f)
            student_clean = preprocess_text(student_raw)
            
        student_data.append({
            "student": student,
            "clean_text": student_clean
        })
        student_texts_dict[student.name] = student_clean
        
    plagiarism_flags = detect_plagiarism(student_texts_dict)
    
    for data in student_data:
        student = data["student"]
        student_clean = data["clean_text"]
        
        evaluation = evaluate_assignment(student_clean, teacher_clean, weights=weights)
        flag = plagiarism_flags.get(student.name, None)
        
        submission = Submission(
            student_id=student.id,
            assignment_id=new_assignment.id,
            content_text=student_clean,
            score=evaluation.get("score"),
            question_scores=json.dumps(evaluation.get("question_scores", {})),
            feedback="{}",
            plagiarism_flag=flag
        )
        db.session.add(submission)
        processed_count += 1
        
    db.session.commit()
    
    # Cleanup Temp Files
    try:
        shutil.rmtree(batch_dir)
    except:
        pass
        
    if processed_count > 0:
        flash(f'Successfully evaluated {processed_count} assignments with custom weights and AI Feedback!')
        return redirect(url_for('grading.report', assignment_id=new_assignment.id))
    else:
        flash('No valid student files were processed.')
        return redirect(url_for('grading.evaluate'))

@grading_bp.route('/report/<int:assignment_id>')
@login_required
def report(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    
    avg_score = 0
    if submissions:
        avg_score = round(sum([sub.score for sub in submissions if sub.score is not None]) / len(submissions), 2)
        
    for sub in submissions:
        if sub.question_scores:
            sub.q_scores_dict = json.loads(sub.question_scores)
        else:
            sub.q_scores_dict = {}
            
    return render_template('grading/report.html', assignment=assignment, submissions=submissions, avg_score=avg_score)

@grading_bp.route('/report/<int:assignment_id>/download')
@login_required
def download_report(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    
    pdf = FPDF(orientation="landscape")
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Detailed Mark Report: {assignment.title}", ln=True, align="C")
    pdf.ln(10)
    
    all_questions = set()
    for sub in submissions:
        if sub.question_scores:
            q_dict = json.loads(sub.question_scores)
            all_questions.update(q_dict.keys())
            
    sorted_questions = sorted(list(all_questions))
    
    name_col_width = 60
    total_col_width = 30
    remaining_width = 277 - name_col_width - total_col_width
    q_col_width = remaining_width / max(1, len(sorted_questions))
    if q_col_width > 40:
        q_col_width = 40
        
    pdf.set_font("helvetica", "B", 10)
    col_title = "Candidate ID" if assignment.is_blind else "Student ID"
    pdf.cell(name_col_width, 10, col_title, border=1)
    
    for q in sorted_questions:
        pdf.cell(q_col_width, 10, q, border=1, align="C")
    pdf.cell(total_col_width, 10, "Total Mark", border=1, align="C")
    pdf.ln()
    
    pdf.set_font("helvetica", "", 10)
    for sub in submissions:
        display_name = sub.student.candidate_id if assignment.is_blind and sub.student.candidate_id else sub.student.name[:25]
        pdf.cell(name_col_width, 10, display_name, border=1)
        q_dict = json.loads(sub.question_scores) if sub.question_scores else {}
        
        for q in sorted_questions:
            score = str(q_dict.get(q, '-'))
            pdf.cell(q_col_width, 10, score, border=1, align="C")
            
        pdf.cell(total_col_width, 10, str(sub.score), border=1, align="C")
        pdf.ln()

    pdf_bytes = bytes(pdf.output())
    
    # Save copy to active workspace reports folder
    try:
        active_ws = get_active_workspace_name()
        ws_dir = workspace_service.get_workspace_dir(active_ws)
        with open(os.path.join(ws_dir, 'reports', f"report_{assignment.id}.pdf"), 'wb') as f:
            f.write(pdf_bytes)
    except:
        pass

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{assignment.id}.pdf'
    return response

@grading_bp.route('/report/<int:assignment_id>/csv')
@login_required
def download_csv(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    
    si = io.StringIO()
    cw = csv.writer(si)
    
    all_questions = set()
    for sub in submissions:
        if sub.question_scores:
            q_dict = json.loads(sub.question_scores)
            all_questions.update(q_dict.keys())
    sorted_questions = sorted(list(all_questions))
    
    # CSV always reveals true names
    headers = ["True Student ID", "Candidate ID (if blind)"] + sorted_questions + ["Total Mark", "Plagiarism Flag"]
    cw.writerow(headers)
    
    for sub in submissions:
        row = [sub.student.name, sub.student.candidate_id if sub.student.candidate_id else "N/A"]
        q_dict = json.loads(sub.question_scores) if sub.question_scores else {}
        for q in sorted_questions:
            row.append(q_dict.get(q, '-'))
        row.append(sub.score)
        row.append(sub.plagiarism_flag if sub.plagiarism_flag else "None")
        cw.writerow(row)
        
    csv_content = si.getvalue()
    
    # Save copy to active workspace exports folder
    try:
        active_ws = get_active_workspace_name()
        ws_dir = workspace_service.get_workspace_dir(active_ws)
        with open(os.path.join(ws_dir, 'exports', f"report_{assignment.id}.csv"), 'w', encoding='utf-8') as f:
            f.write(csv_content)
    except:
        pass

    output = make_response(csv_content)
    output.headers["Content-Disposition"] = f"attachment; filename=report_{assignment.id}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@grading_bp.route('/report/<int:assignment_id>/student/<int:student_id>/pdf')
@login_required
def student_feedback_pdf(assignment_id, student_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = Submission.query.filter_by(assignment_id=assignment_id, student_id=student_id).first_or_404()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Individual Feedback Report", ln=True, align="C")
    
    display_name = submission.student.candidate_id if assignment.is_blind and submission.student.candidate_id else submission.student.name
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, f"Student: {display_name}", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, f"Total Score: {submission.score}/100", ln=True)
    
    if submission.plagiarism_flag:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, f"WARNING: {submission.plagiarism_flag}", ln=True)
        pdf.set_text_color(0, 0, 0)
        
    pdf.ln(5)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Question Breakdown:", ln=True)
    
    q_dict = json.loads(submission.question_scores) if submission.question_scores else {}
    
    for q, score in sorted(q_dict.items()):
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 8, f"{q}: {score}/100", ln=True)
        
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Your Extracted Submission:", ln=True)
    pdf.set_font("helvetica", "", 9)
    clean_text = submission.content_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 5, clean_text)
    
    pdf_bytes = bytes(pdf.output())

    # Save copy to active workspace results folder
    try:
        active_ws = get_active_workspace_name()
        ws_dir = workspace_service.get_workspace_dir(active_ws)
        safe_name = secure_filename(display_name) or "student"
        with open(os.path.join(ws_dir, 'results', f"feedback_{assignment.id}_{safe_name}.pdf"), 'wb') as f:
            f.write(pdf_bytes)
    except:
        pass

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=feedback_{display_name}.pdf'
    return response
