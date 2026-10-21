import React, { useState } from 'react'
import { GitBranch, Search, Play, Settings2, AlertCircle } from 'lucide-react'

interface RepoIngestionFormProps {
  isSubmitting: boolean
  onStartAnalysis: (repoUrl: string, commitLimit: number, algorithm: string) => Promise<void>
}

export const RepoIngestionForm: React.FC<RepoIngestionFormProps> = ({
  isSubmitting,
  onStartAnalysis,
}) => {
  const [repoUrl, setRepoUrl] = useState('')
  const [commitLimit, setCommitLimit] = useState(50)
  const [algorithm, setAlgorithm] = useState<'dbscan' | 'hdbscan'>('dbscan')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!repoUrl.trim()) {
      setErrorMsg('Please enter a GitHub repository URL.')
      return
    }
    setErrorMsg(null)
    try {
      await onStartAnalysis(repoUrl.trim(), commitLimit, algorithm)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to initiate repository analysis.')
    }
  }

  const handlePreset = (url: string) => {
    setRepoUrl(url)
    setErrorMsg(null)
  }

  return (
    <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
            <GitBranch className="w-5 h-5 text-indigo-400" />
            <span>Repository Ingestion & Mining Pipeline</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Submit a public GitHub repository. CodeEcho mines commit history, parses AST diffs, and groups candidate recurring anti-patterns.
          </p>
        </div>

        {/* Presets */}
        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-500 font-medium">Verified Presets:</span>
          <button
            type="button"
            onClick={() => handlePreset('https://github.com/pallets/click')}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            pallets/click
          </button>
          <button
            type="button"
            onClick={() => handlePreset('https://github.com/psf/requests')}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            psf/requests
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex flex-col lg:flex-row gap-3">
          {/* URL Input */}
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

          {/* Commit Limit Slider */}
          <div className="flex items-center space-x-3 bg-slate-950 border border-slate-700 px-3.5 py-2 rounded-lg">
            <label className="text-xs text-slate-400 whitespace-nowrap">Commit Limit:</label>
            <input
              type="range"
              min="10"
              max="200"
              step="10"
              value={commitLimit}
              onChange={(e) => setCommitLimit(Number(e.target.value))}
              className="w-24 accent-indigo-500 cursor-pointer"
            />
            <span className="text-xs font-mono font-medium text-indigo-400 w-8">{commitLimit}</span>
          </div>

          {/* Algorithm Toggle */}
          <div className="flex items-center space-x-2 bg-slate-950 border border-slate-700 px-3 py-2 rounded-lg">
            <Settings2 className="w-3.5 h-3.5 text-slate-400" />
            <select
              aria-label="Clustering Algorithm"
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value as 'dbscan' | 'hdbscan')}
              className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="dbscan" className="bg-slate-900">DBSCAN (Cosine)</option>
              <option value="hdbscan" className="bg-slate-900">HDBSCAN (Density)</option>
            </select>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || !repoUrl.trim()}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium text-sm rounded-lg transition shadow-lg shadow-indigo-600/20 flex items-center justify-center space-x-2 shrink-0"
          >
            <Play className={`w-4 h-4 ${isSubmitting ? 'animate-pulse' : ''}`} />
            <span>{isSubmitting ? 'Queueing Analysis...' : 'Start Mining & Clustering'}</span>
          </button>
        </div>
      </form>

      {errorMsg && (
        <div className="p-3.5 bg-rose-950/40 border border-rose-800/60 rounded-lg text-xs text-rose-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
    </section>
  )
}
