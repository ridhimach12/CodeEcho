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
- **Grounded AI Explanations & Root-Cause Hypotheses**:
  - Synthesizes plain-language pattern explanations citing exact commit SHAs, file paths, and line deltas.
  - Mitigates prompt injection by wrapping untrusted code diffs and commit messages in `<untrusted_diff>` XML encapsulation.
  - **Deterministic Fallback**: If LLM API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) are unconfigured, CodeEcho transparently generates structured explanations directly from the AST mutation profile via `codeecho-rule-engine-v1`.
  - Distinguishes unverified hypotheses from facts (`HYPOTHESIS:`) and recommends concrete systemic remedies (e.g. typing, mypy, custom linter rule).
- **Natural Language Repository Query Service (`NLQueryService`)**:
  - Answers questions regarding pattern rankings, affected files, commit lists, temporal chronology, structural shifts, and fixes.
  - Grounded citations: provides clickable citations to clusters, commits, and files.
  - Scope containment: out-of-scope or speculative questions are safely rejected.
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

## 📊 Empirical Multi-Repository Validation Results

Validated end-to-end on diverse real-world open-source repositories:

| Repository | Commits Mined | Python Changes Extracted | Clusters Discovered ($K$) | Noise Points | Analysis Runtime | Representative Finding |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`pallets/click`** | 20 | 96 | 12 | 22 | 2.96s | Recurrent parameter parsing & type validation refactorings (`src/click/types.py`) |
| **`psf/requests`** | 20 | 36 | 3 | 12 | 4.61s | Recurrent exception handling & return statement adaptations (`src/requests/models.py`) |
| **`bottlepy/bottle`** | 20 | 72 | 8 | 21 | 4.26s | Simplified conditional branching & header manipulation (`bottle.py`) |
| **Non-Python Repo (Edge Case)** | 4 | 0 | 0 | 0 | 0.05s | Handled zero Python changes gracefully with 0 clusters & 0 noise |

---

## 🔬 Empirical Ablation Study (386 Mined Changes)

Evaluation across representation strategies on real repository diffs (report in [`experiments/ablation_study_report.md`](experiments/ablation_study_report.md)):

| Representation Configuration | Algorithm | Clusters ($K$) | Noise Points | Noise % | Intra-Cluster Sim | Silhouette |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline 1: TF-IDF Only ($w_{\text{sem}}=1.0$)** | DBSCAN | 41 | 25 | 6.5% | 0.929 | 0.3655 |
| **Baseline 2: AST Structural Only ($w_{\text{struct}}=1.0$)** | DBSCAN | 3 | 62 | 16.1% | 0.759 | 0.1872 |
| **Proposed: Dual Fused ($w_{\text{sem}}=0.7, w_{\text{struct}}=0.3$)** | DBSCAN | 40 | 20 | 5.2% | 0.932 | 0.1635 |
| **Fused + Strict ($\epsilon=0.25$)** | DBSCAN | 70 | 42 | 10.9% | 0.961 | 0.5740 |
| **Fused + HDBSCAN** | HDBSCAN | 126 | 46 | 11.9% | 0.981 | 0.8815 |

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

# Run pytest unit and API tests (59 passing tests)
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

### 4. Docker Production Deployment (Unified Container)
```bash
# Build and run unified production container (serves frontend & backend on port 8000)
docker compose up --build -d

# Check health
curl http://localhost:8000/api/v1/health
```

---

## 🧪 Verified Milestones

- [x] **Milestone 1 (Day 1)**: Workspace setup, Git mining engine, AST/diff hunk parsing, normalization, FastAPI backend skeleton, React + Vite + Tailwind frontend scaffold, 11 passing automated tests.
- [x] **Milestone 2 (Day 2)**: Python AST feature extractor (`PythonASTParser`), TF-IDF baseline vectorizer (`TFIDFEmbedder`), weak supervision heuristic pair generator (`WeakSupervisionGenerator`), 26 passing automated tests.
- [x] **Milestone 3 (Day 3)**: Density clustering engine (`ClusteringEngine`), medoid exemplar selection, SQLite persistence with SQLAlchemy, analysis service, real-world validation on `pallets/click` (10 patterns discovered in 3.46s).
- [x] **Milestone 4 (Day 4)**: Frontend integration with real analysis APIs, lifecycle polling banner, interactive dashboard, pattern explorer with unified diff viewer, temporal recurrence timeline, 33 passing automated tests.
- [x] **Milestone 5 (Day 5)**: Grounded AI explanation engine with deterministic fallback (`codeecho-rule-engine-v1`), prompt injection mitigation, natural language repository query engine (`NLQueryService`), pattern detail modal explanation tab, repository Q&A interface, 51 passing automated tests.
- [x] **Milestone 6 (Day 6)**: Multi-repo empirical validation (`pallets/click`, `psf/requests`, `bottlepy/bottle`), empirical ablation study (386 changes), security audit & hardening (SSRF, injection, path traversal, stale run cleanup), multi-stage Dockerfile and docker-compose deployment, 59 passing automated tests.
- [ ] **Milestone 7 (Day 7)**: Evaluation benchmarks (ablation study, silhouette, Davies-Bouldin), research paper draft.
