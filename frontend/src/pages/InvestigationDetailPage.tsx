import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { api } from '../services/api'
import type { Investigation, TimelineResponse } from '../services/types'
import EvidencePanel from '../components/EvidencePanel'
import TimelineView from '../timeline/TimelineView'
import EntityGraph from '../graph/EntityGraph'
import WorkspacePanel from '../components/WorkspacePanel'
import ExportPanel from '../components/ExportPanel'

export default function InvestigationDetailPage() {
  const { id } = useParams<{ id: string }>()

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

  if (isLoading) return (
    <div className="flex justify-center py-16">
      <Loader2 size={24} className="animate-spin text-gray-500" />
    </div>
  )
  if (!investigation) return (
    <div className="text-center py-16 text-gray-500">Investigation not found.</div>
  )

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{investigation.title}</h1>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            investigation.status === 'open' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
          }`}>{investigation.status}</span>
        </div>
        {investigation.description && (
          <p className="text-gray-400 mt-1 text-sm">{investigation.description}</p>
        )}
      </div>

      {/* Row 1: Evidence + Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-1">
          <EvidencePanel investigationId={id!} />
        </div>
        <div className="lg:col-span-2">
          <TimelineView timeline={timeline} investigationId={id!} />
        </div>
      </div>

      {/* Row 2: Entity graph (full width) */}
      <EntityGraph investigationId={id!} />

      {/* Row 3: Notes + Export */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <WorkspacePanel investigationId={id!} />
        <ExportPanel investigationId={id!} />
      </div>
    </div>
  )
}
