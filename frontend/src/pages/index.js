import Head from 'next/head';
import { useState } from 'react';

export default function Home() {
  const [activeTab, setActiveTab] = useState('upload');
  const [answerKeyFile, setAnswerKeyFile] = useState(null);
  const [studentZipFile, setStudentZipFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState('');
  const [jobStatus, setJobStatus] = useState(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5000';

  const handleStartEvaluation = async (e) => {
    e.preventDefault();
    if (!answerKeyFile || !studentZipFile) {
      alert('Please select both the Answer Key PDF and the Student Submissions ZIP file.');
      return;
    }

    setStatusMsg('Uploading files and starting evaluation job...');
    const formData = new FormData();
    formData.append('teacher_pdf', answerKeyFile);
    formData.append('student_zip', studentZipFile);

    try {
      const res = await fetch(`${apiBase}/api/evaluations/start`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMsg(`Evaluation job started successfully! Job ID: ${data.job_id || 'active'}`);
        setJobStatus(data);
      } else {
        setStatusMsg(`Error: ${data.error || 'Failed to start evaluation.'}`);
      }
    } catch (err) {
      setStatusMsg(`Connection error: ${err.message}. Make sure backend is running at ${apiBase}`);
    }
  };

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', margin: 0, padding: 0, backgroundColor: '#f8fafc', minHeight: '100vh', display: 'flex' }}>
      <Head>
        <title>Mr.Strict — AI Assignment Evaluator</title>
      </Head>

      {/* Sidebar */}
      <div style={{ width: 250, backgroundColor: '#1e3a8a', color: '#fff', padding: 24 }}>
        <h2 style={{ margin: '0 0 24px 0', fontSize: '1.4rem' }}>Mr.Strict</h2>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            onClick={() => setActiveTab('upload')}
            style={{
              textAlign: 'left',
              padding: '10px 14px',
              backgroundColor: activeTab === 'upload' ? '#2563eb' : 'transparent',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              fontWeight: 'bold',
            }}
          >
            🚀 Evaluate (Step 1-3)
          </button>
          <button
            onClick={() => setActiveTab('results')}
            style={{
              textAlign: 'left',
              padding: '10px 14px',
              backgroundColor: activeTab === 'results' ? '#2563eb' : 'transparent',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            📊 Results Dashboard
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: 32 }}>
        <header style={{ backgroundColor: '#fff', padding: 20, borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', marginBottom: 24 }}>
          <h2 style={{ margin: 0, color: '#1e293b' }}>
            {activeTab === 'upload' ? 'AI-Assisted Evaluation (3-Step Workflow)' : 'Final Results Dashboard'}
          </h2>
        </header>

        {activeTab === 'upload' && (
          <div style={{ backgroundColor: '#fff', padding: 28, borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)', maxWidth: 750 }}>
            <form onSubmit={handleStartEvaluation}>
              {/* Step 1: Upload Answer Key */}
              <div style={{ marginBottom: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 8 }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#1d4ed8' }}>Step 1: Upload Answer Key</h4>
                <p style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#64748b' }}>
                  Upload the instructor answer key or rubric (Single PDF with questions and reference answers).
                </p>
                <input
                  type="file"
                  accept=".pdf"
                  required
                  onChange={(e) => setAnswerKeyFile(e.target.files[0])}
                  style={{ display: 'block', width: '100%' }}
                />
              </div>

              {/* Step 2: Upload Student Answer Sheets as ZIP */}
              <div style={{ marginBottom: 24, padding: 16, border: '1px solid #e2e8f0', borderRadius: 8 }}>
                <h4 style={{ margin: '0 0 8px 0', color: '#1d4ed8' }}>Step 2: Upload Student Answer Sheets (ZIP)</h4>
                <p style={{ margin: '0 0 12px 0', fontSize: '0.88rem', color: '#64748b' }}>
                  Upload a ZIP archive containing student PDF answer sheets (named by roll number, e.g. <code>22CS001.pdf</code>).
                </p>
                <input
                  type="file"
                  accept=".zip"
                  required
                  onChange={(e) => setStudentZipFile(e.target.files[0])}
                  style={{ display: 'block', width: '100%' }}
                />
              </div>

              {/* Step 3: Start Evaluation Button */}
              <div style={{ marginTop: 20 }}>
                <button
                  type="submit"
                  style={{
                    backgroundColor: '#16a34a',
                    color: '#fff',
                    border: 'none',
                    padding: '14px 28px',
                    fontSize: '1.05rem',
                    fontWeight: 'bold',
                    borderRadius: 6,
                    cursor: 'pointer',
                    width: '100%',
                  }}
                >
                  ▶ Start Evaluation
                </button>
              </div>
            </form>

            {statusMsg && (
              <div style={{ marginTop: 20, padding: 12, backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 6, color: '#166534', fontSize: '0.9rem' }}>
                {statusMsg}
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && (
          <div style={{ backgroundColor: '#fff', padding: 28, borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <h3 style={{ marginTop: 0 }}>Class Performance & Plagiarism Summary</h3>
            <p style={{ color: '#64748b' }}>
              Connects to the backend REST API to display semantic similarity scores, keyword coverage, suspected malpractice flags, and student-to-student plagiarism matrices.
            </p>
            <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
              <a
                href={`${apiBase}/api/evaluations/exports/excel`}
                target="_blank"
                rel="noreferrer"
                style={{ backgroundColor: '#0284c7', color: '#fff', padding: '10px 18px', borderRadius: 6, textDecoration: 'none', fontWeight: 'bold' }}
              >
                📥 Download Excel Gradebook
              </a>
              <a
                href={`${apiBase}/api/evaluations/exports/pdf`}
                target="_blank"
                rel="noreferrer"
                style={{ backgroundColor: '#475569', color: '#fff', padding: '10px 18px', borderRadius: 6, textDecoration: 'none', fontWeight: 'bold' }}
              >
                📥 Download Master PDF Report
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
