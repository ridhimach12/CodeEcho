export interface HealthStatus {
  status: string
  version: string
  environment: string
  timestamp: string
}

export interface AnalysisSummary {
  analysis_id: string
  repo_url: string
  owner: string
  repo: string
  status: 'PENDING' | 'CLONING' | 'EXTRACTING' | 'CLUSTERING' | 'COMPLETED' | 'FAILED'
  commit_limit: number
  commits_mined: number
  changes_extracted: number
  clusters_discovered: number
  noise_points: number
  clustering_algorithm: string
  execution_time_seconds: number
  error_message?: string | null
  started_at: string
  completed_at?: string | null
}

export interface ClusterDetail {
  id: number
  cluster_number: number
  label_name: string
  is_noise: boolean
  member_count: number
  avg_similarity: number
  dominant_shifts: string[]
  affected_files: string[]
  exemplar_change_id?: string | null
  exemplar_file?: string | null
  exemplar_diff?: string | null
}

export interface CodeChangeDetail {
  change_id: string
  commit_hash: string
  file_path: string
  old_start: number
  new_start: number
  deleted_code: string
  added_code: string
  raw_diff: string
  added_lines_count: number
  deleted_lines_count: number
  detected_shifts: string[]
  enclosing_scope?: string | null
  timestamp: string
}

export interface GroundedEvidenceItem {
  commit_hash: string
  file_path: string
  lines_summary: string
  evidence_snippet: string
}

export interface ClusterExplanation {
  cluster_id: number
  pattern_title: string
  plain_description: string
  supporting_evidence: GroundedEvidenceItem[]
  root_cause_hypothesis: string
  suggested_systemic_fix: string
  limitations_and_uncertainty: string
  explanation_mode: 'llm_generated' | 'deterministic_fallback'
  model_name: string
  confidence_score: number
}

export interface NLQueryCitation {
  type: 'cluster' | 'commit' | 'file'
  identifier: string
  description?: string
}

export interface NLQueryResponse {
  question: string
  answer: string
  confidence: number
  query_type: 'deterministic_db' | 'grounded_retrieval' | 'unsupported'
  citations: NLQueryCitation[]
}
