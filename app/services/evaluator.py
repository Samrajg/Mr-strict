import PyPDF2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re
import urllib.request
import json

print("Loading local BERT model (all-MiniLM-L6-v2)...")
try:
    bert_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Failed to load BERT model: {e}")
    bert_model = None

def extract_text_from_pdf(pdf_stream):
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_stream)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF stream: {e}")
    return text.strip()

def preprocess_text(text):
    lines = text.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned_lines)

def parse_questions(text):
    questions = {}
    current_q = "General"
    current_text = []
    
    pattern = re.compile(r'^(?:Q(?:uestion)?\s*(\d+)[\.\:\)]?|(\d+)[\.\)])\s*(.*)', re.IGNORECASE)
    
    for line in text.split('\n'):
        match = pattern.match(line.strip())
        if match:
            if current_text:
                questions[current_q] = " ".join(current_text)
            q_num = match.group(1) or match.group(2)
            current_q = f"Q{q_num}"
            current_text = [match.group(3)]
        else:
            current_text.append(line.strip())
            
    if current_text:
        questions[current_q] = " ".join(current_text)
        
    if len(questions) == 1 and "General" in questions:
        return {"Q1": questions["General"]}
        
    if "General" in questions and not questions["General"].strip():
        del questions["General"]
        
    return questions

def evaluate_assignment(student_text, teacher_rubric_text, weights=None):
    if bert_model is None:
        return {"score": 0, "question_scores": {}, "overall_feedback": "Error: BERT model not loaded."}
        
    if not student_text or not teacher_rubric_text:
        return {"score": 0, "question_scores": {}, "overall_feedback": "Empty text provided."}

    try:
        teacher_qs = parse_questions(teacher_rubric_text)
        student_qs = parse_questions(student_text)
        
        question_scores = {}
        total_weighted_score = 0
        
        # If no weights provided or invalid, distribute equally
        use_weights = weights and len(weights) == len(teacher_qs) and sum(float(w) for w in weights.values()) > 0
        
        for q_id, teacher_ans in teacher_qs.items():
            if not teacher_ans.strip():
                continue
                
            student_ans = student_qs.get(q_id, "")
            
            if not student_ans.strip():
                base_score = 0
            else:
                embeddings = bert_model.encode([teacher_ans, student_ans])
                similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
                base_score = max(0, min(100, int(similarity * 100)))
                
            question_scores[q_id] = base_score
            
            # Weighting
            if use_weights and q_id in weights:
                weight_val = float(weights[q_id]) / 100.0
            else:
                weight_val = 1.0 / len(teacher_qs)
                
            total_weighted_score += base_score * weight_val
            
        final_score = int(total_weighted_score)
        
        return {
            "score": final_score,
            "question_scores": question_scores,
            "overall_feedback": f"Evaluated {len(teacher_qs)} questions via Local BERT."
        }
    except Exception as e:
        return {
            "score": 0,
            "question_scores": {},
            "overall_feedback": f"Error during evaluation: {str(e)}"
        }

def detect_plagiarism(student_texts_dict):
    if bert_model is None or len(student_texts_dict) < 2:
        return {}

    student_ids = list(student_texts_dict.keys())
    texts = list(student_texts_dict.values())
    
    flags = {}
    
    try:
        embeddings = bert_model.encode(texts)
        sim_matrix = cosine_similarity(embeddings)
        
        for i in range(len(student_ids)):
            for j in range(i + 1, len(student_ids)):
                sim = sim_matrix[i][j]
                if sim > 0.95:
                    msg = f"High similarity ({int(sim*100)}%) with {student_ids[j]}"
                    msg2 = f"High similarity ({int(sim*100)}%) with {student_ids[i]}"
                    
                    if student_ids[i] in flags:
                        flags[student_ids[i]] += f" | {msg}"
                    else:
                        flags[student_ids[i]] = msg
                        
                    if student_ids[j] in flags:
                        flags[student_ids[j]] += f" | {msg2}"
                    else:
                        flags[student_ids[j]] = msg2
    except Exception as e:
        print(f"Error in plagiarism detection: {e}")
        
    return flags
