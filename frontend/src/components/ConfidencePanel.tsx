import { useQuery } from '@tanstack/react-query'
import { Shield, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { api } from '../services/api'
import type { ConfidenceScore } from '../services/types'
import clsx from 'clsx'

const LABEL_COLORS = {
  High:     { ring: 'stroke-success',  bg: 'bg-success',     text: 'text-success',     badge: 'bg-success/15 text-success border-success/30' },
  Medium:   { ring: 'stroke-warning',  bg: 'bg-warning',     text: 'text-warning',     badge: 'bg-warning/15 text-warning border-warning/30' },
  Low:      { ring: 'stroke-danger',   bg: 'bg-danger',      text: 'text-danger',       badge: 'bg-danger/15 text-danger border-danger/30' },
  Critical: { ring: 'stroke-red-600',  bg: 'bg-red-600',     text: 'text-red-500',      badge: 'bg-red-600/15 text-red-400 border-red-500/30' },
}

export default function ConfidencePanel({ investigationId }: { investigationId: string }) {
  const [showDimensions, setShowDimensions] = useState(false)
  const { data, isLoading } = useQuery<ConfidenceScore>({
    queryKey: ['confidence', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/confidence`).then(r => r.data),
    refetchInterval: 10000,
  })

  if (isLoading || !data) return null

  const colors = LABEL_COLORS[data.label as keyof typeof LABEL_COLORS] || LABEL_COLORS.Medium
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const filled = (data.overall / 100) * circumference

  return (
    <div className="bg-panel border border-border rounded-xl p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Shield size={14} className={colors.text} />
        <span className="text-xs font-semibold text-white">Reconstruction Confidence</span>
        <span className={clsx('ml-auto text-[10px] px-2 py-0.5 rounded-full border font-medium', colors.badge)}>
          {data.label}
        </span>
      </div>

      {/* Score ring + summary */}
      <div className="flex items-center gap-4">
        {/* SVG ring */}
        <div className="relative flex-shrink-0 w-20 h-20">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 88 88">
            <circle cx="44" cy="44" r={radius} fill="none" stroke="#21262d" strokeWidth="8" />
            <circle
              cx="44" cy="44" r={radius}
              fill="none"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${filled} ${circumference}`}
              className={clsx('transition-all duration-700', colors.ring)}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={clsx('text-xl font-bold', colors.text)}>{Math.round(data.overall)}</span>
            <span className="text-[9px] text-muted">/ 100</span>
          </div>
        </div>

        {/* Summary + gaps */}
        <div className="flex-1 min-w-0 space-y-2">
          <p className="text-xs text-white/80 leading-relaxed">{data.summary}</p>
          {data.gaps.length > 0 && (
            <div className="flex items-start gap-1.5 bg-warning/8 border border-warning/20 rounded-md px-2.5 py-2">
              <AlertTriangle size={11} className="text-warning mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-warning font-medium">{data.gaps.length} evidence gap{data.gaps.length > 1 ? 's' : ''}</p>
                <p className="text-[10px] text-muted mt-0.5">{data.gaps[0].description}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Dimensions breakdown */}
      <div>
        <button
          onClick={() => setShowDimensions(v => !v)}
          className="flex items-center gap-1.5 text-[10px] text-muted hover:text-white transition-colors w-full"
        >
          {showDimensions ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          {showDimensions ? 'Hide' : 'Show'} breakdown
        </button>
        {showDimensions && (
          <div className="mt-2 space-y-2">
            {data.dimensions.map(d => (
              <div key={d.name}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-muted">{d.name}</span>
                  <span className={clsx('text-[10px] font-medium', d.score >= 80 ? 'text-success' : d.score >= 50 ? 'text-warning' : 'text-danger')}>
                    {Math.round(d.score)}%
                  </span>
                </div>
                <div className="h-1 bg-panel-2 rounded-full overflow-hidden">
                  <div
                    className={clsx('h-full rounded-full transition-all duration-500', d.score >= 80 ? 'bg-success' : d.score >= 50 ? 'bg-warning' : 'bg-danger')}
                    style={{ width: `${d.score}%` }}
                  />
                </div>
                <p className="text-[9px] text-subtle mt-0.5">{d.detail}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Evidence gaps list */}
      {data.gaps.length > 0 && showDimensions && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Coverage gaps</p>
          <div className="space-y-1.5">
            {data.gaps.map((g, i) => (
              <div key={i} className="bg-panel-2 border border-border rounded-md px-3 py-2">
                <p className="text-[10px] text-white font-medium">{g.description}</p>
                <p className="text-[9px] text-muted mt-0.5">
                  {new Date(g.start_time).toLocaleTimeString()} → {new Date(g.end_time).toLocaleTimeString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
