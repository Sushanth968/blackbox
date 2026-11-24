import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle, Clock, Filter, Flag,
  Search, X, ChevronDown, SlidersHorizontal, Send, AlignJustify
} from 'lucide-react'
import type { TimelineResponse, Event, Conflict } from '../services/types'
import { format } from 'date-fns'
import clsx from 'clsx'
import { api } from '../services/api'
import { EventLabelBadge } from '../components/ConfidencePanel': Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  error:    'bg-red-400/15 text-red-400 border-red-400/25',
  warning:  'bg-warning/15 text-warning border-warning/25',
  info:     'bg-accent/10 text-accent border-accent/20',
  debug:    'bg-muted/10 text-muted border-muted/20',
}

const SEV_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  error:    'bg-red-400',
  warning:  'bg-warning',
  info:     'bg-accent',
  debug:    'bg-muted',
}

const SEV_LINE: Record<string, string> = {
  critical: 'border-red-500/40',
  error:    'border-red-400/30',
  warning:  'border-warning/30',
  info:     'border-accent/20',
  debug:    'border-muted/20',
}

const SEV_ROW_ACTIVE: Record<string, string> = {
  critical: 'bg-red-500/8 border-red-500/30',
  error:    'bg-red-400/6 border-red-400/25',
  warning:  'bg-warning/8 border-warning/25',
  info:     'bg-accent/8 border-accent/20',
  debug:    'bg-muted/5 border-muted/15',
}

const CONFLICT_LABEL: Record<string, string> = {
  out_of_order:         'Out of order',
  clock_skew:           'Clock skew',
  duplicate_timestamps: 'Duplicate timestamps',
  gap_anomaly:          'Gap anomaly',
}

const SEVERITIES = ['all', 'critical', 'error', 'warning', 'info', 'debug']

export default function TimelineView({ timeline, investigationId }: { timeline?: TimelineResponse; investigationId: string }) {
  const qc = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState('all')
  const [actorFilter, setActorFilter] = useState('all')
  const [chatInput, setChatInput] = useState('')

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
    <div className="flex items-center justify-center h-full text-muted text-sm">
      Upload evidence files to see the timeline
    </div>
  )

  const actors = Array.from(new Set(timeline.events.map(e => e.actor).filter(Boolean))) as string[]

  const filtered = timeline.events.filter(e => {
    if (severityFilter !== 'all' && e.severity !== severityFilter) return false
    if (actorFilter !== 'all' && e.actor !== actorFilter) return false
    return true
  })

  const selectedEvent = selectedId ? filtered.find(e => e.id === selectedId) ?? null : null

  const conflictSet = new Set(
    timeline.conflicts.flatMap(c => [c.event_a_id, c.event_b_id].filter(Boolean))
  )

  return (
    <div className="flex h-full">
      {/* ── Left: Filters ── */}
      <div className="w-56 flex-shrink-0 border-r border-border bg-panel flex flex-col overflow-y-auto">
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <span className="text-xs font-semibold text-white">Timeline filters</span>
          <SlidersHorizontal size={13} className="text-muted" />
        </div>

        <div className="p-4 space-y-5 flex-1">
          {/* Date range placeholder */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Date range</p>
            <div className="flex items-center gap-1.5 bg-panel-2 border border-border rounded-md px-2.5 py-1.5 text-xs text-muted">
              <Clock size={11} className="flex-shrink-0" />
              <span className="truncate">All time</span>
            </div>
          </div>

          {/* Sources */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Sources</p>
            <div className="space-y-1.5">
              {['GitHub', 'CI/CD', 'Runtime logs', 'Auth'].map((src, i) => (
                <label key={src} className="flex items-center justify-between cursor-pointer group">
                  <div className="flex items-center gap-2">
                    <div className={clsx('w-3.5 h-3.5 rounded border flex items-center justify-center transition-colors',
                      i < 3 ? 'bg-accent/20 border-accent/40' : 'bg-transparent border-border group-hover:border-muted'
                    )}>
                      {i < 3 && <div className="w-1.5 h-1.5 rounded-sm bg-accent" />}
                    </div>
                    <span className="text-xs text-muted group-hover:text-white transition-colors">{src}</span>
                  </div>
                  <span className="text-[10px] text-subtle">{[3, 2, 2, 1][i]}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Event types */}
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Event types</p>
            <div className="flex flex-wrap gap-1.5">
              {SEVERITIES.filter(s => s !== 'all').map(s => {
                const count = timeline.events.filter(e => e.severity === s).length
                if (count === 0) return null
                const active = severityFilter === s
                return (
                  <button
                    key={s}
                    onClick={() => setSeverityFilter(active ? 'all' : s)}
                    className={clsx(
                      'text-[10px] px-2 py-0.5 rounded-full border capitalize transition-colors',
                      active ? SEV_BADGE[s] : 'border-border text-muted hover:text-white'
                    )}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Actor filter */}
          {actors.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Actor</p>
              <div className="relative">
                <select
                  value={actorFilter}
                  onChange={e => setActorFilter(e.target.value)}
                  className="w-full appearance-none bg-panel-2 border border-border rounded-md px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-accent/50 pr-6"
                >
                  <option value="all">All actors</option>
                  {actors.map(a => <option key={a} value={a}>{a}</option>)}
                </select>
                <ChevronDown size={10} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
              </div>
            </div>
          )}
        </div>

        {/* Clear filters */}
        <div className="p-3 border-t border-border">
          <button
            onClick={() => { setSeverityFilter('all'); setActorFilter('all') }}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 text-xs text-muted hover:text-white transition-colors"
          >
            <X size={11} />
            Clear filters
          </button>
        </div>
      </div>

      {/* ── Center: Event feed ── */}
      <div className="flex-1 flex flex-col min-w-0 border-r border-border">
        {/* Feed header */}
        <div className="px-4 py-3 border-b border-border flex items-center gap-3 bg-panel flex-shrink-0">
          <div className="flex-1">
            <span className="text-xs font-semibold text-white">Event timeline</span>
            <span className="text-xs text-muted ml-2">{filtered.length} events</span>
          </div>
          <button className="p-1.5 text-muted hover:text-white rounded transition-colors hover:bg-white/5">
            <Search size={13} />
          </button>
          <div className="flex items-center gap-1.5 bg-panel-2 border border-border rounded-md px-2 py-1 text-xs text-muted">
            <span>Reconstructed order</span>
            <ChevronDown size={10} />
          </div>
          <button className="flex items-center gap-1 bg-panel-2 border border-border rounded-md px-2 py-1 text-[10px] text-muted hover:text-white transition-colors">
            <Filter size={10} />
            Dense
          </button>
        </div>

        {/* Feed list */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-muted text-sm">
              No events match the current filter
            </div>
          ) : (
            <div className="relative">
              {/* Timeline spine */}
              <div className="absolute left-[72px] top-0 bottom-0 w-px bg-border" />

              {filtered.map((ev) => {
                const sev = ev.severity || 'info'
                const isSelected = selectedId === ev.id
                const isConflict = conflictSet.has(ev.id)
                const isFlagged = !!flagMap[ev.id]

                return (
                  <div
                    key={ev.id}
                    onClick={() => setSelectedId(isSelected ? null : ev.id)}
                    className={clsx(
                      'relative flex items-start gap-3 px-4 py-3 cursor-pointer border-b border-border/50 transition-colors group',
                      isSelected ? SEV_ROW_ACTIVE[sev] || SEV_ROW_ACTIVE.info : 'hover:bg-white/3',
                      isSelected && 'border-l-2 ' + SEV_LINE[sev]
                    )}
                  >
                    {/* Timestamp */}
                    <div className="w-14 flex-shrink-0 text-right">
                      <span className="text-[10px] font-mono text-muted">
                        {ev.timestamp ? format(new Date(ev.timestamp), 'HH:mm:ss') : '--:--:--'}
                      </span>
                    </div>

                    {/* Node on spine */}
                    <div className="relative flex-shrink-0 z-10 w-5 flex justify-center pt-1">
                      <div className={clsx(
                        'w-2.5 h-2.5 rounded-full border-2 border-panel',
                        isSelected ? (SEV_DOT[sev] || SEV_DOT.info) : (isConflict ? 'bg-warning' : (SEV_DOT[sev] || SEV_DOT.info))
                      )} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-white truncate">
                            {ev.action ? ev.action.replace(/_/g, ' ') : ev.raw?.slice(0, 60) || 'Event'}
                          </p>
                          <p className="text-[10px] text-muted mt-0.5 truncate">
                            {[ev.actor, ev.object].filter(Boolean).join(' · ') || ev.source?.split('/').pop() || ''}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          {isConflict && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-warning/15 text-warning border border-warning/25 font-medium">
                              Anomaly
                            </span>
                          )}
                          {ev.severity && ev.severity !== 'info' && (
                            <span className={clsx('text-[9px] px-1.5 py-0.5 rounded border font-medium capitalize', SEV_BADGE[sev])}>
                              {ev.severity}
                            </span>
                          )}
                          <EventLabelBadge
                            eventId={ev.id}
                            investigationId={investigationId}
                            currentLabel={ev.label_type}
                          />
                          <button
                            onClick={e => { e.stopPropagation(); isFlagged ? unflagEvent.mutate(flagMap[ev.id]) : flagEvent.mutate(ev.id) }}
                            className={clsx(
                              'p-0.5 rounded transition-all',
                              isFlagged ? 'text-warning' : 'text-transparent group-hover:text-muted hover:!text-warning'
                            )}
                          >
                            <Flag size={11} fill={isFlagged ? 'currentColor' : 'none'} />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Temporal analysis banner */}
        {timeline.conflicts.length > 0 && (
          <div className="flex items-center gap-3 px-4 py-2.5 bg-warning/8 border-t border-warning/20 flex-shrink-0">
            <AlertTriangle size={13} className="text-warning flex-shrink-0" />
            <span className="text-xs text-warning flex-1">
              <span className="font-medium">Temporal analysis:</span> {timeline.conflicts.length} ordering conflict{timeline.conflicts.length > 1 ? 's' : ''} in current view
            </span>
            <button className="flex items-center gap-1 text-[10px] text-warning border border-warning/30 rounded px-2 py-1 hover:bg-warning/10 transition-colors">
              Review conflict →
            </button>
          </div>
        )}

        {/* Chat bar */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-t border-border bg-panel flex-shrink-0">
          <span className="text-muted flex-shrink-0">✦</span>
          <input
            type="text"
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            placeholder="Ask about this investigation..."
            className="flex-1 bg-transparent text-xs text-white placeholder-muted focus:outline-none"
          />
          <button className="p-1.5 text-muted hover:text-white transition-colors">
            <Send size={13} />
          </button>
        </div>
      </div>

      {/* ── Right: Event details panel ── */}
      <div className="w-72 flex-shrink-0 bg-panel flex flex-col overflow-y-auto">
        {selectedEvent ? (
          <EventDetailsPanel
            event={selectedEvent}
            conflicts={timeline.conflicts.filter(c => c.event_a_id === selectedEvent.id || c.event_b_id === selectedEvent.id)}
            onClose={() => setSelectedId(null)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-muted px-6 text-center">
            <div className="w-10 h-10 rounded-full bg-panel-2 border border-border flex items-center justify-center">
              <AlignJustify size={16} />
            </div>
            <p className="text-xs">Click any event in the timeline to see details</p>
          </div>
        )}
      </div>
    </div>
  )
}

function EventDetailsPanel({ event, conflicts, onClose }: {
  event: Event
  conflicts: Conflict[]
  onClose: () => void
}) {
  const sev = event.severity || 'info'
  const eventId = `EVT-${event.id.slice(0, 5).toUpperCase()}`

  return (
    <>
      {/* Panel header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between flex-shrink-0">
        <span className="text-xs font-semibold text-white">Event details</span>
        <button onClick={onClose} className="p-1 text-muted hover:text-white transition-colors rounded">
          <X size={13} />
        </button>
      </div>

      <div className="p-4 space-y-4 flex-1">
        {/* Event ID + severity */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {sev === 'error' || sev === 'critical' ? (
              <AlertTriangle size={15} className="text-red-400" />
            ) : sev === 'warning' ? (
              <AlertTriangle size={15} className="text-warning" />
            ) : (
              <Clock size={15} className="text-accent" />
            )}
            <span className="text-sm font-bold text-white">{eventId}</span>
          </div>
          {sev !== 'info' && (
            <span className={clsx('text-[10px] px-2 py-0.5 rounded border font-medium capitalize', SEV_BADGE[sev])}>
              {sev === 'error' ? 'Runtime error' : sev}
            </span>
          )}
        </div>

        {/* Timestamp */}
        {event.timestamp && (
          <div className="flex items-center gap-2 text-xs text-muted">
            <Clock size={11} className="flex-shrink-0" />
            <span className="font-mono">{format(new Date(event.timestamp), 'HH:mm:ss zzz')}</span>
          </div>
        )}

        {/* Raw / description */}
        {event.raw && (
          <p className="text-xs text-white/80 leading-relaxed bg-panel-2 border border-border rounded-md px-3 py-2">
            {event.raw.slice(0, 120)}
          </p>
        )}

        {/* Fields */}
        <div className="space-y-2">
          {[
            { label: 'Actor',  value: event.actor,  icon: '👤' },
            { label: 'Entity', value: event.object, icon: '⬡' },
            { label: 'Source', value: event.source?.split('/').pop(), icon: '📄' },
          ].filter(f => f.value).map(f => (
            <div key={f.label} className="flex items-center gap-2 text-xs">
              <span className="w-28 text-muted flex items-center gap-1.5">
                <span className="text-[10px]">{f.icon}</span>
                {f.label}
              </span>
              <span className="text-white font-medium truncate">{f.value}</span>
            </div>
          ))}
          {event.timestamp && (
            <div className="flex items-center gap-2 text-xs">
              <span className="w-28 text-muted flex items-center gap-1.5">
                <span className="text-[10px]">🗓</span>
                Original timestamp
              </span>
              <span className="text-white font-mono text-[10px]">{format(new Date(event.timestamp), 'HH:mm:ss xxx')}</span>
            </div>
          )}
          {event.timestamp_confidence < 1 && (
            <div className="flex items-center gap-2 text-xs">
              <span className="w-28 text-muted flex items-center gap-1.5">
                <span className="text-[10px]">🛡</span>
                Extraction conf.
              </span>
              <span className="text-white font-medium">{event.timestamp_confidence.toFixed(2)}</span>
            </div>
          )}
        </div>

        {/* Evidence provenance */}
        {event.source && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase tracking-wider text-muted font-semibold">Evidence provenance</span>
              <span className="flex items-center gap-1 text-[10px] text-success bg-success/10 border border-success/25 rounded px-1.5 py-0.5">
                ✓ Integrity verified
              </span>
            </div>
            <div className="bg-panel-2 border border-border rounded-md p-2.5">
              <div className="flex items-start gap-2">
                <div className="w-6 h-6 bg-panel border border-border rounded flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[9px] text-muted">📄</span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-white font-medium truncate">{event.source.split('/').pop()}</p>
                  {event.source_line && (
                    <p className="text-[10px] text-muted mt-0.5">Line {event.source_line}</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Conflicts */}
        {conflicts.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Temporal conflicts</p>
            <div className="space-y-1.5">
              {conflicts.map((c, i) => (
                <div key={i} className="bg-warning/8 border border-warning/20 rounded-md px-3 py-2">
                  <p className="text-[10px] font-medium text-warning capitalize">{CONFLICT_LABEL[c.type] || c.type}</p>
                  <p className="text-[10px] text-muted mt-0.5">{c.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="border-t border-border pt-3">
          <p className="text-[10px] uppercase tracking-wider text-muted font-semibold mb-2">Legend</p>
          <div className="space-y-1.5">
            {[
              { color: 'bg-accent', label: 'Extracted event' },
              { color: 'bg-purple-400', label: 'Inferred relationship' },
              { color: 'bg-warning', label: 'Anomaly' },
              { color: 'bg-success', label: 'User-confirmed conclusion' },
            ].map(l => (
              <div key={l.label} className="flex items-center gap-2">
                <div className={clsx('w-2.5 h-2.5 rounded-full flex-shrink-0', l.color)} />
                <span className="text-[10px] text-muted">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
