import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Library, FileText, CheckCircle, AlertCircle, Clock, Loader2, Search, ChevronRight } from 'lucide-react'
import { api } from '../services/api'
import { format } from 'date-fns'
import clsx from 'clsx'

interface EvidenceRow {
  id: string
  investigation_id: string
  investigation_title: string
  original_name: string
  file_type: string | null
  file_size: number | null
  sha256: string | null
  status: string
  uploaded_at: string | null
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  uploaded:   <Clock size={13} className="text-muted" />,
  processing: <Loader2 size={13} className="animate-spin text-warning" />,
  processed:  <CheckCircle size={13} className="text-success" />,
  failed:     <AlertCircle size={13} className="text-danger" />,
}

const STATUS_BADGE: Record<string, string> = {
  uploaded:   'bg-muted/10 text-muted border-muted/20',
  processing: 'bg-warning/10 text-warning border-warning/20',
  processed:  'bg-success/10 text-success border-success/20',
  failed:     'bg-danger/10 text-danger border-danger/20',
}

const EXT_COLOR: Record<string, string> = {
  txt:    'bg-blue-500/15 text-blue-400',
  log:    'bg-blue-500/15 text-blue-400',
  json:   'bg-yellow-500/15 text-yellow-400',
  jsonl:  'bg-yellow-500/15 text-yellow-400',
  csv:    'bg-green-500/15 text-green-400',
  git:    'bg-purple-500/15 text-purple-400',
  cicd:   'bg-cyan-500/15 text-cyan-400',
  syslog: 'bg-orange-500/15 text-orange-400',
}

function formatSize(bytes: number | null) {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function EvidenceLibraryPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const { data: files = [], isLoading } = useQuery<EvidenceRow[]>({
    queryKey: ['evidence-library'],
    queryFn: () => api.get('/evidence').then(r => r.data),
    refetchInterval: 5000,
  })

  const statuses = ['all', 'processed', 'processing', 'failed', 'uploaded']

  const filtered = files.filter(f => {
    if (statusFilter !== 'all' && f.status !== statusFilter) return false
    if (search) {
      const q = search.toLowerCase()
      if (!f.original_name.toLowerCase().includes(q) && !f.investigation_title.toLowerCase().includes(q)) return false
    }
    return true
  })

  const totalSize = files.reduce((acc, f) => acc + (f.file_size ?? 0), 0)
  const processedCount = files.filter(f => f.status === 'processed').length

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Library size={18} className="text-accent" />
            Evidence Library
          </h1>
          <p className="text-xs text-muted mt-0.5">All uploaded evidence files across investigations</p>
        </div>

        {/* Summary chips */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-2.5 py-1 rounded-md bg-panel-2 border border-border text-muted">
            {files.length} file{files.length !== 1 ? 's' : ''}
          </span>
          <span className="text-[10px] px-2.5 py-1 rounded-md bg-success/10 border border-success/20 text-success">
            {processedCount} processed
          </span>
          <span className="text-[10px] px-2.5 py-1 rounded-md bg-panel-2 border border-border text-muted">
            {formatSize(totalSize)} total
          </span>
        </div>
      </div>

      {/* Search + status filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search files or investigations..."
            className="w-full bg-panel border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-white placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
          />
        </div>
        <div className="flex items-center gap-1.5">
          {statuses.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={clsx(
                'text-[10px] px-2.5 py-1 rounded-md border capitalize transition-colors',
                statusFilter === s
                  ? s === 'all' ? 'bg-white/10 border-white/20 text-white font-medium'
                    : clsx(STATUS_BADGE[s], 'font-medium')
                  : 'bg-transparent border-border text-muted hover:text-white'
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={20} className="animate-spin text-muted" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-muted">
          <div className="w-12 h-12 rounded-full bg-panel border border-border flex items-center justify-center mx-auto mb-4">
            <Library size={20} className="opacity-40" />
          </div>
          <p className="text-sm">{files.length === 0 ? 'No evidence files yet' : 'No files match your search'}</p>
          {files.length === 0 && (
            <p className="text-xs mt-1 text-subtle">Upload evidence files inside an investigation to see them here</p>
          )}
        </div>
      ) : (
        <div className="bg-panel border border-border rounded-xl overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[2fr_1.5fr_80px_80px_100px_32px] gap-3 px-4 py-2.5 border-b border-border bg-panel-2 text-[10px] uppercase tracking-wider text-muted font-semibold">
            <span>File</span>
            <span>Investigation</span>
            <span>Type</span>
            <span>Size</span>
            <span>Uploaded</span>
            <span></span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-border">
            {filtered.map(f => (
              <div key={f.id} className="grid grid-cols-[2fr_1.5fr_80px_80px_100px_32px] gap-3 px-4 py-3 items-center hover:bg-white/3 transition-colors group">
                {/* File */}
                <div className="flex items-center gap-2.5 min-w-0">
                  <FileText size={13} className="text-muted flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-white truncate font-medium">{f.original_name}</p>
                    {f.sha256 && (
                      <p className="text-[9px] text-subtle font-mono mt-0.5" title={`SHA-256: ${f.sha256}`}>
                        {f.sha256.slice(0, 12)}…
                      </p>
                    )}
                  </div>
                </div>

                {/* Investigation */}
                <Link
                  to={`/investigations/${f.investigation_id}`}
                  className="flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors min-w-0 group/link"
                  onClick={e => e.stopPropagation()}
                >
                  <span className="truncate">{f.investigation_title}</span>
                  <ChevronRight size={10} className="flex-shrink-0 opacity-0 group-hover/link:opacity-100 transition-opacity" />
                </Link>

                {/* Type */}
                <span className={clsx(
                  'text-[10px] px-2 py-0.5 rounded font-mono font-medium w-fit uppercase',
                  EXT_COLOR[f.file_type ?? ''] ?? 'bg-muted/10 text-muted'
                )}>
                  {f.file_type ?? '?'}
                </span>

                {/* Size */}
                <span className="text-xs text-muted">{formatSize(f.file_size)}</span>

                {/* Uploaded */}
                <span className="text-[10px] text-muted">
                  {f.uploaded_at ? format(new Date(f.uploaded_at), 'MMM d, HH:mm') : '—'}
                </span>

                {/* Status icon */}
                <div className="flex justify-end">
                  {STATUS_ICON[f.status] ?? STATUS_ICON.uploaded}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
