# Mr.Strict — Local-First Prototype User & Admin Guide

Welcome to **Mr.Strict**, a local-first automated grading and assignment analytics desktop web tool.

> [!WARNING]
> **Prototype & Security Notice:**
> This software is designed strictly for **local-first** execution on your personal workstation. The demo credentials (`demo` / `demo123`) are provided solely for evaluation and local prototyping. **Never expose this prototype to the public internet** or unencrypted external networks without replacing the authentication layer with enterprise multi-factor authentication and HTTPS certificates. Local files are not automatically encrypted merely because a login screen is present.

---

## 1. Quick Start

### Step 1: Open Terminal in the Project Directory
Navigate to:
```powershell
cd "c:\Users\Godwin Samraj\Downloads\Mr Strict"
```

### Step 2: Activate the Virtual Environment
On Windows PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```

### Step 3: Run the Application
```powershell
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 2. Signing In (Demo Credentials)

When accessing any grading or workspace screen, you will be prompted to authenticate:

- **Username:** `demo`
- **Password:** `demo123`

---

## 3. Local Workspace Management

All course materials, submissions, results, and backups remain on your own computer.

### Creating a Workspace
1. Click **📂 Workspaces** in the left sidebar.
2. In the **Create New Workspace** form, enter a unique folder name (e.g., `My_Class_2026`).
3. Click **Create Workspace**.
4. The system creates the following isolated directory structure on your disk under `MrStrictData/workspaces/<WorkspaceName>/`:

```
MrStrictData/
  workspaces/
    My_Class_2026/
      workspace.json                   # Metadata & version
      uploads/
        answer_keys/                   # Stored teacher rubric PDFs
        student_submissions/           # Stored student submission PDFs
      results/                         # Individual student feedback PDFs
      reports/                         # Master landscape mark sheets (PDF)
      exports/                         # Master CSV gradebook spreadsheets
      backups/                         # Workspace ZIP archives
```

### Switching Active Workspaces
- On the **Workspaces** page, click the **Open** button next to any existing workspace.
- The badge at the top of the screen will update to display the active workspace.
- All subsequent grading sessions, file uploads, reports, and dashboard trends will be automatically scoped to that workspace.

---

## 4. Grading an Assignment

1. Click **Evaluate Assignment** in the sidebar.
2. Enter the **Assignment Title** (e.g. `Midterm Quiz`).
3. Upload the **Teacher Rubric / Answer Key** (`.pdf`).
4. Select all **Student Submission PDFs** (multi-file upload supported).
5. Optional: Toggle **Enable "Blind" Grading Mode** to mask student names with Candidate IDs.
6. Click **Run Bulk Evaluation**.
7. Confirm or adjust the detected **Question Weights** (summing to 100%).
8. Click **Evaluate Assignments**.
9. The semantic similarity scores, question-by-question marks, and plagiarism flags will be generated and saved directly to the active workspace.

---

## 5. Backups and Restore

### Creating a Backup
- Go to **📂 Workspaces**.
- Click the **Backup** button next to any workspace.
- A complete, self-contained ZIP archive containing all uploads, reports, and exports will be generated in `MrStrictData/workspaces/<WorkspaceName>/backups/`.

### Restoring a Workspace
- To restore a workspace on a new machine or after a system wipe, simply unzip the archive into your `MrStrictData/workspaces/` folder.
- Mr.Strict will detect the `workspace.json` file and display the restored workspace on the Workspaces dashboard immediately upon refresh.

---

## 6. Running Automated Tests

To verify security, authentication, path traversal defense, and workspace isolation:
```powershell
.\venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```
