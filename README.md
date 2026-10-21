# CodeEcho 🔍

> **CodeEcho: An AI-Assisted Pattern Recognition System for Detecting Recurring Anti-Patterns in Software Repositories.**  
> *B.Tech CSE-AI Capstone & Academic Research Project*

---

## 📌 Overview

CodeEcho mines Git commit history and code diffs across software repositories to detect recurring anti-patterns and systemic mistakes. By pairing structural AST modifications with semantic code representations and unsupervised clustering, CodeEcho identifies repeating changes, tracks their temporal evolution across repository history, and provides grounded root-cause explanations with concrete suggestions for systemic fixes.

---

## 🏗️ Architecture & Features

- **Safe Git Ingestion**: Depth-limited shallow clones, protocol checks, URL sanitation, and strict timeouts.
- **Diff & Commit Extraction**: Unified diff parsing, hunk decomposition, issue reference linkage (`#101`), revert commit detection.
- **Normalization Engine**: Strips docstrings, comments, and whitespace noise; canonicalizes local identifiers (`VAR_1`, `VAR_2`) to eliminate variable renaming artifacts.
- **Structural AST Parsing**:
  - Extracts 12-dimensional structural programming metrics (Try/Except/Raise, None-guards, conditionals, returns, loops, function definitions, calls, assignments, asserts, with).
  - Resilient multi-tier fallback (wrapper context, statement extraction, and regex token heuristics) that never crashes on partial or truncated diff hunks.
  - Detects behavioral shifts (`added_none_guard`, `added_exception_handling`, `added_explicit_raise`).
- **Baseline Embeddings (`BaseEmbedder` & `TFIDFEmbedder`)**:
  - Combines word/operator n-grams with character sub-tokens for syntax-aware code representations.
  - Fixed output dimension, pre-warmed vocabulary, zero-vector handling for empty inputs, and safe L2 normalization.
- **Calibrated Weak Supervision**:
  - Generates positive and negative training/evaluation pairs using repository signals (shared issue references, revert retractions, temporal proximity).
  - Explicit confidence scoring (0.85 for same-file shared issues, 0.55 for cross-file issues, 0.90 for reverts, 0.88 for sampled distant negatives).
- **Interactive UI & REST API**:
  - FastAPI backend with `/api/v1/health`, `/api/v1/validate-repo`, and `/api/v1/extract-features`.
  - React + Vite + Tailwind dashboard with live status badge and demo presets (`pallets/click`, `psf/requests`).

---

## ⚠️ Current Scope & Limitations (Milestone 2)

- **Clustering in Progress**: Features and embeddings are now extractable; candidate pattern clustering is scheduled for **Milestone 3**.
- **Python AST Focus**: Full AST parsing is currently implemented for Python (`.py`). Other file types are handled via tokenization and TF-IDF representations.
- **Weak Supervision Signals**: Weak labels represent noisy heuristics rather than human-verified ground truth; confidence values and assumptions are documented per pair.

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git CLI (v2.40+)

### 2. Backend Setup
```bash
# Navigate to project root
cd CodeEcho

# Create and activate virtual environment
python -m venv backend/venv --system-site-packages
# On Windows PowerShell:
.\backend\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Run pytest unit tests (26 passing tests)
$env:PYTHONPATH="."
pytest backend/tests -v

# Run FastAPI dev server
uvicorn backend.app.main:app --reload --port 8000
```
Swagger UI will be available at: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Vite dev server will be available at: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Verified Milestones

- [x] **Milestone 1 (Day 1)**: Workspace setup, Git mining engine, AST/diff hunk parsing, normalization, FastAPI backend skeleton, React + Vite + Tailwind frontend scaffold, 11 passing automated tests.
- [x] **Milestone 2 (Day 2)**: Python AST feature extractor (`PythonASTParser`), TF-IDF baseline vectorizer (`TFIDFEmbedder`), weak supervision heuristic pair generator (`WeakSupervisionGenerator`), 26 passing automated tests, frontend production build verified.
- [ ] **Milestone 3 (Day 3)**: DBSCAN / HDBSCAN clustering engine, exemplar selection, SQLite database persistence with SQLAlchemy.
- [ ] **Milestone 4 (Day 4)**: Asynchronous background analysis worker, pattern explorer UI, temporal timeline.
- [ ] **Milestone 5 (Day 5)**: Grounded root-cause explainer, deterministic fallback, NL repository query.
- [ ] **Milestone 6 (Day 6)**: Integration testing on real open-source repos (`pallets/click`), cloud deployment.
- [ ] **Milestone 7 (Day 7)**: Evaluation benchmarks (ablation study, silhouette, Davies-Bouldin), research paper draft.
