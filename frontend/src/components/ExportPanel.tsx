import { useQuery } from '@tanstack/react-query'
import { Download, FileJson, FileText } from 'lucide-react'
import { api } from '../services/api'

interface FlagSummary {
  id: string
  event_id: string
  label: string | null
  flagged_at: string
}

export default function ExportPanel({ investigationId }: { investigationId: string }) {
  const { data: flags = [] } = useQuery<FlagSummary[]>({
    queryKey: ['flags', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/flags`).then(r => r.data),
  })

  const downloadJson = () => {
    window.open(`/api/investigations/${investigationId}/export/json`, '_blank')
  }

  const downloadReport = () => {
    window.open(`/api/investigations/${investigationId}/export/report`, '_blank')
  }

  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <h2 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
        <Download size={14} />
        Export
      </h2>

      <div className="space-y-2">
        <button
          onClick={downloadJson}
          className="w-full flex items-center gap-3 px-3 py-2.5 bg-surface border border-border hover:border-accent/50 rounded-lg text-sm transition-colors text-left group"
        >
          <FileJson size={16} className="text-blue-500 flex-shrink-0" />
          <div>
            <p className="text-foreground text-sm">JSON Export</p>
            <p className="text-xs text-muted">Full investigation data — events, entities, notes</p>
          </div>
          <Download size={13} className="ml-auto text-subtle group-hover:text-muted" />
        </button>

        <button
          onClick={downloadReport}
          className="w-full flex items-center gap-3 px-3 py-2.5 bg-surface border border-border hover:border-accent/50 rounded-lg text-sm transition-colors text-left group"
        >
          <FileText size={16} className="text-success flex-shrink-0" />
          <div>
            <p className="text-foreground text-sm">Text Report</p>
            <p className="text-xs text-muted">
              Readable summary with flagged events{flags.length > 0 ? ` (${flags.length} flagged)` : ''}, conflicts, entities
            </p>
          </div>
          <Download size={13} className="ml-auto text-subtle group-hover:text-muted" />
        </button>
      </div>

      {flags.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border">
          <p className="text-xs text-muted mb-2">Flagged events ({flags.length})</p>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {flags.map(f => (
              <div key={f.id} className="flex items-center gap-2 text-xs text-muted">
                <span className="w-1.5 h-1.5 rounded-full bg-warning flex-shrink-0" />
                <span className="font-mono text-subtle text-[10px]">{f.event_id.slice(0, 8)}…</span>
                {f.label && <span className="text-foreground">{f.label}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
