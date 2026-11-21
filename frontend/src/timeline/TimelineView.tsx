import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Clock, ChevronDown, ChevronUp, Filter, AlertCircle, Gauge, Copy, Flag } from 'lucide-react'
import type { TimelineResponse, Event, Conflict } from '../services/types'
import { format } from 'date-fns'
import clsx from 'clsx'
import { api } from '../services/api'

const SEVERITY_STYLE: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  error: 'bg-red-400/10 text-red-400 border-red-400/30',
  warning: 'bg-yellow-400/10 text-yellow-400 border-yellow-400/30',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  debug: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
}

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  error: 'bg-red-400',
  warning: 'bg-yellow-400',
  info: 'bg-blue-400',
  debug: 'bg-gray-500',
}

const CONFLICT_STYLE: Record<string, { bg: string; icon: React.ReactNode; label: string }> = {
  out_of_order:         { bg: 'bg-red-500/10 border-red-500/30 text-red-400',    icon: <AlertCircle size={13} />, label: 'Out of order' },
  clock_skew:           { bg: 'bg-orange-500/10 border-orange-500/30 text-orange-400', icon: <Gauge size={13} />, label: 'Clock skew' },
  duplicate_timestamps: { bg: 'bg-yellow-400/10 border-yellow-400/30 text-yellow-400', icon: <Copy size={13} />, label: 'Duplicate timestamps' },
  gap_anomaly:          { bg: 'bg-purple-500/10 border-purple-500/30 text-purple-400', icon: <AlertTriangle size={13} />, label: 'Gap anomaly' },
}

const SEVERITIES = ['all', 'critical', 'error', 'warning', 'info', 'debug']

export default function TimelineView({ timeline, investigationId }: { timeline?: TimelineResponse; investigationId: string }) {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState('all')
  const [showConflicts, setShowConflicts] = useState(true)

  const { data: flags = [] } = useQuery<{ id: string; event_id: string; label: string | null }[]>({
    queryKey: ['flags', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/flags`).then(r => r.data),
  })

  const flagEvent = useMutation({
    mutationFn: (event_id: string) =>
      api.post(`/investigations/${investigationId}/flags`, { event_id }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['flags', investigationId] }),
  })

  const unflagEvent = useMutation({
    mutationFn: (flagId: string) =>
      api.delete(`/investigations/${investigationId}/flags/${flagId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['flags', investigationId] }),
  })

  const flagMap = Object.fromEntries(flags.map(f => [f.event_id, f.id]))

  if (!timeline) return (
    <div className="bg-panel border border-border rounded-xl p-6 text-center text-gray-500 text-sm">
      Upload evidence files to see the timeline
    </div>
  )

  const filtered = severityFilter === 'all'
    ? timeline.events
    : timeline.events.filter(e => e.severity === severityFilter)

  const conflictsByType = timeline.conflicts.reduce<Record<string, Conflict[]>>((acc, c) => {
    acc[c.type] = [...(acc[c.type] || []), c]
    return acc
  }, {})

  return (
    <div className="bg-panel border border-border rounded-xl p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Timeline</h2>
        <span className="text-xs text-gray-500">{filtered.length} / {timeline.total} events</span>
      </div>

      {/* Severity filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <Filter size={12} className="text-gray-600 flex-shrink-0" />
        {SEVERITIES.map(s => {
          const count = s === 'all' ? timeline.total : timeline.events.filter(e => e.severity === s).length
          if (s !== 'all' && count === 0) return null
          return (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={clsx(
                'text-xs px-2 py-0.5 rounded-full border transition-colors capitalize flex items-center gap-1',
                severityFilter === s
                  ? s === 'all' ? 'bg-white/10 border-white/20 text-white' : `${SEVERITY_STYLE[s]} font-medium`
                  : 'border-border text-gray-600 hover:text-gray-300 hover:border-gray-600'
              )}
            >
              {s}
              <span className="opacity-60">{count}</span>
            </button>
          )
        })}
      </div>

      {/* Conflict summary */}
      {timeline.conflicts.length > 0 && (
        <div className="rounded-lg border border-yellow-400/20 overflow-hidden">
          <button
            onClick={() => setShowConflicts(v => !v)}
            className="w-full flex items-center justify-between px-3 py-2 bg-yellow-400/5 hover:bg-yellow-400/10 transition-colors"
          >
            <span className="flex items-center gap-2 text-yellow-400 text-xs font-medium">
              <AlertTriangle size={13} />
              {timeline.conflicts.length} temporal anomal{timeline.conflicts.length > 1 ? 'ies' : 'y'} detected
            </span>
            {showConflicts ? <ChevronUp size={13} className="text-gray-500" /> : <ChevronDown size={13} className="text-gray-500" />}
          </button>
          {showConflicts && (
            <div className="divide-y divide-border/50">
              {Object.entries(conflictsByType).map(([type, items]) => {
                const style = CONFLICT_STYLE[type] || CONFLICT_STYLE.out_of_order
                return (
                  <div key={type} className={clsx('px-3 py-2 border-l-2', style.bg)}>
                    <div className="flex items-center gap-1.5 text-xs font-medium mb-1">
                      {style.icon}
                      {style.label} ({items.length})
                    </div>
                    {items.slice(0, 3).map((c, i) => (
                      <p key={i} className="text-xs text-gray-400 ml-5 leading-relaxed">{c.description}</p>
                    ))}
                    {items.length > 3 && (
                      <p className="text-xs text-gray-600 ml-5">+{items.length - 3} more</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Event list */}
      {filtered.length === 0 ? (
        <p className="text-xs text-gray-600 text-center py-6">No events match the current filter</p>
      ) : (
        <div className="space-y-1 max-h-[560px] overflow-y-auto pr-1">
          {filtered.map(ev => (
            <EventRow
              key={ev.id}
              event={ev}
              expanded={expanded === ev.id}
              onToggle={() => setExpanded(expanded === ev.id ? null : ev.id)}
              isConflict={timeline.conflicts.some(c => c.event_a_id === ev.id || c.event_b_id === ev.id)}
              isFlagged={!!flagMap[ev.id]}
              onFlag={() => flagMap[ev.id] ? unflagEvent.mutate(flagMap[ev.id]) : flagEvent.mutate(ev.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function EventRow({
  event, expanded, onToggle, isConflict, isFlagged, onFlag
}: {
  event: Event; expanded: boolean; onToggle: () => void; isConflict: boolean; isFlagged: boolean; onFlag: () => void
}) {
  const sev = event.severity || 'info'
  const style = SEVERITY_STYLE[sev] || SEVERITY_STYLE.info

  return (
    <div className={clsx(
      'border rounded-lg overflow-hidden transition-shadow',
      style,
      isConflict && 'ring-1 ring-yellow-400/40'
    )}>
      <button onClick={onToggle} className="w-full flex items-center gap-2.5 px-3 py-2 text-left group">
        <div className="flex flex-col items-center gap-0.5">
          <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', SEVERITY_DOT[sev] || SEVERITY_DOT.info)} />
          {isConflict && <div className="w-1 h-1 rounded-full bg-yellow-400/60 flex-shrink-0" />}
        </div>
        <div className="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
          {event.timestamp ? (
            <span className="text-xs text-gray-400 flex-shrink-0 font-mono">
              {format(new Date(event.timestamp), 'MM-dd HH:mm:ss')}
              {event.timestamp_confidence < 1 && (
                <span className="text-yellow-400 ml-0.5" title={`Confidence: ${Math.round(event.timestamp_confidence * 100)}%`}>~</span>
              )}
            </span>
          ) : (
            <span className="text-xs text-gray-600 flex-shrink-0 italic">no timestamp</span>
          )}
          {event.actor && (
            <span className="text-xs font-medium bg-white/10 px-1.5 py-0.5 rounded shrink-0">{event.actor}</span>
          )}
          {event.action && (
            <span className="text-[10px] uppercase tracking-wider font-bold opacity-70 shrink-0">{event.action}</span>
          )}
          {event.object && (
            <span className="text-xs text-gray-400 truncate max-w-[160px]">{event.object}</span>
          )}
          {!event.actor && !event.action && !event.object && (
            <span className="text-xs text-gray-300 truncate">{event.raw?.slice(0, 90)}</span>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0 mt-0.5">
          <button
            onClick={e => { e.stopPropagation(); onFlag() }}
            title={isFlagged ? 'Unflag event' : 'Flag event'}
            className={clsx(
              'p-0.5 rounded transition-colors opacity-0 group-hover:opacity-100',
              isFlagged ? 'text-yellow-400 opacity-100' : 'text-gray-600 hover:text-yellow-400'
            )}
          >
            <Flag size={12} fill={isFlagged ? 'currentColor' : 'none'} />
          </button>
          {expanded ? <ChevronUp size={13} className="text-gray-500" /> : <ChevronDown size={13} className="text-gray-500" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-current/10 pt-2 space-y-2">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            {event.source && <Detail label="Source" value={event.source.split('/').pop() || event.source} />}
            {event.source_line != null && <Detail label="Line" value={String(event.source_line)} />}
            {event.severity && <Detail label="Severity" value={event.severity} />}
            {event.timestamp_confidence < 1 && (
              <Detail label="Timestamp confidence" value={`${Math.round(event.timestamp_confidence * 100)}%`} />
            )}
          </div>
          {event.extra && Object.keys(event.extra).length > 0 && (
            <div className="flex flex-wrap gap-1">
              {Object.entries(event.extra).slice(0, 8).map(([k, v]) => (
                <span key={k} className="text-xs bg-black/30 px-1.5 py-0.5 rounded text-gray-400">
                  <span className="text-gray-600">{k}:</span> {String(v).slice(0, 50)}
                </span>
              ))}
            </div>
          )}
          {event.raw && (
            <pre className="p-2 bg-black/30 rounded text-xs text-gray-400 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
              {event.raw}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-gray-600">{label}: </span>
      <span className="text-gray-300">{value}</span>
    </div>
  )
}
