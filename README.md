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
- **Unsupervised Pattern Discovery (`ClusteringEngine`)**:
  - Density-based clustering (DBSCAN & HDBSCAN) over cosine distance matrices.
  - Isolates non-repeating changes into an explicit Noise partition (`cluster_id = -1`).
  - **Medoid Exemplar Selection**: For every non-noise cluster, selects the change with highest intra-cluster similarity as the representative inspectable diff.
- **SQLite Persistence**:
  - Relational schema (`RepositoryDB`, `AnalysisRunDB`, `CommitDB`, `CodeChangeDB`, `PatternClusterDB`, `ClusterMembershipDB`).
  - Persistent across server restarts.
- **REST API Endpoints**:
  - `POST /api/v1/analyses`: Trigger background analysis on any public GitHub URL.
  - `GET /api/v1/analyses`: List past analyses and summary metrics.
  - `GET /api/v1/analyses/{id}`: Poll status (`PENDING`, `CLONING`, `EXTRACTING`, `CLUSTERING`, `COMPLETED`, `FAILED`).
  - `GET /api/v1/analyses/{id}/clusters`: Retrieve candidate patterns with exemplar code diffs.
  - `GET /api/v1/analyses/{id}/clusters/{cluster_id}/changes`: Retrieve member code changes.
  - `POST /api/v1/extract-features`: Live interactive diff inspector.

---

## 📊 Empirical Validation Results (pallets/click)

Ran end-to-end analysis on `https://github.com/pallets/click` with 15 commits:

| Metric | Measured Value |
| :--- | :--- |
| Commits Mined | 15 |
| Python Changes Extracted | 87 diff hunks |
| Candidate Patterns Discovered | 10 clusters |
| Noise Points | 18 changes |
| Execution Runtime | 3.46 seconds |
| Discovered Pattern Example | `Candidate Pattern #5: added_none_guard, added_conditional_branching, added_return_statement` (2 members, exemplar: `src/click/core.py`) |

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

# Run pytest unit tests (33 passing tests)
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
- [x] **Milestone 2 (Day 2)**: Python AST feature extractor (`PythonASTParser`), TF-IDF baseline vectorizer (`TFIDFEmbedder`), weak supervision heuristic pair generator (`WeakSupervisionGenerator`), 26 passing automated tests.
- [x] **Milestone 3 (Day 3)**: Density clustering engine (`ClusteringEngine` with DBSCAN & HDBSCAN), medoid exemplar selection, representation fusion pipeline, SQLite database persistence with SQLAlchemy, end-to-end background analysis service, 33 passing automated tests, real-world validation on `pallets/click` (10 patterns discovered in 3.46s).
- [ ] **Milestone 4 (Day 4)**: Frontend integration with real analysis APIs, interactive dashboard, cluster explorer with diff viewer, temporal recurrence timeline.
- [ ] **Milestone 5 (Day 5)**: Grounded root-cause explainer, deterministic fallback, NL repository query.
- [ ] **Milestone 6 (Day 6)**: Multi-repo testing, Docker containerization, cloud deployment.
- [ ] **Milestone 7 (Day 7)**: Evaluation benchmarks (ablation study, silhouette, Davies-Bouldin), research paper draft.
