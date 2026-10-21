import React, { useState } from 'react'
import {
  MessageSquareCode,
  Send,
  Sparkles,
  GitCommit,
  FileCode,
  Boxes,
  ShieldCheck,
  AlertCircle,
  History,
} from 'lucide-react'
import { AnalysisSummary, ClusterDetail, NLQueryResponse, NLQueryCitation } from '../types'

interface RepositoryQueryViewProps {
  analysis: AnalysisSummary
  clusters: ClusterDetail[]
  onSelectCluster?: (cluster: ClusterDetail) => void
}

interface QueryHistoryItem {
  id: string
  timestamp: string
  response: NLQueryResponse
}

const PRESET_QUESTIONS = [
  'Which candidate pattern recurred most frequently?',
  'What files are affected by anti-patterns across this repository?',
  'When was Pattern #1 first introduced and when did it last recur?',
  'How can we prevent or fix Pattern #1?',
  'Give me an overview summary of all patterns detected in this repository.',
]

export const RepositoryQueryView: React.FC<RepositoryQueryViewProps> = ({
  analysis,
  clusters,
  onSelectCluster,
}) => {
  const [queryText, setQueryText] = useState('')
  const [selectedClusterHint, setSelectedClusterHint] = useState<number | ''>('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentResponse, setCurrentResponse] = useState<NLQueryResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [history, setHistory] = useState<QueryHistoryItem[]>([])

  const handleSubmitQuery = async (questionToAsk?: string) => {
    const q = (questionToAsk || queryText).trim()
    if (!q) return

    setIsLoading(true)
    setErrorMsg(null)

    try {
      const payload: { query: string; cluster_id?: number } = { query: q }
      if (selectedClusterHint !== '') {
        payload.cluster_id = Number(selectedClusterHint)
      }

      const res = await fetch(`/api/v1/analyses/${analysis.analysis_id}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        throw new Error(`Query failed with status ${res.status}`)
      }

      const data: NLQueryResponse = await res.json()
      setCurrentResponse(data)
      setHistory((prev) => [
        {
          id: Math.random().toString(36).substring(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          response: data,
        },
        ...prev,
      ])
      if (!questionToAsk) {
        setQueryText('')
      }
    } catch (err: unknown) {
      console.error('Query execution error:', err)
      const message = err instanceof Error ? err.message : 'Failed to query repository.'
      setErrorMsg(message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCitationClick = (citation: NLQueryCitation) => {
    if (citation.type === 'cluster' && onSelectCluster) {
      // Find cluster by label or number
      const match = citation.identifier.match(/\d+/)
      if (match) {
        const clusterNum = parseInt(match[0], 10) - 1
        const target = clusters.find((c) => c.cluster_number === clusterNum)
        if (target) onSelectCluster(target)
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-800/80 text-indigo-400">
                <MessageSquareCode className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-bold text-white">Repository Pattern Intelligence & Q&A</h2>
            </div>
            <p className="text-xs text-slate-400 max-w-2xl">
              Ask natural-language questions grounded strictly in mined Git commits, candidate clusters, and structural code changes. Speculative or out-of-scope queries are explicitly rejected.
            </p>
          </div>

          <div className="flex items-center space-x-3 text-xs">
            <span className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 font-mono">
              Repo: {analysis.owner}/{analysis.repo}
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-emerald-400 font-mono flex items-center space-x-1.5">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Grounded Evidence Mode</span>
            </span>
          </div>
        </div>

        {/* Preset Question Pills */}
        <div className="mt-5 pt-4 border-t border-slate-800/80">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2.5">
            Suggested Research Questions
          </span>
          <div className="flex flex-wrap gap-2">
            {PRESET_QUESTIONS.map((question, i) => (
              <button
                key={i}
                onClick={() => {
                  setQueryText(question)
                  handleSubmitQuery(question)
                }}
                disabled={isLoading}
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-950/80 hover:bg-indigo-950/60 border border-slate-800 hover:border-indigo-800 text-slate-300 hover:text-indigo-200 transition text-left disabled:opacity-50"
              >
                &ldquo;{question}&rdquo;
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSubmitQuery()
          }}
          className="mt-4 flex flex-col sm:flex-row gap-2"
        >
          {/* Optional Cluster Hint Filter */}
          <select
            value={selectedClusterHint}
            onChange={(e) => setSelectedClusterHint(e.target.value === '' ? '' : Number(e.target.value))}
            className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Pattern Clusters</option>
            {clusters
              .filter((c) => !c.is_noise)
              .map((c) => (
                <option key={c.id} value={c.cluster_number}>
                  Pattern #{c.cluster_number + 1}: {c.label_name}
                </option>
              ))}
          </select>

          <div className="flex-1 relative">
            <input
              type="text"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="e.g. Which commits introduced Pattern #1, or what systemic fix is recommended?"
              className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 pr-10"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !queryText.trim()}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center justify-center space-x-2 transition disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Ask Grounded AI</span>
          </button>
        </form>
      </div>

      {/* Error Message */}
      {errorMsg && (
        <div className="p-4 bg-rose-950/20 border border-rose-900 rounded-xl text-xs text-rose-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Current / Latest Response Card */}
      {currentResponse && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-lg animate-fadeIn">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Grounded Answer
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs">
              {/* Query Type Badge */}
              <span className={`px-2 py-0.5 rounded font-mono text-[11px] font-semibold border ${
                currentResponse.query_type === 'deterministic_db'
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800'
                  : currentResponse.query_type === 'grounded_retrieval'
                  ? 'bg-indigo-950/80 text-indigo-300 border-indigo-800'
                  : 'bg-amber-950/80 text-amber-300 border-amber-800'
              }`}>
                {currentResponse.query_type === 'deterministic_db'
                  ? 'Deterministic DB Evidence'
                  : currentResponse.query_type === 'grounded_retrieval'
                  ? 'Grounded LLM Retrieval'
                  : 'Out of Scope / Unsupported'}
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400 font-mono text-[11px]">
                Confidence: {Math.round(currentResponse.confidence * 100)}%
              </span>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-[11px] text-slate-400 block font-mono">Q: &ldquo;{currentResponse.question}&rdquo;</span>
            <p className="text-sm text-slate-100 leading-relaxed pt-1">
              {currentResponse.answer}
            </p>
          </div>

          {/* Citations section */}
          {currentResponse.citations && currentResponse.citations.length > 0 && (
            <div className="pt-3 border-t border-slate-800/80 space-y-2">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                Evidence Citations ({currentResponse.citations.length})
              </span>
              <div className="flex flex-wrap gap-2">
                {currentResponse.citations.map((c, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleCitationClick(c)}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 hover:border-indigo-600 hover:text-indigo-200 transition"
                  >
                    {c.type === 'cluster' && <Boxes className="w-3.5 h-3.5 text-indigo-400" />}
                    {c.type === 'commit' && <GitCommit className="w-3.5 h-3.5 text-indigo-400" />}
                    {c.type === 'file' && <FileCode className="w-3.5 h-3.5 text-emerald-400" />}
                    <span>{c.type === 'commit' ? c.identifier.slice(0, 7) : c.identifier}</span>
                    {c.description && <span className="text-[10px] text-slate-500">({c.description})</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Query History Log */}
      {history.length > 1 && (
        <div className="space-y-3">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
            <History className="w-3.5 h-3.5 text-slate-500" />
            <span>Previous Queries in this Session ({history.length - 1})</span>
          </div>
          <div className="space-y-2">
            {history.slice(1).map((item) => (
              <div
                key={item.id}
                className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between text-slate-400">
                  <span className="font-medium text-slate-200">&ldquo;{item.response.question}&rdquo;</span>
                  <span className="font-mono text-[10px] text-slate-500">{item.timestamp}</span>
                </div>
                <p className="text-slate-300 leading-relaxed text-[12px]">{item.response.answer}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
