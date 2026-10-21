import React, { useState, useEffect } from 'react'
import {
  GitBranch,
  Layers,
  Search,
  Activity,
  Calendar,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Code2,
  Terminal,
  ExternalLink,
  BookOpen
} from 'lucide-react'

interface HealthStatus {
  status: string
  version: string
  environment: string
}

export default function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [maxCommits, setMaxCommits] = useState(50)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'explorer' | 'timeline' | 'query'>('dashboard')
  
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    owner?: string
    repo?: string
    message: string
  } | null>(null)

  // Check backend health on initial load
  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
  }, [])

  const handleValidate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repoUrl.trim()) return

    setIsValidating(true)
    setValidationResult(null)

    try {
      const res = await fetch('/api/v1/validate-repo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl }),
      })
      const data = await res.json()
      setValidationResult(data)
    } catch (err: any) {
      setValidationResult({
        valid: false,
        message: err.message || 'Network error reaching CodeEcho API.',
      })
    } finally {
      setIsValidating(false)
    }
  }

  const handlePresetSelect = (preset: string) => {
    setRepoUrl(preset)
    setValidationResult(null)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-600/20 text-indigo-400 rounded-lg border border-indigo-500/30">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold tracking-tight text-white">CodeEcho</h1>
                <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800 rounded-full">
                  Research MVP v0.1
                </span>
              </div>
              <p className="text-xs text-slate-400">
                AI-Assisted Pattern Recognition for Recurring Anti-Patterns in Git Repositories
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700 text-xs">
              <span className={`w-2 h-2 rounded-full ${health ? 'bg-emerald-400' : 'bg-rose-500 animate-pulse'}`} />
              <span className="text-slate-300">
                {health ? `Backend Connected (${health.version})` : 'Connecting Backend...'}
              </span>
            </div>
            <a
              href="/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-indigo-400 transition"
            >
              <BookOpen className="w-4 h-4" />
              <span>Swagger API</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Repo Ingestion Section */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-100 flex items-center space-x-2">
                <GitBranch className="w-5 h-5 text-indigo-400" />
                <span>Repository Onboarding & Mining</span>
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                Enter a public GitHub repository. CodeEcho extracts commits, parses AST diffs, and computes semantic representations.
              </p>
            </div>

            {/* Quick Demo Presets */}
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-500 font-medium">Demo Presets:</span>
              <button
                type="button"
                onClick={() => handlePresetSelect('https://github.com/pallets/click')}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                pallets/click
              </button>
              <button
                type="button"
                onClick={() => handlePresetSelect('https://github.com/psf/requests')}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              >
                psf/requests
              </button>
            </div>
          </div>

          <form onSubmit={handleValidate} className="space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  placeholder="https://github.com/owner/repository"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                  required
                />
              </div>

              <div className="flex items-center space-x-3 bg-slate-950 border border-slate-700 px-4 py-2 rounded-lg">
                <label className="text-xs text-slate-400 whitespace-nowrap">Commit Limit:</label>
                <input
                  type="range"
                  min="10"
                  max="200"
                  step="10"
                  value={maxCommits}
                  onChange={(e) => setMaxCommits(Number(e.target.value))}
                  className="w-24 accent-indigo-500 cursor-pointer"
                />
                <span className="text-xs font-mono font-medium text-indigo-400 w-8">{maxCommits}</span>
              </div>

              <button
                type="submit"
                disabled={isValidating || !repoUrl.trim()}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium text-sm rounded-lg transition shadow-lg shadow-indigo-600/20 flex items-center justify-center space-x-2"
              >
                {isValidating ? (
                  <>
                    <Activity className="w-4 h-4 animate-spin" />
                    <span>Validating...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Validate & Inspect</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Validation Feedback */}
          {validationResult && (
            <div
              className={`p-4 rounded-lg border text-sm flex items-start space-x-3 ${
                validationResult.valid
                  ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                  : 'bg-rose-950/40 border-rose-800/60 text-rose-300'
              }`}
            >
              {validationResult.valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              )}
              <div className="space-y-1">
                <p className="font-medium">
                  {validationResult.valid
                    ? `Repository Verified: ${validationResult.owner}/${validationResult.repo}`
                    : 'Validation Error'}
                </p>
                <p className="text-xs opacity-90">{validationResult.message}</p>
                {validationResult.valid && (
                  <div className="pt-2 flex items-center space-x-4 text-xs font-mono">
                    <span>Target: {validationResult.owner}/{validationResult.repo}</span>
                    <span>Max Commits: {maxCommits}</span>
                    <span className="text-emerald-400 font-sans">Ready for mining pipeline</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* View Navigation Tabs */}
        <div className="flex border-b border-slate-800 space-x-8 text-sm">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`pb-3 font-medium flex items-center space-x-2 transition ${
              activeTab === 'dashboard'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Analysis Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab('explorer')}
            className={`pb-3 font-medium flex items-center space-x-2 transition ${
              activeTab === 'explorer'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code2 className="w-4 h-4" />
            <span>Pattern Explorer</span>
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`pb-3 font-medium flex items-center space-x-2 transition ${
              activeTab === 'timeline'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calendar className="w-4 h-4" />
            <span>Temporal Evolution</span>
          </button>
          <button
            onClick={() => setActiveTab('query')}
            className={`pb-3 font-medium flex items-center space-x-2 transition ${
              activeTab === 'query'
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <HelpCircle className="w-4 h-4" />
            <span>Repository Q&A</span>
          </button>
        </div>

        {/* Tab View Content */}
        <section className="space-y-6">
          {activeTab === 'dashboard' && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-1">
                <span className="text-xs text-slate-400 font-medium">Commits Mined</span>
                <p className="text-2xl font-bold text-white">0</p>
                <span className="text-xs text-slate-500">Awaiting repository run</span>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-1">
                <span className="text-xs text-slate-400 font-medium">Candidate Anti-Patterns</span>
                <p className="text-2xl font-bold text-indigo-400">0</p>
                <span className="text-xs text-slate-500">Clusters identified</span>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-1">
                <span className="text-xs text-slate-400 font-medium">Files Impacted</span>
                <p className="text-2xl font-bold text-emerald-400">0</p>
                <span className="text-xs text-slate-500">Unique source files</span>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-1">
                <span className="text-xs text-slate-400 font-medium">Representation Engine</span>
                <p className="text-lg font-bold text-slate-200">AST + TF-IDF</p>
                <span className="text-xs text-indigo-400">Baseline Ready</span>
              </div>
            </div>
          )}

          {activeTab === 'explorer' && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center space-y-3">
              <Code2 className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-semibold text-slate-200">No Pattern Clusters Generated Yet</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Validate a repository above and trigger an analysis run to extract code diffs and discover candidate anti-pattern clusters.
              </p>
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center space-y-3">
              <Calendar className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-semibold text-slate-200">Temporal Visualization Standby</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Commit timestamps and recurrence curves will display here once repository mining runs.
              </p>
            </div>
          )}

          {activeTab === 'query' && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-8 text-center space-y-3">
              <Terminal className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-semibold text-slate-200">Grounded Natural Language Query</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Ask questions like &quot;Which pattern recurred most frequently in the last 50 commits?&quot; once patterns are extracted.
              </p>
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CodeEcho Minor Project &bull; B.Tech CSE-AI &bull; Academic Evaluation</span>
          <span>Dual Representation Engine (AST + Embeddings) &bull; Zero Hallucination Grounding</span>
        </div>
      </footer>
    </div>
  )
}
