import React from 'react'
import { Layers, BookOpen, ExternalLink, RefreshCw, GitBranch } from 'lucide-react'
import { HealthStatus, AnalysisSummary } from '../types'

interface NavbarProps {
  health: HealthStatus | null
  analyses: AnalysisSummary[]
  currentAnalysisId: string | null
  onSelectAnalysis: (id: string) => void
  onRefreshList: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  analyses,
  currentAnalysisId,
  onSelectAnalysis,
  onRefreshList,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-bold tracking-tight text-white">CodeEcho</span>
              <span className="px-2 py-0.5 text-[11px] font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800 rounded-full">
                Research Prototype
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Pattern Recognition for Recurring Anti-Patterns in Git Repositories
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto justify-end flex-wrap gap-2">
          {/* Recent Analyses Selector */}
          {analyses.length > 0 && (
            <div className="flex items-center space-x-1.5 bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
              <GitBranch className="w-3.5 h-3.5 text-slate-400" />
              <select
                aria-label="Recent Analyses"
                value={currentAnalysisId || ''}
                onChange={(e) => onSelectAnalysis(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none cursor-pointer max-w-[200px] truncate"
              >
                <option value="" disabled className="bg-slate-900 text-slate-400">
                  Select Past Analysis
                </option>
                {analyses.map((a) => (
                  <option key={a.analysis_id} value={a.analysis_id} className="bg-slate-900 text-slate-100">
                    {a.owner}/{a.repo} ({a.status})
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={onRefreshList}
                title="Refresh recent analyses list"
                className="text-slate-500 hover:text-slate-300 transition"
              >
                <RefreshCw className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Backend Health Badge */}
          <div className="flex items-center space-x-2 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                health?.status === 'healthy' ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-rose-500 animate-pulse'
              }`}
            />
            <span className="text-slate-300 font-mono">
              {health?.status === 'healthy' ? `v${health.version}` : 'Connecting...'}
            </span>
          </div>

          {/* Swagger Link */}
          <a
            href="/api/v1/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-indigo-400 transition px-2 py-1"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </header>
  )
}
