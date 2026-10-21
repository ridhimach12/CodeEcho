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
  - **Medoid Exemplar Selection**: Selects the change with highest intra-cluster similarity as the representative inspectable diff.
- **SQLite Persistence**:
  - Relational schema (`RepositoryDB`, `AnalysisRunDB`, `CommitDB`, `CodeChangeDB`, `PatternClusterDB`, `ClusterMembershipDB`).
  - Persistent across server restarts.
- **Full Interactive Web UI (React + Vite + Tailwind CSS)**:
  - **Repo Ingestion**: Input form with commit limit slider, algorithm selector (DBSCAN/HDBSCAN), and presets (`pallets/click`, `psf/requests`).
  - **Lifecycle Stepper**: Real-time polling indicator (`PENDING` $\rightarrow$ `CLONING` $\rightarrow$ `EXTRACTING` $\rightarrow$ `CLUSTERING` $\rightarrow$ `COMPLETED`).
  - **Analysis Dashboard**: Responsive metric cards, cluster size distribution bars, and dominant AST shift tags.
  - **Pattern Explorer**: Filter by noise points, sort by size/similarity, search by pattern shifts and affected files.
  - **Pattern Detail Modal**: Unified diff viewer with syntax colors (`+` green, `-` red), exemplar diff tab, constituent changes list, and clickable links to GitHub commits.
  - **Temporal Timeline**: Interactive chart visualizing when each pattern occurred across chronological commit timestamps.

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

# Run pytest unit and API tests (33 passing tests)
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
npm run build   # Verified clean production build
npm run dev     # Starts Vite dev server
```
Application interface will be available at: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Verified Milestones

- [x] **Milestone 1 (Day 1)**: Workspace setup, Git mining engine, AST/diff hunk parsing, normalization, FastAPI backend skeleton, React + Vite + Tailwind frontend scaffold, 11 passing automated tests.
- [x] **Milestone 2 (Day 2)**: Python AST feature extractor (`PythonASTParser`), TF-IDF baseline vectorizer (`TFIDFEmbedder`), weak supervision heuristic pair generator (`WeakSupervisionGenerator`), 26 passing automated tests.
- [x] **Milestone 3 (Day 3)**: Density clustering engine (`ClusteringEngine`), medoid exemplar selection, SQLite persistence with SQLAlchemy, analysis service, real-world validation on `pallets/click` (10 patterns discovered in 3.46s).
- [x] **Milestone 4 (Day 4)**: Frontend integration with real analysis APIs, lifecycle polling banner, interactive dashboard, pattern explorer with unified diff viewer, temporal recurrence timeline, 33 passing automated tests.
- [ ] **Milestone 5 (Day 5)**: Grounded root-cause explainer, deterministic fallback, NL repository query.
- [ ] **Milestone 6 (Day 6)**: Multi-repo validation, Docker containerization, public cloud deployment.
- [ ] **Milestone 7 (Day 7)**: Evaluation benchmarks (ablation study, silhouette, Davies-Bouldin), research paper draft.
