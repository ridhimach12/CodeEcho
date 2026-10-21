import React, { useState, useMemo } from 'react'
import { Search, Filter, ArrowUpDown, ChevronRight, FileText } from 'lucide-react'
import { ClusterDetail } from '../types'

interface PatternExplorerViewProps {
  clusters: ClusterDetail[]
  onSelectCluster: (cluster: ClusterDetail) => void
}

export const PatternExplorerView: React.FC<PatternExplorerViewProps> = ({
  clusters,
  onSelectCluster,
}) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [showNoise, setShowNoise] = useState(false)
  const [sortBy, setSortBy] = useState<'size' | 'similarity' | 'number'>('size')

  const filteredClusters = useMemo(() => {
    return clusters
      .filter((c) => {
        if (!showNoise && c.is_noise) return false
        if (!searchQuery.trim()) return true
        const query = searchQuery.toLowerCase()
        const matchName = c.label_name.toLowerCase().includes(query)
        const matchFiles = c.affected_files.some((f) => f.toLowerCase().includes(query))
        const matchShifts = c.dominant_shifts.some((s) => s.toLowerCase().includes(query))
        return matchName || matchFiles || matchShifts
      })
      .sort((a, b) => {
        if (sortBy === 'size') return b.member_count - a.member_count
        if (sortBy === 'similarity') return b.avg_similarity - a.avg_similarity
        return a.cluster_number - b.cluster_number
      })
  }, [clusters, showNoise, searchQuery, sortBy])

  return (
    <div className="space-y-6">
      {/* Controls Bar: Search, Sort, Noise Toggle */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        {/* Search Input */}
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by pattern shift (e.g. none_guard), file, or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition"
          />
        </div>

        <div className="flex items-center space-x-3 w-full md:w-auto justify-between md:justify-end">
          {/* Noise Toggle */}
          <label className="flex items-center space-x-2 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showNoise}
              onChange={(e) => setShowNoise(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0 cursor-pointer"
            />
            <span>Include Noise ({clusters.filter((c) => c.is_noise).reduce((acc, c) => acc + c.member_count, 0)})</span>
          </label>

          {/* Sort Selector */}
          <div className="flex items-center space-x-1.5 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300">
            <ArrowUpDown className="w-3 h-3 text-slate-500" />
            <select
              aria-label="Sort by"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-transparent focus:outline-none cursor-pointer"
            >
              <option value="size" className="bg-slate-900">Sort by Size</option>
              <option value="similarity" className="bg-slate-900">Sort by Similarity</option>
              <option value="number" className="bg-slate-900">Sort by Number</option>
            </select>
          </div>
        </div>
      </div>

      {/* Clusters List */}
      {filteredClusters.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center space-y-3">
          <Filter className="w-8 h-8 text-slate-600 mx-auto" />
          <h4 className="text-sm font-semibold text-slate-300">No matching clusters found</h4>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search keywords or toggle &quot;Include Noise&quot; to inspect unclustered changes.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredClusters.map((cluster) => {
            return (
              <div
                key={cluster.id}
                onClick={() => onSelectCluster(cluster)}
                className={`group border rounded-xl p-5 cursor-pointer transition hover:border-indigo-500/60 shadow-md space-y-3.5 flex flex-col justify-between ${
                  cluster.is_noise
                    ? 'bg-amber-950/10 border-amber-900/40 hover:bg-amber-950/20'
                    : 'bg-slate-900/60 border-slate-800 hover:bg-slate-900/90'
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span
                      className={`text-sm font-semibold group-hover:text-indigo-400 transition leading-snug ${
                        cluster.is_noise ? 'text-amber-300' : 'text-slate-200'
                      }`}
                    >
                      {cluster.label_name}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono shrink-0 font-medium ${
                        cluster.is_noise
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-indigo-950 text-indigo-300 border border-indigo-800'
                      }`}
                    >
                      {cluster.member_count} {cluster.member_count === 1 ? 'change' : 'changes'}
                    </span>
                  </div>

                  {/* AST Shift Tags */}
                  {cluster.dominant_shifts.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {cluster.dominant_shifts.map((shift) => (
                        <span
                          key={shift}
                          className="px-2 py-0.5 rounded-md bg-slate-950/80 border border-slate-800 text-[10px] font-mono text-slate-300"
                        >
                          {shift}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Affected Files List */}
                  <div className="text-xs text-slate-400 space-y-1 pt-1">
                    <div className="flex items-center space-x-1.5 text-slate-500 text-[11px]">
                      <FileText className="w-3 h-3" />
                      <span>{cluster.affected_files.length} impacted files:</span>
                    </div>
                    <p className="font-mono text-[11px] text-slate-300 truncate">
                      {cluster.affected_files.slice(0, 3).join(', ')}
                      {cluster.affected_files.length > 3 && ` +${cluster.affected_files.length - 3} more`}
                    </p>
                  </div>
                </div>

                {/* Footer of Card */}
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    {!cluster.is_noise && (
                      <span className="text-[11px] text-emerald-400 font-mono">
                        ~{Math.round(cluster.avg_similarity * 100)}% similarity
                      </span>
                    )}
                    {cluster.exemplar_file && (
                      <span className="text-[11px] text-slate-500 font-mono truncate max-w-[140px]">
                        Exemplar: {cluster.exemplar_file.split('/').pop()}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-1 text-indigo-400 group-hover:translate-x-0.5 transition font-medium">
                    <span>Inspect</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
