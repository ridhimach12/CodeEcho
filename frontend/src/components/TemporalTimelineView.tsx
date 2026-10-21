import React, { useState, useEffect } from 'react'
import { Calendar, GitCommit, Info, Filter } from 'lucide-react'
import { AnalysisSummary, ClusterDetail, CodeChangeDetail } from '../types'

interface TemporalTimelineViewProps {
  analysis: AnalysisSummary
  clusters: ClusterDetail[]
  onSelectCluster: (cluster: ClusterDetail) => void
}

interface TimelinePoint {
  change_id: string
  commit_hash: string
  file_path: string
  timestamp: Date
  cluster_number: number
  cluster_name: string
  cluster_ref: ClusterDetail
}

export const TemporalTimelineView: React.FC<TemporalTimelineViewProps> = ({
  analysis,
  clusters,
  onSelectCluster,
}) => {
  const [timelinePoints, setTimelinePoints] = useState<TimelinePoint[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hoveredPoint, setHoveredPoint] = useState<TimelinePoint | null>(null)

  const nonNoiseClusters = clusters.filter((c) => !c.is_noise)

  useEffect(() => {
    let isMounted = true
    setIsLoading(true)

    // Fetch changes for non-noise clusters to construct chronological timeline
    const fetchPromises = nonNoiseClusters.map((c) =>
      fetch(`/api/v1/analyses/${analysis.analysis_id}/clusters/${c.id}/changes`)
        .then((res) => res.json())
        .then((changes: CodeChangeDetail[]) =>
          changes.map((ch) => ({
            change_id: ch.change_id,
            commit_hash: ch.commit_hash,
            file_path: ch.file_path,
            timestamp: new Date(ch.timestamp),
            cluster_number: c.cluster_number,
            cluster_name: c.label_name,
            cluster_ref: c,
          }))
        )
        .catch(() => [])
    )

    Promise.all(fetchPromises)
      .then((results) => {
        if (!isMounted) return
        const flat = results.flat().sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime())
        setTimelinePoints(flat)
      })
      .finally(() => {
        if (isMounted) setIsLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [analysis.analysis_id, clusters.length])

  // Calculate timeline bounds
  const timestamps = timelinePoints.map((p) => p.timestamp.getTime())
  const minTime = timestamps.length > 0 ? Math.min(...timestamps) : Date.now() - 86400000
  const maxTime = timestamps.length > 0 ? Math.max(...timestamps) : Date.now()
  const timeSpan = Math.max(maxTime - minTime, 3600000) // at least 1 hour

  // Y-axis cluster positions
  const clusterTracks = nonNoiseClusters.map((c, i) => ({
    cluster: c,
    yPos: 50 + i * 45,
  }))

  const svgHeight = Math.max(200, 70 + nonNoiseClusters.length * 45)
  const svgWidth = 800

  return (
    <div className="space-y-6">
      {/* Informational Header */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-indigo-400" />
            <span>Temporal Evolution & Recurrence Timeline</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">
            {timelinePoints.length} observed change events
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Plots when each candidate pattern appeared over chronological Git commit history. Helps identify whether a pattern is chronic (recurring persistently) or isolated to a specific development burst.
        </p>
      </div>

      {/* Scientific Grounding Note */}
      <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-3.5 flex items-start space-x-2.5 text-xs text-slate-400">
        <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <span>
          <strong className="text-slate-300">Grounding Statement: </strong>
          Timestamps represent exact Git author/commit dates. Plotting displays observed chronology across repository history; causal transmission across developers or files is an inferred hypothesis.
        </span>
      </div>

      {/* Interactive Timeline Chart */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
        {isLoading ? (
          <div className="py-20 text-center text-xs text-slate-500">
            Extracting commit timestamps and assembling timeline...
          </div>
        ) : timelinePoints.length === 0 ? (
          <div className="py-16 text-center text-xs text-slate-500 space-y-2">
            <Filter className="w-6 h-6 text-slate-600 mx-auto" />
            <p>No multi-instance pattern clusters found to plot on timeline.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[750px]">
              <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto select-none">
                {/* Horizontal grid lines for each cluster track */}
                {clusterTracks.map(({ cluster, yPos }) => (
                  <g key={cluster.id} className="group cursor-pointer" onClick={() => onSelectCluster(cluster)}>
                    <line
                      x1="180"
                      y1={yPos}
                      x2={svgWidth - 30}
                      y2={yPos}
                      stroke="#1e293b"
                      strokeWidth="1.5"
                      strokeDasharray="4 4"
                    />
                    {/* Cluster Track Label */}
                    <text
                      x="170"
                      y={yPos + 4}
                      textAnchor="end"
                      fill="#94a3b8"
                      fontSize="10"
                      fontFamily="monospace"
                      className="hover:fill-indigo-400 transition"
                    >
                      Pattern #{cluster.cluster_number + 1} ({cluster.member_count})
                    </text>
                  </g>
                ))}

                {/* Vertical Start / End Time Guides */}
                <line x1="180" y1="25" x2="180" y2={svgHeight - 25} stroke="#334155" strokeWidth="1" />
                <line x1={svgWidth - 30} y1="25" x2={svgWidth - 30} y2={svgHeight - 25} stroke="#334155" strokeWidth="1" />

                {/* Time Axis Labels */}
                <text x="180" y="20" textAnchor="start" fill="#64748b" fontSize="9" fontFamily="monospace">
                  {new Date(minTime).toLocaleDateString()}
                </text>
                <text x={svgWidth - 30} y="20" textAnchor="end" fill="#64748b" fontSize="9" fontFamily="monospace">
                  {new Date(maxTime).toLocaleDateString()}
                </text>

                {/* Chronological Event Dots */}
                {timelinePoints.map((pt) => {
                  const xNorm = (pt.timestamp.getTime() - minTime) / timeSpan
                  const xPos = 180 + xNorm * (svgWidth - 210)
                  const track = clusterTracks.find((t) => t.cluster.cluster_number === pt.cluster_number)
                  const yPos = track ? track.yPos : 50
                  const isHovered = hoveredPoint?.change_id === pt.change_id

                  return (
                    <circle
                      key={pt.change_id}
                      cx={xPos}
                      cy={yPos}
                      r={isHovered ? 6 : 4}
                      fill={isHovered ? '#818cf8' : '#6366f1'}
                      stroke="#0f172a"
                      strokeWidth="1.5"
                      className="cursor-pointer transition-all duration-200"
                      onMouseEnter={() => setHoveredPoint(pt)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      onClick={() => onSelectCluster(pt.cluster_ref)}
                    />
                  )
                })}
              </svg>
            </div>

            {/* Hover Tooltip Card */}
            {hoveredPoint && (
              <div className="mt-3 p-3 bg-slate-950 border border-slate-700 rounded-lg text-xs flex items-center justify-between text-slate-300">
                <div className="flex items-center space-x-3">
                  <GitCommit className="w-4 h-4 text-indigo-400" />
                  <span className="font-mono text-indigo-300">{hoveredPoint.commit_hash.slice(0, 7)}</span>
                  <span>&bull;</span>
                  <span className="font-mono text-slate-200">{hoveredPoint.file_path}</span>
                  <span>&bull;</span>
                  <span className="text-slate-400">{hoveredPoint.timestamp.toLocaleString()}</span>
                </div>
                <span className="text-indigo-400 font-medium">Click to inspect cluster</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
