import { useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Loader2, CheckCircle, AlertCircle, Clock, RefreshCw, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import type { EvidenceFile } from '../services/types'

const STATUS_ICON = {
  uploaded: <Clock size={14} className="text-gray-400" />,
  processing: <Loader2 size={14} className="animate-spin text-yellow-400" />,
  processed: <CheckCircle size={14} className="text-green-400" />,
  failed: <AlertCircle size={14} className="text-red-400" />,
}

const ACCEPTED = '.log,.txt,.json,.jsonl,.ndjson,.csv,.git,.syslog'

export default function EvidencePanel({ investigationId }: { investigationId: string }) {
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: files, isLoading } = useQuery<EvidenceFile[]>({
    queryKey: ['evidence', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/evidence`).then(r => r.data),
    refetchInterval: 3000,
  })

  const upload = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post(`/investigations/${investigationId}/evidence`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['evidence', investigationId] })
      qc.invalidateQueries({ queryKey: ['timeline', investigationId] })
    },
  })

  const reprocess = useMutation({
    mutationFn: (evidenceId: string) =>
      api.post(`/investigations/${investigationId}/evidence/${evidenceId}/reprocess`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['evidence', investigationId] })
      qc.invalidateQueries({ queryKey: ['timeline', investigationId] })
    },
  })

  const remove = useMutation({
    mutationFn: (evidenceId: string) =>
      api.delete(`/investigations/${investigationId}/evidence/${evidenceId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['evidence', investigationId] })
      qc.invalidateQueries({ queryKey: ['timeline', investigationId] })
      qc.invalidateQueries({ queryKey: ['confidence', investigationId] })
    },
  })

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    Array.from(e.dataTransfer.files).forEach(f => upload.mutate(f))
  }

  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Evidence Files</h2>

      <div
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-border hover:border-accent/50 rounded-lg p-4 text-center cursor-pointer transition-colors mb-4"
      >
        <Upload size={20} className="mx-auto text-gray-500 mb-1" />
        <p className="text-xs text-gray-500">Drop files or click to upload</p>
        <p className="text-xs text-gray-600 mt-0.5">.log .txt .json .jsonl .csv .git .syslog</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={e => Array.from(e.target.files || []).forEach(f => upload.mutate(f))}
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4"><Loader2 size={16} className="animate-spin text-gray-500" /></div>
      ) : files?.length === 0 ? (
        <p className="text-xs text-gray-600 text-center py-3">No evidence uploaded yet</p>
      ) : (
        <div className="space-y-2">
          {files?.map(f => (
            <div key={f.id} className="flex items-start gap-2.5 p-2.5 bg-surface rounded-lg group">
              <FileText size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white truncate">{f.original_name}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-xs text-gray-600 bg-white/5 px-1.5 py-0.5 rounded font-mono">
                    {f.file_type?.toUpperCase() || '?'}
                  </span>
                  <span className="text-xs text-gray-600">{((f.file_size || 0) / 1024).toFixed(1)} KB</span>
                  {f.sha256 && (
                    <span className="text-xs text-gray-700 font-mono" title={`SHA-256: ${f.sha256}`}>
                      {f.sha256.slice(0, 8)}…
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
                {f.status === 'failed' && (
                  <button
                    onClick={() => reprocess.mutate(f.id)}
                    title="Reprocess"
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-white"
                  >
                    <RefreshCw size={13} />
                  </button>
                )}
                <button
                  onClick={() => remove.mutate(f.id)}
                  title="Delete"
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-danger"
                >
                  <Trash2 size={13} />
                </button>
                {STATUS_ICON[f.status as keyof typeof STATUS_ICON]}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
