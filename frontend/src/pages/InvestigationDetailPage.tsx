import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2, ChevronRight, FileText, List, AlertTriangle, Share2, FileOutput, Plus } from 'lucide-react'
import { api } from '../services/api'
import type { Investigation, TimelineResponse, EvidenceFile } from '../services/types'
import EvidencePanel from '../components/EvidencePanel'
import TimelineView from '../timeline/TimelineView'
import EntityGraph from '../graph/EntityGraph'
import WorkspacePanel from '../components/WorkspacePanel'
import ExportPanel from '../components/ExportPanel'
import clsx from 'clsx'

type Tab = 'overview' | 'timeline' | 'evidence' | 'relationships' | 'anomalies' | 'report'

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: 'overview',       label: 'Overview',       icon: <List size={13} /> },
  { id: 'timeline',       label: 'Timeline',        icon: <List size={13} /> },
  { id: 'evidence',       label: 'Evidence',        icon: <FileText size={13} /> },
  { id: 'relationships',  label: 'Relationships',   icon: <Share2 size={13} /> },
  { id: 'anomalies',      label: 'Anomalies',       icon: <AlertTriangle size={13} /> },
  { id: 'report',         label: 'Report',          icon: <FileOutput size={13} /> },
]

const STATUS_STYLES: Record<string, string> = {
  open:        'bg-success/15 text-success border border-success/30',
  in_review:   'bg-warning/15 text-warning border border-warning/30',
  closed:      'bg-muted/15 text-muted border border-muted/30',
}

export default function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<Tab>('timeline')

  const { data: investigation, isLoading } = useQuery<Investigation>({
    queryKey: ['investigation', id],
    queryFn: () => api.get(`/investigations/${id}`).then(r => r.data),
  })

  const { data: timeline } = useQuery<TimelineResponse>({
    queryKey: ['timeline', id],
    queryFn: () => api.get(`/investigations/${id}/timeline`).then(r => r.data),
    enabled: !!id,
    refetchInterval: 5000,
  })

  const { data: evidence = [] } = useQuery<EvidenceFile[]>({
    queryKey: ['evidence', id],
    queryFn: () => api.get(`/investigations/${id}/evidence`).then(r => r.data),
    enabled: !!id,
    refetchInterval: 3000,
  })

  if (isLoading) return (
    <div className="flex justify-center py-16">
      <Loader2 size={24} className="animate-spin text-muted" />
    </div>
  )
  if (!investigation) return (
    <div className="text-center py-16 text-muted">Investigation not found.</div>
  )

  const eventCount = timeline?.total ?? 0
  const conflictCount = timeline?.conflicts?.length ?? 0
  const evidenceCount = evidence.length

  const statusKey = investigation.status === 'open' ? 'open' : investigation.status
  const statusLabel = investigation.status === 'open' ? 'Open' : investigation.status.replace('_', ' ')

  return (
    <div className="flex flex-col h-full">
      {/* Breadcrumb + header */}
      <div className="px-6 pt-5 pb-4 border-b border-border bg-panel">
        {/* Breadcrumb */}
        <div className="flex items-center gap-1.5 text-xs text-muted mb-3">
          <Link to="/investigations" className="hover:text-white transition-colors">Investigations</Link>
          <ChevronRight size={12} />
          <span className="text-white font-medium">INV-{investigation.id.slice(0,4).toUpperCase()}</span>
        </div>

        {/* Title row */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-white">{investigation.title}</h1>
              <span className={clsx('text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5', STATUS_STYLES[statusKey] || STATUS_STYLES.open)}>
                <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" />
                {statusLabel}
              </span>
            </div>
            {investigation.description && (
              <p className="text-sm text-muted mt-1">{investigation.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => setTab('evidence')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-2 rounded-md text-xs font-medium text-white transition-colors"
            >
              <Plus size={13} />
              Add evidence
            </button>
            <button
              onClick={() => setTab('report')}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-panel-2 hover:bg-white/10 border border-border rounded-md text-xs font-medium text-white transition-colors"
            >
              <FileOutput size={13} />
              Generate report
            </button>
          </div>
        </div>

        {/* Stats chips */}
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <StatChip icon={<FileText size={12} />} label={`${evidenceCount} evidence source${evidenceCount !== 1 ? 's' : ''}`} />
          <StatChip icon={<List size={12} />} label={`${eventCount} events`} />
          {conflictCount > 0 && (
            <StatChip icon={<AlertTriangle size={12} />} label={`${conflictCount} anomal${conflictCount !== 1 ? 'ies' : 'y'}`} variant="warning" />
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-0 px-6 border-b border-border bg-panel overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              'flex items-center gap-1.5 px-4 py-3 text-xs font-medium border-b-2 transition-colors whitespace-nowrap',
              tab === t.id
                ? 'border-accent text-accent'
                : 'border-transparent text-muted hover:text-white'
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {tab === 'timeline' && (
          <TimelineView timeline={timeline} investigationId={id!} />
        )}
        {tab === 'evidence' && (
          <div className="p-6 max-w-3xl">
            <EvidencePanel investigationId={id!} />
          </div>
        )}
        {tab === 'relationships' && (
          <div className="p-6 h-full">
            <EntityGraph investigationId={id!} />
          </div>
        )}
        {tab === 'report' && (
          <div className="p-6 max-w-3xl">
            <ExportPanel investigationId={id!} />
          </div>
        )}
        {tab === 'overview' && (
          <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-5 max-w-5xl">
            <EvidencePanel investigationId={id!} />
            <WorkspacePanel investigationId={id!} />
          </div>
        )}
        {tab === 'anomalies' && (
          <div className="p-6 max-w-3xl">
            <AnomaliesPanel conflicts={timeline?.conflicts ?? []} />
          </div>
        )}
      </div>
    </div>
  )
}

function StatChip({ icon, label, variant }: { icon: React.ReactNode; label: string; variant?: 'warning' }) {
  return (
    <span className={clsx(
      'flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium',
      variant === 'warning'
        ? 'bg-warning/10 border-warning/25 text-warning'
        : 'bg-panel-2 border-border text-muted'
    )}>
      {icon}
      {label}
    </span>
  )
}

function AnomaliesPanel({ conflicts }: { conflicts: { type: string; description: string }[] }) {
  if (conflicts.length === 0) return (
    <div className="bg-panel border border-border rounded-xl p-8 text-center text-muted text-sm">
      No temporal anomalies detected yet.
    </div>
  )
  return (
    <div className="bg-panel border border-border rounded-xl divide-y divide-border">
      {conflicts.map((c, i) => (
        <div key={i} className="px-4 py-3 flex items-start gap-3">
          <AlertTriangle size={14} className="text-warning mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-xs font-medium text-white capitalize">{c.type.replace(/_/g, ' ')}</p>
            <p className="text-xs text-muted mt-0.5">{c.description}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
