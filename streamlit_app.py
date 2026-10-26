import io
import re
import zipfile
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from fpdf import FPDF
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Page configuration
st.set_page_config(
    page_title="Mr. Strict — AI Exam Evaluator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="Loading Sentence-BERT model (all-MiniLM-L6-v2)...")
def load_evaluator_model():
    """Cache the lightweight Sentence-BERT model in memory."""
    return SentenceTransformer("all-MiniLM-L6-v2")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text).strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""


def parse_questions_from_text(raw_text: str) -> Dict[str, str]:
    """Parse text into questions and answers using regex (e.g. Q1., Q2., Question 1:, 1., etc.)."""
    pattern = r"(?:(?<=\n)|^)(?:Q(?:uestion)?\.?\s*(\d+)|(\d+)\.)[\s:]+"
    splits = re.split(pattern, raw_text, flags=re.IGNORECASE)

    questions = {}
    if len(splits) > 1:
        # splits will contain groups: (q_num_1, q_num_2, content)
        i = 1
        while i < len(splits):
            q_num = splits[i] or splits[i + 1]
            content = splits[i + 2] if i + 2 < len(splits) else ""
            if q_num and content:
                questions[f"Q{q_num.strip()}"] = content.strip()
            i += 3
    else:
        # Fallback if no explicit Question numbering is detected
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        if paragraphs:
            for idx, p in enumerate(paragraphs, 1):
                questions[f"Section {idx}"] = p
        else:
            questions["Full Submission"] = raw_text

    return questions


def compute_semantic_score(
    model: SentenceTransformer, student_answer: str, reference_answer: str
) -> float:
    """Compute normalized cosine similarity (0.0 to 1.0) between student and reference text."""
    if not student_answer.strip() or not reference_answer.strip():
        return 0.0

    embeddings = model.encode([student_answer, reference_answer])
    sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    # Bound between 0.0 and 1.0
    return float(max(0.0, min(1.0, sim)))


def generate_excel_report(
    eval_results: List[Dict], plagiarism_df: pd.DataFrame
) -> bytes:
    """Create an Excel summary report with scores and plagiarism data."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Scores
        scores_data = []
        for res in eval_results:
            row = {
                "Student Name": res["student_name"],
                "Total Marks Obtained": round(res["total_marks"], 2),
                "Max Possible Marks": res["max_marks"],
                "Percentage (%)": round(res["percentage"], 2),
            }
            # Add breakdown per question
            for q_id, q_data in res["breakdown"].items():
                row[f"{q_id} Score"] = round(q_data["score"], 2)
                row[f"{q_id} Similarity"] = f"{round(q_data['similarity'] * 100, 1)}%"
            scores_data.append(row)

        df_scores = pd.DataFrame(scores_data)
        df_scores.to_excel(writer, sheet_name="Grades & Scores", index=False)

        # Sheet 2: Plagiarism Matrix
        if not plagiarism_df.empty:
            plagiarism_df.to_excel(writer, sheet_name="Plagiarism Matrix")

    return output.getvalue()


def generate_pdf_summary(
    eval_results: List[Dict], flags: List[str]
) -> bytes:
    """Create an official PDF evaluation summary."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title Banner
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, "Mr. Strict — Evaluation & Assessment Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, "AI-Assisted Semantic Scoring & Integrity Analysis", ln=True, align="C")
    pdf.ln(8)

    # Class Performance Summary
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "1. Grade Summary", ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(60, 8, " Student Name", border=1, fill=True)
    pdf.cell(40, 8, " Marks Obtained", border=1, fill=True, align="C")
    pdf.cell(40, 8, " Max Marks", border=1, fill=True, align="C")
    pdf.cell(40, 8, " Percentage", border=1, fill=True, align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    for res in eval_results:
        pdf.cell(60, 8, f" {res['student_name']}", border=1)
        pdf.cell(40, 8, f"{res['total_marks']:.2f}", border=1, align="C")
        pdf.cell(40, 8, f"{res['max_marks']}", border=1, align="C")
        pdf.cell(40, 8, f"{res['percentage']:.1f}%", border=1, align="C")
        pdf.ln(8)

    pdf.ln(6)

    # Integrity & Plagiarism Flags
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "2. Integrity & Similarity Alerts (>= 90%)", ln=True)
    pdf.set_font("Helvetica", "", 10)

    if flags:
        pdf.set_text_color(185, 28, 28)
        for flag in flags:
            pdf.multi_cell(0, 6, f"[FLAG] {flag}")
            pdf.ln(1)
    else:
        pdf.set_text_color(22, 101, 52)
        pdf.cell(0, 6, "No high-similarity (>=90%) pairwise collisions detected between students.", ln=True)

    pdf.set_text_color(0, 0, 0)
    return pdf.output()


# --- Streamlit UI Layout ---
model = load_evaluator_model()

st.title("🎓 Mr. Strict — AI Exam Evaluator")
st.caption("Local-first, single-stack automated evaluation using Sentence-BERT & Cosine Similarity")

with st.sidebar:
    st.header("⚙️ Configuration")
    plagiarism_threshold = st.slider(
        "Plagiarism Alert Threshold (%)",
        min_value=50,
        max_value=100,
        value=90,
        step=5,
        help="Flag pairs of student submissions exceeding this pairwise similarity score.",
    )
    st.divider()
    st.markdown(
        """
        **How it works:**
        1. 📄 **Upload Answer Key**: Extracts questions & reference answers.
        2. 📂 **Upload Submissions**: Accepts multiple PDFs or a single `.zip` file.
        3. ⚖️ **Set Marks**: Assign marks per question.
        4. 🚀 **Evaluate**: Semantic NLP grading + Peer Plagiarism Matrix.
        5. 📥 **Export**: Download Excel & PDF reports.
        """
    )
    st.divider()
    st.info("💡 Powered by Sentence-BERT (`all-MiniLM-L6-v2`) running locally on CPU/GPU.")

tab1, tab2, tab3 = st.tabs(["📝 1. Upload & Setup", "📊 2. Evaluation Results", "🔍 3. Plagiarism Matrix"])

with tab1:
    st.subheader("Step 1: Upload Teacher's Answer Key")
    key_file = st.file_uploader("Upload Answer Key (PDF)", type=["pdf"], key="key_uploader")

    answer_key_dict = {}
    if key_file:
        key_text = extract_text_from_pdf(key_file.read())
        if key_text:
            answer_key_dict = parse_questions_from_text(key_text)
            st.success(f"Extracted {len(answer_key_dict)} question(s) from Answer Key.")
            with st.expander("Preview Detected Questions & Reference Answers"):
                for q_id, q_text in answer_key_dict.items():
                    st.markdown(f"**{q_id}**: {q_text[:300]}..." if len(q_text) > 300 else f"**{q_id}**: {q_text}")
        else:
            st.warning("Could not extract text from the uploaded Answer Key PDF.")

    st.divider()

    st.subheader("Step 2: Assign Question Weights (Marks)")
    question_weights = {}
    if answer_key_dict:
        cols = st.columns(min(len(answer_key_dict), 4))
        for idx, q_id in enumerate(answer_key_dict.keys()):
            with cols[idx % len(cols)]:
                question_weights[q_id] = st.number_input(
                    f"Marks for {q_id}",
                    min_value=1.0,
                    max_value=100.0,
                    value=10.0,
                    step=1.0,
                    key=f"weight_{q_id}",
                )
    else:
        st.info("Upload an Answer Key above to configure question marks.")

    st.divider()

    st.subheader("Step 3: Upload Student Answer Sheets")
    upload_method = st.radio("Choose upload format:", ["Multiple PDF Files", "Single ZIP Archive containing PDFs"], horizontal=True)

    student_submissions = {}

    if upload_method == "Multiple PDF Files":
        student_files = st.file_uploader(
            "Upload Student Submissions (PDFs)",
            type=["pdf"],
            accept_multiple_files=True,
            key="student_files_uploader",
        )
        if student_files:
            for s_file in student_files:
                student_name = s_file.name.replace(".pdf", "").replace("_", " ").title()
                extracted = extract_text_from_pdf(s_file.read())
                if extracted:
                    student_submissions[student_name] = extracted
            st.success(f"Loaded {len(student_submissions)} student submission(s).")

    else:
        zip_file = st.file_uploader("Upload Student Submissions ZIP", type=["zip"], key="zip_uploader")
        if zip_file:
            try:
                with zipfile.ZipFile(io.BytesIO(zip_file.read())) as z:
                    for filename in z.namelist():
                        if filename.lower().endswith(".pdf") and not filename.startswith("__MACOSX"):
                            with z.open(filename) as f:
                                student_name = filename.split("/")[-1].replace(".pdf", "").replace("_", " ").title()
                                extracted = extract_text_from_pdf(f.read())
                                if extracted:
                                    student_submissions[student_name] = extracted
                st.success(f"Extracted {len(student_submissions)} student PDF(s) from ZIP archive.")
            except Exception as e:
                st.error(f"Error reading ZIP file: {e}")

    # Evaluate Button
    can_evaluate = bool(answer_key_dict and student_submissions)
    if st.button("🚀 Start AI Evaluation", type="primary", disabled=not can_evaluate):
        with st.spinner("Evaluating student submissions with Sentence-BERT..."):
            eval_results = []
            student_texts = []
            student_names = list(student_submissions.keys())

            total_max_marks = sum(question_weights.values())

            for name in student_names:
                full_sub_text = student_submissions[name]
                student_texts.append(full_sub_text)
                sub_questions = parse_questions_from_text(full_sub_text)

                breakdown = {}
                student_total_marks = 0.0

                for q_id, ref_ans in answer_key_dict.items():
                    # Check if student answered this question specifically
                    s_ans = sub_questions.get(q_id, full_sub_text)
                    sim = compute_semantic_score(model, s_ans, ref_ans)
                    max_q_marks = question_weights[q_id]
                    q_score = sim * max_q_marks

                    student_total_marks += q_score
                    breakdown[q_id] = {
                        "similarity": sim,
                        "score": q_score,
                        "max": max_q_marks,
                    }

                percentage = (student_total_marks / total_max_marks * 100) if total_max_marks > 0 else 0.0

                eval_results.append({
                    "student_name": name,
                    "total_marks": student_total_marks,
                    "max_marks": total_max_marks,
                    "percentage": percentage,
                    "breakdown": breakdown,
                })

            # Calculate Plagiarism Matrix
            plagiarism_flags = []
            plagiarism_df = pd.DataFrame()
            if len(student_names) > 1:
                sub_embeddings = model.encode(student_texts)
                sim_matrix = cosine_similarity(sub_embeddings)
                plagiarism_df = pd.DataFrame(sim_matrix, index=student_names, columns=student_names)

                threshold_val = plagiarism_threshold / 100.0
                for i in range(len(student_names)):
                    for j in range(i + 1, len(student_names)):
                        score = sim_matrix[i][j]
                        if score >= threshold_val:
                            pct = round(score * 100, 1)
                            plagiarism_flags.append(
                                f"{student_names[i]} and {student_names[j]} exhibit {pct}% content similarity!"
                            )

            st.session_state["eval_results"] = eval_results
            st.session_state["plagiarism_df"] = plagiarism_df
            st.session_state["plagiarism_flags"] = plagiarism_flags
            st.success("Evaluation complete! Navigate to 'Evaluation Results' tab to view scores.")

# Tabs 2 & 3: Results Display
eval_results = st.session_state.get("eval_results")
plagiarism_df = st.session_state.get("plagiarism_df")
plagiarism_flags = st.session_state.get("plagiarism_flags", [])

with tab2:
    if eval_results:
        st.subheader("Class Evaluation Summary")

        # Metric cards
        avg_score = np.mean([r["percentage"] for r in eval_results])
        top_score = max([r["percentage"] for r in eval_results])
        lowest_score = min([r["percentage"] for r in eval_results])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Submissions", len(eval_results))
        m2.metric("Average Score", f"{avg_score:.1f}%")
        m3.metric("Highest Score", f"{top_score:.1f}%")
        m4.metric("Lowest Score", f"{lowest_score:.1f}%")

        st.divider()

        # Score Table
        summary_rows = [
            {
                "Student Name": r["student_name"],
                "Marks Obtained": f"{r['total_marks']:.2f} / {r['max_marks']}",
                "Percentage": f"{r['percentage']:.1f}%",
            }
            for r in eval_results
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        # Question Breakdown
        with st.expander("Detailed Question-by-Question Marks Breakdown"):
            breakdown_list = []
            for r in eval_results:
                row = {"Student": r["student_name"]}
                for q_id, q_data in r["breakdown"].items():
                    row[f"{q_id} Marks"] = f"{q_data['score']:.2f}/{q_data['max']}"
                    row[f"{q_id} Sim"] = f"{round(q_data['similarity'] * 100, 1)}%"
                breakdown_list.append(row)
            st.dataframe(pd.DataFrame(breakdown_list), use_container_width=True)

        st.divider()

        # Downloads
        st.subheader("📥 Export Reports")
        c1, c2 = st.columns(2)

        with c1:
            excel_bytes = generate_excel_report(eval_results, plagiarism_df if plagiarism_df is not None else pd.DataFrame())
            st.download_button(
                label="📊 Download Excel Report (.xlsx)",
                data=excel_bytes,
                file_name="mr_strict_evaluation_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

        with c2:
            pdf_bytes = generate_pdf_summary(eval_results, plagiarism_flags)
            st.download_button(
                label="📄 Download Official PDF Summary (.pdf)",
                data=pdf_bytes,
                file_name="mr_strict_evaluation_summary.pdf",
                mime="application/pdf",
            )
    else:
        st.info("Run an evaluation from the 'Upload & Setup' tab to view results here.")

with tab3:
    if plagiarism_df is not None and not plagiarism_df.empty:
        st.subheader("Peer Plagiarism & Collusion Detection")

        if plagiarism_flags:
            st.error(f"⚠️ {len(plagiarism_flags)} Potential Plagiarism Case(s) Flagged (Threshold >= {plagiarism_threshold}%):")
            for flag in plagiarism_flags:
                st.markdown(f"- **{flag}**")
        else:
            st.success("✅ No student submission pairs exceeded the selected similarity threshold.")

        st.markdown("#### Peer Similarity Matrix")
        # Format heatmap values as percentages
        st.dataframe(
            plagiarism_df.style.format("{:.1%}")
            .background_gradient(cmap="Reds", vmin=0.0, vmax=1.0),
            use_container_width=True,
        )
    else:
        st.info("Plagiarism matrix will appear here after running evaluation on 2 or more submissions.")
