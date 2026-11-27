import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, FolderSearch, Loader2, ChevronRight, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import type { Investigation } from '../services/types'
import { format } from 'date-fns'
import clsx from 'clsx'

const STATUS_STYLES: Record<string, string> = {
  open:      'bg-success/15 text-success border border-success/30',
  in_review: 'bg-warning/15 text-warning border-warning/30',
  closed:    'bg-muted/10 text-muted border-muted/20',
}

export default function InvestigationsPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  const { data: investigations, isLoading } = useQuery<Investigation[]>({
    queryKey: ['investigations'],
    queryFn: () => api.get('/investigations/').then(r => r.data),
  })

  const create = useMutation({
    mutationFn: (payload: { title: string; description: string }) =>
      api.post('/investigations/', payload).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['investigations'] })
      setShowForm(false)
      setTitle('')
      setDescription('')
    },
  })

  const remove = useMutation({
    mutationFn: (id: string) => api.delete(`/investigations/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['investigations'] })
      setConfirmDelete(null)
    },
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-foreground">Investigations</h1>
          <p className="text-xs text-muted mt-0.5">Evidence-driven event reconstruction</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-2 rounded-md text-xs font-medium text-white transition-colors"
        >
          <Plus size={13} />
          New Investigation
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-panel border border-border rounded-xl p-5 mb-5">
          <h2 className="text-xs font-semibold mb-4 text-foreground">New Investigation</h2>
          <input
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-xs text-foreground mb-3 focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
            placeholder="Title — e.g. Production API failure after deployment"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <textarea
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-xs text-foreground mb-3 resize-none focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
            placeholder="Description (optional)"
            rows={2}
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              onClick={() => create.mutate({ title, description })}
              disabled={!title || create.isPending}
              className="px-3 py-1.5 bg-accent hover:bg-accent-2 disabled:opacity-50 rounded-md text-xs font-medium text-white transition-colors"
            >
              {create.isPending ? 'Creating…' : 'Create'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 bg-panel-2 hover:bg-black/10 border border-border rounded-md text-xs text-muted hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={20} className="animate-spin text-muted" />
        </div>
      ) : investigations?.length === 0 ? (
        <div className="text-center py-20 text-muted">
          <div className="w-12 h-12 rounded-full bg-panel border border-border flex items-center justify-center mx-auto mb-4">
            <FolderSearch size={20} className="opacity-40" />
          </div>
          <p className="text-sm">No investigations yet</p>
          <p className="text-xs mt-1 text-subtle">Create one to start reconstructing events</p>
        </div>
      ) : (
        <div className="space-y-2">
          {investigations?.map(inv => {
            const statusKey = inv.status
            return (
              <div key={inv.id} className="relative group">
                <Link
                  to={`/investigations/${inv.id}`}
                  className="flex items-center gap-4 bg-panel border border-border hover:border-border-2 rounded-xl px-5 py-4 transition-all"
                >
                  <div className="w-9 h-9 rounded-lg bg-panel-2 border border-border flex items-center justify-center flex-shrink-0">
                    <FolderSearch size={15} className="text-muted group-hover:text-accent transition-colors" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-medium text-foreground group-hover:text-accent transition-colors truncate">{inv.title}</h3>
                      <span className={clsx('text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1', STATUS_STYLES[statusKey] || STATUS_STYLES.open)}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
                        {inv.status.replace('_', ' ')}
                      </span>
                    </div>
                    {inv.description && (
                      <p className="text-xs text-muted mt-0.5 truncate">{inv.description}</p>
                    )}
                    <p className="text-[10px] text-subtle mt-1">{format(new Date(inv.created_at), 'MMM d, yyyy · HH:mm')}</p>
                  </div>

                  <ChevronRight size={14} className="text-subtle group-hover:text-muted transition-colors flex-shrink-0" />
                </Link>

                <button
                  onClick={e => { e.preventDefault(); setConfirmDelete(inv.id) }}
                  title="Delete investigation"
                  className="absolute right-12 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-subtle hover:text-danger hover:bg-danger/10 opacity-0 group-hover:opacity-100 transition-all"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Delete confirm dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-panel border border-border rounded-xl p-5 w-80 shadow-2xl">
            <h3 className="text-sm font-semibold text-foreground mb-1">Delete investigation?</h3>
            <p className="text-xs text-muted mb-4">This will permanently delete the investigation, all evidence files, events, notes and flags. This cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-3 py-1.5 text-xs text-muted hover:text-foreground bg-panel-2 border border-border rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => remove.mutate(confirmDelete)}
                disabled={remove.isPending}
                className="px-3 py-1.5 text-xs text-white bg-danger hover:bg-danger/80 disabled:opacity-50 rounded-md transition-colors"
              >
                {remove.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
