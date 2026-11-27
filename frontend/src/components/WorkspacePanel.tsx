import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { StickyNote, Plus, Trash2, Loader2, Pencil, Check, X } from 'lucide-react'
import { api } from '../services/api'
import { format } from 'date-fns'

interface Note {
  id: string
  content: string
  author: string | null
  event_id: string | null
  created_at: string
}

export default function WorkspacePanel({ investigationId }: { investigationId: string }) {
  const qc = useQueryClient()
  const [draft, setDraft] = useState('')
  const [editId, setEditId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const { data: notes = [], isLoading } = useQuery<Note[]>({
    queryKey: ['notes', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/notes`).then(r => r.data),
  })

  const add = useMutation({
    mutationFn: (content: string) =>
      api.post(`/investigations/${investigationId}/notes`, { content }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notes', investigationId] })
      setDraft('')
    },
  })

  const update = useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      api.patch(`/investigations/${investigationId}/notes/${id}`, { content }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notes', investigationId] })
      setEditId(null)
    },
  })

  const remove = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/investigations/${investigationId}/notes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notes', investigationId] }),
  })

  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <h2 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
        <StickyNote size={14} />
        Investigation Notes
      </h2>

      <div className="mb-4">
        <textarea
          value={draft}
          onChange={e => setDraft(e.target.value)}
          placeholder="Add a note…"
          rows={2}
          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-foreground resize-none focus:outline-none focus:border-accent/50 placeholder:text-muted transition-colors"
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && draft.trim()) {
              add.mutate(draft.trim())
            }
          }}
        />
        <div className="flex justify-end mt-1.5">
          <button
            onClick={() => draft.trim() && add.mutate(draft.trim())}
            disabled={!draft.trim() || add.isPending}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-accent text-white hover:bg-accent/80 disabled:opacity-40 rounded-lg transition-colors"
          >
            <Plus size={12} />
            {add.isPending ? 'Adding…' : 'Add note'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4"><Loader2 size={16} className="animate-spin text-muted" /></div>
      ) : notes.length === 0 ? (
        <p className="text-xs text-subtle text-center py-4">No notes yet</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
          {notes.map(note => (
            <div key={note.id} className="group bg-surface rounded-lg p-3 border border-border">
              {editId === note.id ? (
                <div>
                  <textarea
                    value={editContent}
                    onChange={e => setEditContent(e.target.value)}
                    rows={3}
                    autoFocus
                    className="w-full bg-panel border border-accent/50 rounded px-2 py-1.5 text-sm text-foreground resize-none focus:outline-none focus:border-accent transition-colors"
                  />
                  <div className="flex gap-1.5 mt-1.5 justify-end">
                    <button
                      onClick={() => update.mutate({ id: note.id, content: editContent })}
                      disabled={!editContent.trim()}
                      className="p-1 text-success hover:text-success/70 transition-colors"
                    ><Check size={13} /></button>
                    <button onClick={() => setEditId(null)} className="p-1 text-muted hover:text-foreground transition-colors">
                      <X size={13} />
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-foreground whitespace-pre-wrap break-words">{note.content}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-muted">
                      {format(new Date(note.created_at), 'MMM d, HH:mm')}
                    </span>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => { setEditId(note.id); setEditContent(note.content) }}
                        className="p-1 text-muted hover:text-foreground transition-colors"
                      ><Pencil size={12} /></button>
                      <button
                        onClick={() => remove.mutate(note.id)}
                        className="p-1 text-muted hover:text-danger transition-colors"
                      ><Trash2 size={12} /></button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
