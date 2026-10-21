import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Activity,
  Boxes,
  Calendar,
  FileSearch,
  MessageSquareCode,
} from 'lucide-react'
import { HealthStatus, AnalysisSummary, ClusterDetail } from './types'
import { apiFetch } from './api/client'
import { Navbar } from './components/Navbar'
import { RepoIngestionForm } from './components/RepoIngestionForm'
import { AnalysisLifecycleBanner } from './components/AnalysisLifecycleBanner'
import { DashboardView } from './components/DashboardView'
import { PatternExplorerView } from './components/PatternExplorerView'
import { TemporalTimelineView } from './components/TemporalTimelineView'
import { RepositoryQueryView } from './components/RepositoryQueryView'
import { PatternDetailModal } from './components/PatternDetailModal'

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([])
  const [currentAnalysisId, setCurrentAnalysisId] = useState<string | null>(null)
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisSummary | null>(null)
  const [clusters, setClusters] = useState<ClusterDetail[]>([])
  const [selectedCluster, setSelectedCluster] = useState<ClusterDetail | null>(null)

  const [activeTab, setActiveTab] = useState<'dashboard' | 'explorer' | 'timeline' | 'qa'>('dashboard')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const pollingRef = useRef<number | null>(null)

  // 1. Initial Health and Analyses List Fetch
  const fetchAnalysesList = useCallback(() => {
    apiFetch('/api/v1/analyses')
      .then((res) => res.json())
      .then((data: AnalysisSummary[]) => {
        setAnalyses(data)
        if (data.length > 0 && !currentAnalysisId) {
          // Select most recent analysis by default
          setCurrentAnalysisId(data[0].analysis_id)
        }
      })
      .catch((err) => console.error('Failed to load past analyses:', err))
  }, [currentAnalysisId])

  useEffect(() => {
    apiFetch('/api/v1/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))

    fetchAnalysesList()
  }, [fetchAnalysesList])

  // 2. Fetch Clusters for Active Analysis
  const fetchClusters = useCallback((analysisId: string) => {
    apiFetch(`/api/v1/analyses/${analysisId}/clusters`)
      .then((res) => res.json())
      .then((data: ClusterDetail[]) => setClusters(data))
      .catch((err) => console.error('Failed to fetch clusters:', err))
  }, [])

  // 3. Polling Active Analysis Status
  useEffect(() => {
    if (!currentAnalysisId) return

    const pollStatus = () => {
      apiFetch(`/api/v1/analyses/${currentAnalysisId}`)
        .then((res) => res.json())
        .then((data: AnalysisSummary) => {
          setCurrentAnalysis(data)

          const terminalStates = ['COMPLETED', 'FAILED']
          if (terminalStates.includes(data.status)) {
            if (pollingRef.current) {
              clearInterval(pollingRef.current)
              pollingRef.current = null
            }
            if (data.status === 'COMPLETED') {
              fetchClusters(data.analysis_id)
              fetchAnalysesList()
            }
          }
        })
        .catch((err) => {
          console.error('Polling error:', err)
          if (pollingRef.current) {
            clearInterval(pollingRef.current)
            pollingRef.current = null
          }
        })
    }

    // Initial fetch
    pollStatus()

    // Start interval
    pollingRef.current = window.setInterval(pollStatus, 1500)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [currentAnalysisId, fetchClusters, fetchAnalysesList])

  // 4. Handle Starting New Analysis
  const handleStartAnalysis = async (repoUrl: string, commitLimit: number, algorithm: string) => {
    setIsSubmitting(true)
    try {
      const res = await apiFetch('/api/v1/analyses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl,
          commit_limit: commitLimit,
          clustering_algorithm: algorithm,
        }),
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Failed to schedule repository analysis.')
      }

      const data = await res.json()
      setClusters([])
      setCurrentAnalysisId(data.analysis_id)
      setActiveTab('dashboard')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSelectAnalysis = (analysisId: string) => {
    setCurrentAnalysisId(analysisId)
    setClusters([])
    setSelectedCluster(null)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        health={health}
        analyses={analyses}
        currentAnalysisId={currentAnalysisId}
        onSelectAnalysis={handleSelectAnalysis}
        onRefreshList={fetchAnalysesList}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Repo Ingestion Bar */}
        <RepoIngestionForm
          isSubmitting={isSubmitting}
          onStartAnalysis={handleStartAnalysis}
        />

        {/* Active Analysis Lifecycle Banner */}
        {currentAnalysis && (
          <AnalysisLifecycleBanner analysis={currentAnalysis} />
        )}

        {/* View Navigation Tabs */}
        {currentAnalysis && (
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
              <span>Dashboard & Metrics</span>
            </button>
            <button
              onClick={() => setActiveTab('explorer')}
              className={`pb-3 font-medium flex items-center space-x-2 transition ${
                activeTab === 'explorer'
                  ? 'border-b-2 border-indigo-500 text-indigo-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Boxes className="w-4 h-4" />
              <span>Pattern Explorer ({currentAnalysis.clusters_discovered})</span>
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
              <span>Temporal Recurrence</span>
            </button>
            <button
              onClick={() => setActiveTab('qa')}
              className={`pb-3 font-medium flex items-center space-x-2 transition ${
                activeTab === 'qa'
                  ? 'border-b-2 border-indigo-500 text-indigo-400'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MessageSquareCode className="w-4 h-4" />
              <span>Repository Q&amp;A</span>
            </button>
          </div>
        )}

        {/* Content Views */}
        {currentAnalysis ? (
          <div className="space-y-6">
            {activeTab === 'dashboard' && (
              <DashboardView
                analysis={currentAnalysis}
                clusters={clusters}
                onSelectCluster={(c) => setSelectedCluster(c)}
              />
            )}

            {activeTab === 'explorer' && (
              <PatternExplorerView
                clusters={clusters}
                onSelectCluster={(c) => setSelectedCluster(c)}
              />
            )}

            {activeTab === 'timeline' && (
              <TemporalTimelineView
                analysis={currentAnalysis}
                clusters={clusters}
                onSelectCluster={(c) => setSelectedCluster(c)}
              />
            )}

            {activeTab === 'qa' && (
              <RepositoryQueryView
                analysis={currentAnalysis}
                clusters={clusters}
                onSelectCluster={(c) => setSelectedCluster(c)}
              />
            )}
          </div>
        ) : (
          /* Empty Standby State */
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-16 text-center space-y-4">
            <FileSearch className="w-12 h-12 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <h3 className="text-base font-semibold text-slate-200">No Repository Analyzed Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Submit a repository URL above or pick a verified preset to start mining commit history, extracting AST diffs, and discovering candidate recurring patterns.
              </p>
            </div>
          </div>
        )}
      </main>

      {/* Pattern Detail Modal */}
      {selectedCluster && currentAnalysis && (
        <PatternDetailModal
          cluster={selectedCluster}
          analysisId={currentAnalysis.analysis_id}
          repoOwner={currentAnalysis.owner}
          repoName={currentAnalysis.repo}
          onClose={() => setSelectedCluster(null)}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>CodeEcho Capstone &bull; B.Tech CSE-AI Academic Research</span>
          <span>Dual Representation Engine (AST + TF-IDF) &bull; DBSCAN & HDBSCAN Clustering</span>
        </div>
      </footer>
    </div>
  )
}
