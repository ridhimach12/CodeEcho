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
- **Dual Representation Engine**:
  - *Baseline*: AST structural change vector + Token TF-IDF (lightweight, runs in <50MB RAM).
  - *Semantic*: CodeBERT / GraphCodeBERT embedding interface.
- **Cluster & Pattern Discovery**: Density-based clustering (DBSCAN / HDBSCAN) over cosine distances.
- **Grounded Explanations**: Citations backed strictly by actual diff hunks and commit SHAs; deterministic fallback when no LLM key is configured.
- **Interactive UI**: React + Vite + Tailwind dashboard with temporal charts and diff explorer.

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

# Run pytest unit tests (11 passing tests)
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
- [ ] **Milestone 2 (Day 2)**: Python AST feature extractor, TF-IDF baseline vectorizer, weak supervision heuristic pairs.
- [ ] **Milestone 3 (Day 3)**: DBSCAN clustering engine, exemplar selection, SQLite database persistence.
- [ ] **Milestone 4 (Day 4)**: Asynchronous background analysis worker, pattern explorer UI, temporal timeline.
- [ ] **Milestone 5 (Day 5)**: Grounded root-cause explainer, deterministic fallback, NL repository query.
- [ ] **Milestone 6 (Day 6)**: Integration testing on real open-source repos (`pallets/click`), cloud deployment.
- [ ] **Milestone 7 (Day 7)**: Evaluation benchmarks (ablation study, silhouette, Davies-Bouldin), research paper draft.
