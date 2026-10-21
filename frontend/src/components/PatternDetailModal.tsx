import React, { useState, useEffect } from 'react'
import {
  X,
  ExternalLink,
  GitCommit,
  FileCode,
  Sparkles,
  Info,
  Copy,
  Check,
  Brain,
  AlertTriangle,
  Wrench,
  HelpCircle,
  ShieldCheck,
} from 'lucide-react'
import { ClusterDetail, CodeChangeDetail, ClusterExplanation } from '../types'

interface PatternDetailModalProps {
  cluster: ClusterDetail
  analysisId: string
  repoOwner: string
  repoName: string
  onClose: () => void
}

export const PatternDetailModal: React.FC<PatternDetailModalProps> = ({
  cluster,
  analysisId,
  repoOwner,
  repoName,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'explanation' | 'exemplar' | 'members'>('explanation')
  const [changes, setChanges] = useState<CodeChangeDetail[]>([])
  const [selectedChangeId, setSelectedChangeId] = useState<string | null>(null)
  const [isLoadingChanges, setIsLoadingChanges] = useState(false)
  const [copied, setCopied] = useState(false)

  // Explanation state
  const [explanation, setExplanation] = useState<ClusterExplanation | null>(null)
  const [isLoadingExplanation, setIsLoadingExplanation] = useState(false)
  const [explanationError, setExplanationError] = useState<string | null>(null)

  // Fetch constituent changes for this cluster
  useEffect(() => {
    setIsLoadingChanges(true)
    fetch(`/api/v1/analyses/${analysisId}/clusters/${cluster.id}/changes`)
      .then((res) => res.json())
      .then((data: CodeChangeDetail[]) => {
        setChanges(data)
        if (data.length > 0) {
          const defaultId = cluster.exemplar_change_id || data[0].change_id
          setSelectedChangeId(defaultId)
        }
      })
      .catch((err) => {
        console.error('Failed to load constituent changes:', err)
      })
      .finally(() => setIsLoadingChanges(false))
  }, [analysisId, cluster.id, cluster.exemplar_change_id])

  // Fetch grounded AI / deterministic explanation
  useEffect(() => {
    setIsLoadingExplanation(true)
    setExplanationError(null)
    fetch(`/api/v1/analyses/${analysisId}/clusters/${cluster.id}/explanation`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Failed to load explanation (${res.status})`)
        }
        return res.json()
      })
      .then((data: ClusterExplanation) => {
        setExplanation(data)
      })
      .catch((err) => {
        console.error('Failed to load explanation:', err)
        setExplanationError(err.message || 'Could not synthesize explanation.')
      })
      .finally(() => setIsLoadingExplanation(false))
  }, [analysisId, cluster.id])

  // Get currently inspected change
  const currentChange = changes.find((c) => c.change_id === selectedChangeId) || changes[0]
  const diffToDisplay = activeTab === 'exemplar' ? (cluster.exemplar_diff || currentChange?.raw_diff || '') : (currentChange?.raw_diff || '')

  const handleCopyDiff = () => {
    if (diffToDisplay) {
      navigator.clipboard.writeText(diffToDisplay)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Safe Unified Diff Line Styler
  const renderDiffLine = (line: string, idx: number) => {
    let lineClass = 'text-slate-400 py-0.5 px-3 font-mono text-[12px] whitespace-pre'

    if (line.startsWith('+++') || line.startsWith('---')) {
      lineClass += ' text-slate-500 font-bold'
    } else if (line.startsWith('+')) {
      lineClass += ' bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-500'
    } else if (line.startsWith('-')) {
      lineClass += ' bg-rose-950/40 text-rose-300 border-l-2 border-rose-500'
    } else if (line.startsWith('@@')) {
      lineClass += ' bg-indigo-950/50 text-indigo-300 font-bold border-l-2 border-indigo-500 my-1'
    }

    return (
      <div key={idx} className={lineClass}>
        {line}
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-slate-950/80">
          <div className="space-y-1.5 pr-4">
            <div className="flex items-center space-x-2.5">
              <span className="px-2 py-0.5 text-xs font-mono font-semibold rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                {cluster.is_noise ? 'Noise Partition' : `Cluster #${cluster.cluster_number}`}
              </span>
              <h2 className="text-base font-bold text-white">
                {explanation ? explanation.pattern_title : cluster.label_name}
              </h2>
            </div>
            <div className="flex items-center space-x-4 text-xs text-slate-400 font-mono">
              <span>{cluster.member_count} constituent changes</span>
              {!cluster.is_noise && (
                <span>~{Math.round(cluster.avg_similarity * 100)}% intra-cluster similarity</span>
              )}
              {cluster.exemplar_file && (
                <span className="truncate max-w-xs text-slate-300">
                  Exemplar: {cluster.exemplar_file}
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Caveat Notice */}
        <div className="px-5 py-2.5 bg-indigo-950/20 border-b border-slate-800 text-[11px] text-slate-400 flex items-center space-x-2">
          <Info className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          <span>
            Candidate recurring pattern grouped via unsupervised clustering. All root causes are explicitly hypotheses and require independent validation.
          </span>
        </div>

        {/* Tab Header */}
        <div className="px-5 pt-3 border-b border-slate-800 flex items-center space-x-6 text-xs bg-slate-950/40">
          <button
            onClick={() => setActiveTab('explanation')}
            className={`pb-2.5 font-medium flex items-center space-x-1.5 transition ${
              activeTab === 'explanation'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Brain className="w-3.5 h-3.5" />
            <span>Grounded AI Explanation</span>
          </button>
          <button
            onClick={() => setActiveTab('exemplar')}
            className={`pb-2.5 font-medium flex items-center space-x-1.5 transition ${
              activeTab === 'exemplar'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Medoid Exemplar Diff</span>
          </button>
          <button
            onClick={() => setActiveTab('members')}
            className={`pb-2.5 font-medium flex items-center space-x-1.5 transition ${
              activeTab === 'members'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>All Cluster Changes ({cluster.member_count})</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {activeTab === 'explanation' && (
            /* Grounded AI Explanation Tab */
            <div className="space-y-4">
              {isLoadingExplanation ? (
                <div className="p-12 text-center space-y-3">
                  <div className="inline-block w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-xs text-slate-400">Synthesizing evidence-grounded explanation...</p>
                </div>
              ) : explanationError ? (
                <div className="p-6 bg-rose-950/20 border border-rose-800 rounded-xl text-xs text-rose-300">
                  {explanationError}
                </div>
              ) : explanation ? (
                <div className="space-y-4">
                  {/* Explanation Mode & Model Badge */}
                  <div className="flex items-center justify-between p-3 bg-slate-950/70 border border-slate-800 rounded-xl text-xs">
                    <div className="flex items-center space-x-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <span className="text-slate-300 font-medium">Synthesis Mode:</span>
                      <span className={`px-2 py-0.5 rounded font-mono text-[11px] font-semibold border ${
                        explanation.explanation_mode === 'llm_generated'
                          ? 'bg-purple-950/80 text-purple-300 border-purple-800'
                          : 'bg-indigo-950/80 text-indigo-300 border-indigo-800'
                      }`}>
                        {explanation.explanation_mode === 'llm_generated' ? 'LLM Grounded Synthesis' : 'Deterministic Rule Engine'}
                      </span>
                      <span className="text-slate-500 font-mono text-[11px]">
                        ({explanation.model_name})
                      </span>
                    </div>
                    <div className="flex items-center space-x-1.5 text-slate-400 text-xs">
                      <span>Confidence:</span>
                      <span className="font-mono font-bold text-slate-200">
                        {Math.round(explanation.confidence_score * 100)}%
                      </span>
                    </div>
                  </div>

                  {/* Plain Language Description */}
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1.5">
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <Info className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Shared Characteristics & Pattern Behavior</span>
                    </h3>
                    <p className="text-sm text-slate-200 leading-relaxed">
                      {explanation.plain_description}
                    </p>
                  </div>

                  {/* Root-Cause Hypothesis */}
                  <div className="p-4 bg-amber-950/20 border border-amber-900/50 rounded-xl space-y-1.5">
                    <h3 className="text-xs font-semibold text-amber-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                      <span>Root-Cause Hypothesis (Unverified)</span>
                    </h3>
                    <p className="text-xs text-amber-200/90 leading-relaxed font-mono">
                      {explanation.root_cause_hypothesis}
                    </p>
                  </div>

                  {/* Suggested Systemic Fix */}
                  <div className="p-4 bg-emerald-950/20 border border-emerald-900/50 rounded-xl space-y-1.5">
                    <h3 className="text-xs font-semibold text-emerald-300 uppercase tracking-wider flex items-center space-x-1.5">
                      <Wrench className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Suggested Systemic Remediation</span>
                    </h3>
                    <p className="text-xs text-emerald-200/90 leading-relaxed">
                      {explanation.suggested_systemic_fix}
                    </p>
                  </div>

                  {/* Limitations & Uncertainty */}
                  <div className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl space-y-1 text-xs text-slate-400">
                    <div className="flex items-center space-x-1.5 font-semibold text-slate-400">
                      <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
                      <span>Limitations & Uncertainty</span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      {explanation.limitations_and_uncertainty}
                    </p>
                  </div>

                  {/* Supporting Grounded Evidence Table */}
                  {explanation.supporting_evidence.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        Supporting Evidence Citations ({explanation.supporting_evidence.length})
                      </h3>
                      <div className="border border-slate-800 rounded-xl overflow-hidden">
                        <table className="w-full text-left text-xs font-mono">
                          <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 text-[11px]">
                            <tr>
                              <th className="py-2 px-3">Commit Hash</th>
                              <th className="py-2 px-3">File Path</th>
                              <th className="py-2 px-3">Lines</th>
                              <th className="py-2 px-3 text-right">Action</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800 bg-slate-900/50">
                            {explanation.supporting_evidence.map((ev, idx) => (
                              <tr key={idx} className="hover:bg-slate-800/40">
                                <td className="py-2 px-3 text-indigo-300 font-semibold">{ev.commit_hash.slice(0, 7)}</td>
                                <td className="py-2 px-3 text-slate-300">{ev.file_path}</td>
                                <td className="py-2 px-3 text-slate-400">{ev.lines_summary}</td>
                                <td className="py-2 px-3 text-right">
                                  <a
                                    href={`https://github.com/${repoOwner}/${repoName}/commit/${ev.commit_hash}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center space-x-1 text-indigo-400 hover:text-indigo-200"
                                  >
                                    <span>GitHub</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {activeTab === 'exemplar' && (
            /* Exemplar Tab */
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-slate-300">Target File:</span>
                  <span className="font-mono text-indigo-300">{cluster.exemplar_file || 'Unknown file'}</span>
                </div>
                <button
                  onClick={handleCopyDiff}
                  className="flex items-center space-x-1 text-slate-400 hover:text-white transition px-2 py-1 rounded bg-slate-800/80"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy Diff'}</span>
                </button>
              </div>

              {/* Diff Container */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-x-auto py-2 shadow-inner">
                {diffToDisplay ? (
                  diffToDisplay.split('\n').map((line, i) => renderDiffLine(line, i))
                ) : (
                  <div className="p-4 text-xs text-slate-500">No diff snippet available.</div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'members' && (
            /* All Members Tab */
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Left Column: Member List Selector */}
              <div className="border border-slate-800 rounded-xl p-3 bg-slate-950/60 max-h-[500px] overflow-y-auto space-y-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block px-1">
                  Cluster Changes
                </span>
                {isLoadingChanges ? (
                  <div className="text-xs text-slate-500 p-2">Loading member changes...</div>
                ) : (
                  changes.map((ch) => {
                    const isSelected = ch.change_id === selectedChangeId
                    return (
                      <div
                        key={ch.change_id}
                        onClick={() => setSelectedChangeId(ch.change_id)}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer transition space-y-1 ${
                          isSelected
                            ? 'bg-indigo-950/60 border-indigo-600 text-indigo-200'
                            : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="font-mono font-medium truncate text-slate-200">
                          {ch.file_path.split('/').pop()}
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-slate-500">
                          <span>{ch.commit_hash.slice(0, 7)}</span>
                          <span className="text-emerald-400">+{ch.added_lines_count} / -{ch.deleted_lines_count}</span>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              {/* Right Column: Selected Member Diff & Commit Details */}
              <div className="md:col-span-2 space-y-3">
                {currentChange && (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs bg-slate-950/80 border border-slate-800 rounded-lg p-3">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <GitCommit className="w-3.5 h-3.5 text-indigo-400" />
                        <span className="font-mono text-slate-300">{currentChange.commit_hash.slice(0, 7)}</span>
                        <span className="text-slate-500">&bull;</span>
                        <span className="font-mono text-slate-400 truncate max-w-xs">{currentChange.file_path}</span>
                      </div>
                      <span className="text-[11px] text-slate-500 block">
                        Timestamp: {new Date(currentChange.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <a
                        href={`https://github.com/${repoOwner}/${repoName}/commit/${currentChange.commit_hash}`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition text-[11px]"
                      >
                        <span>GitHub Commit</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                )}

                {/* Diff Viewer */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-x-auto py-2 max-h-[420px] overflow-y-auto">
                  {currentChange ? (
                    currentChange.raw_diff.split('\n').map((line, i) => renderDiffLine(line, i))
                  ) : (
                    <div className="p-4 text-xs text-slate-500">Select a change from the list.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-500">
          <span>Grounded Diff Evidence &bull; Verified in Repository Mining Pipeline</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
