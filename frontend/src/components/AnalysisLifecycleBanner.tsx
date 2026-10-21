import React from 'react'
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  FolderDown,
  FileCode,
  Sparkles,
  ExternalLink,
} from 'lucide-react'
import { AnalysisSummary } from '../types'

interface AnalysisLifecycleBannerProps {
  analysis: AnalysisSummary
}

const STAGES = [
  { key: 'CLONING', label: 'Shallow Clone', icon: FolderDown },
  { key: 'EXTRACTING', label: 'AST & Diff Mining', icon: FileCode },
  { key: 'CLUSTERING', label: 'Pattern Clustering', icon: Sparkles },
]

export const AnalysisLifecycleBanner: React.FC<AnalysisLifecycleBannerProps> = ({ analysis }) => {
  const getStageIndex = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 0
      case 'CLONING':
        return 0
      case 'EXTRACTING':
        return 1
      case 'CLUSTERING':
        return 2
      case 'COMPLETED':
        return 3
      default:
        return -1
    }
  }

  const currentIndex = getStageIndex(analysis.status)
  const isFailed = analysis.status === 'FAILED'
  const isCompleted = analysis.status === 'COMPLETED'
  const isRunning = !isFailed && !isCompleted

  return (
    <div
      className={`border rounded-xl p-5 shadow-lg transition ${
        isFailed
          ? 'bg-rose-950/30 border-rose-800/60'
          : isCompleted
          ? 'bg-slate-900/80 border-slate-800'
          : 'bg-indigo-950/20 border-indigo-800/50'
      }`}
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Target Repo and Status Pill */}
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <span>{analysis.owner}/{analysis.repo}</span>
              <a
                href={analysis.repo_url}
                target="_blank"
                rel="noreferrer"
                className="text-slate-400 hover:text-indigo-400 transition"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </h3>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                isCompleted
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : isFailed
                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                  : 'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse'
              }`}
            >
              {analysis.status}
            </span>
          </div>
          <div className="flex items-center space-x-4 text-xs text-slate-400 font-mono">
            <span>ID: {analysis.analysis_id.slice(0, 8)}</span>
            <span>Limit: {analysis.commit_limit} commits</span>
            <span>Algorithm: {analysis.clustering_algorithm.toUpperCase()}</span>
            {analysis.execution_time_seconds > 0 && (
              <span className="flex items-center space-x-1 text-slate-300">
                <Clock className="w-3 h-3" />
                <span>{analysis.execution_time_seconds}s</span>
              </span>
            )}
          </div>
        </div>

        {/* Right: Stepper Stages */}
        {!isFailed && (
          <div className="flex items-center space-x-2 sm:space-x-4 text-xs">
            {STAGES.map((stage, idx) => {
              const Icon = stage.icon
              const isDone = isCompleted || currentIndex > idx
              const isActive = isRunning && currentIndex === idx

              return (
                <div key={stage.key} className="flex items-center space-x-2">
                  <div
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border transition ${
                      isDone
                        ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-300'
                        : isActive
                        ? 'bg-indigo-950/80 border-indigo-600 text-indigo-200 animate-pulse'
                        : 'bg-slate-900/40 border-slate-800 text-slate-500'
                    }`}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Icon className="w-3.5 h-3.5" />
                    )}
                    <span className="font-medium">{stage.label}</span>
                  </div>
                  {idx < STAGES.length - 1 && (
                    <span className={`w-3 h-0.5 ${currentIndex > idx ? 'bg-emerald-500' : 'bg-slate-800'}`} />
                  )}
                </div>
              )
            })}
          </div>
        )}

        {isFailed && (
          <div className="flex items-center space-x-2 text-rose-300 text-xs">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{analysis.error_message || 'The analysis encountered an error during execution.'}</span>
          </div>
        )}
      </div>
    </div>
  )
}
