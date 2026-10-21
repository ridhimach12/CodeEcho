import React from 'react'
import {
  GitCommit,
  FileCode2,
  Boxes,
  HelpCircle,
  Clock,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react'
import { AnalysisSummary, ClusterDetail } from '../types'

interface DashboardViewProps {
  analysis: AnalysisSummary
  clusters: ClusterDetail[]
  onSelectCluster: (cluster: ClusterDetail) => void
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  analysis,
  clusters,
  onSelectCluster,
}) => {
  const nonNoiseClusters = clusters.filter((c) => !c.is_noise)
  const allAffectedFiles = new Set<string>()
  clusters.forEach((c) => c.affected_files.forEach((f) => allAffectedFiles.add(f)))

  const maxClusterSize = Math.max(...nonNoiseClusters.map((c) => c.member_count), 1)

  return (
    <div className="space-y-6">
      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Commits Mined</span>
            <GitCommit className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <p className="text-xl font-bold text-white">{analysis.commits_mined}</p>
          <span className="text-[11px] text-slate-500">Depth limit: {analysis.commit_limit}</span>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Changes Mined</span>
            <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <p className="text-xl font-bold text-white">{analysis.changes_extracted}</p>
          <span className="text-[11px] text-slate-500">Python diff hunks</span>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Candidate Patterns</span>
            <Boxes className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <p className="text-xl font-bold text-indigo-400">{analysis.clusters_discovered}</p>
          <span className="text-[11px] text-slate-500">Recurring groups</span>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Noise Points</span>
            <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <p className="text-xl font-bold text-amber-400">{analysis.noise_points}</p>
          <span className="text-[11px] text-slate-500">Unclustered changes</span>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Files Impacted</span>
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <p className="text-xl font-bold text-emerald-400">{allAffectedFiles.size}</p>
          <span className="text-[11px] text-slate-500">Unique source files</span>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Analysis Runtime</span>
            <Clock className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <p className="text-xl font-bold text-purple-400">{analysis.execution_time_seconds}s</p>
          <span className="text-[11px] text-slate-500">Shallow clone to DB</span>
        </div>
      </div>

      {/* Academic Disclaimer Box */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex items-start space-x-3 text-xs text-slate-400">
        <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-300">Candidate Pattern Notice: </span>
          The clusters identified below represent algorithmically discovered recurring modifications derived from combined structural AST deltas and TF-IDF semantic embeddings. They are candidate archetypes, not verified software bugs.
        </div>
      </div>

      {/* Cluster Distribution & Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Size Distribution Bar Visualizer */}
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
              <Boxes className="w-4 h-4 text-indigo-400" />
              <span>Pattern Cluster Distribution</span>
            </h3>
            <span className="text-xs text-slate-500">{nonNoiseClusters.length} candidate archetypes</span>
          </div>

          {nonNoiseClusters.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">
              No multi-instance recurring clusters formed with the current density threshold.
            </div>
          ) : (
            <div className="space-y-3">
              {nonNoiseClusters.map((cluster) => {
                const percentage = Math.round((cluster.member_count / maxClusterSize) * 100)
                return (
                  <div
                    key={cluster.id}
                    onClick={() => onSelectCluster(cluster)}
                    className="p-2.5 rounded-lg bg-slate-950/60 hover:bg-slate-800/60 border border-slate-800/60 cursor-pointer transition space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-200 truncate max-w-[70%]">
                        {cluster.label_name}
                      </span>
                      <div className="flex items-center space-x-2">
                        <span className="text-slate-400 font-mono">
                          {cluster.member_count} {cluster.member_count === 1 ? 'change' : 'changes'}
                        </span>
                        <span className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                          {Math.round(cluster.avg_similarity * 100)}% sim
                        </span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right: Key Detected Anti-Pattern Shifts */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Dominant Structural Shifts</span>
            </h3>
          </div>

          <p className="text-xs text-slate-400">
            Most frequent structural mutations across recurring changes:
          </p>

          <div className="space-y-2">
            {Array.from(
              new Set(nonNoiseClusters.flatMap((c) => c.dominant_shifts))
            ).slice(0, 8).map((shift) => (
              <div
                key={shift}
                className="px-3 py-2 bg-slate-950/70 border border-slate-800/80 rounded-lg text-xs font-mono text-slate-300 flex items-center justify-between"
              >
                <span>{shift}</span>
                <span className="w-2 h-2 rounded-full bg-indigo-400" />
              </div>
            ))}
            {nonNoiseClusters.length === 0 && (
              <span className="text-xs text-slate-500">None detected</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
