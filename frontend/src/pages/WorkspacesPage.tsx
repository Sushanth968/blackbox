import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Layers, StickyNote, Flag, FileText, Search, ChevronRight,
  Loader2, Plus, Trash2, CheckCircle, Clock, AlertCircle
} from 'lucide-react'
import { api } from '../services/api'
import { format } from 'date-fns'
import clsx from 'clsx'

interface WorkspaceNote {
  id: string
  content: string
  author: string | null
  created_at: string | null
}

interface Workspace {
  id: string
  title: string
  description: string | null
  status: string
  created_at: string | null
  updated_at: string | null
  note_count: number
  flag_count: number
  evidence_count: number
  notes: WorkspaceNote[]
}

const STATUS_PILL: Record<string, string> = {
  open:      'bg-success/15 text-success border-success/30',
  in_review: 'bg-warning/15 text-warning border-warning/30',
  closed:    'bg-muted/10 text-muted border-muted/20',
}

export default function WorkspacesPage() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [addingNoteFor, setAddingNoteFor] = useState<string | null>(null)
  const [noteContent, setNoteContent] = useState('')
  const [noteAuthor, setNoteAuthor] = useState('KR')

  const { data: workspaces = [], isLoading } = useQuery<Workspace[]>({
    queryKey: ['workspaces'],
    queryFn: () => api.get('/workspaces').then(r => r.data),
    refetchInterval: 10000,
  })

  const addNote = useMutation({
    mutationFn: ({ invId, content, author }: { invId: string; content: string; author: string }) =>
      api.post(`/investigations/${invId}/notes`, { content, author }).then(r => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['workspaces'] })
      qc.invalidateQueries({ queryKey: ['notes', vars.invId] })
      setAddingNoteFor(null)
      setNoteContent('')
    },
  })

  const deleteNote = useMutation({
    mutationFn: ({ invId, noteId }: { invId: string; noteId: string }) =>
      api.delete(`/investigations/${invId}/notes/${noteId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })

  const toggle = (id: string) => setExpanded(prev => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  const filtered = workspaces.filter(w => {
    if (!search) return true
    const q = search.toLowerCase()
    return w.title.toLowerCase().includes(q) || (w.description ?? '').toLowerCase().includes(q)
  })

  const totalNotes = workspaces.reduce((a, w) => a + w.note_count, 0)
  const totalFlags = workspaces.reduce((a, w) => a + w.flag_count, 0)

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers size={18} className="text-accent" />
            Workspaces
          </h1>
          <p className="text-xs text-muted mt-0.5">Notes and annotations across all investigations</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-2.5 py-1 rounded-md bg-panel-2 border border-border text-muted">
            {workspaces.length} investigation{workspaces.length !== 1 ? 's' : ''}
          </span>
          <span className="text-[10px] px-2.5 py-1 rounded-md bg-accent/10 border border-accent/20 text-accent">
            {totalNotes} note{totalNotes !== 1 ? 's' : ''}
          </span>
          {totalFlags > 0 && (
            <span className="text-[10px] px-2.5 py-1 rounded-md bg-warning/10 border border-warning/20 text-warning">
              {totalFlags} flag{totalFlags !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-5 max-w-sm">
        <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search investigations..."
          className="w-full bg-panel border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-white placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={20} className="animate-spin text-muted" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-muted">
          <div className="w-12 h-12 rounded-full bg-panel border border-border flex items-center justify-center mx-auto mb-4">
            <Layers size={20} className="opacity-40" />
          </div>
          <p className="text-sm">{workspaces.length === 0 ? 'No investigations yet' : 'No results'}</p>
          {workspaces.length === 0 && (
            <p className="text-xs mt-1 text-subtle">
              <Link to="/investigations" className="text-accent hover:underline">Create an investigation</Link> to start adding notes
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(w => {
            const isOpen = expanded.has(w.id)
            return (
              <div key={w.id} className="bg-panel border border-border rounded-xl overflow-hidden">
                {/* Row header */}
                <button
                  onClick={() => toggle(w.id)}
                  className="w-full flex items-center gap-3 px-5 py-4 hover:bg-white/3 transition-colors text-left"
                >
                  <ChevronRight
                    size={13}
                    className={clsx('text-muted transition-transform flex-shrink-0', isOpen && 'rotate-90')}
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium text-white truncate">{w.title}</span>
                      <span className={clsx(
                        'text-[10px] px-2 py-0.5 rounded-full border font-medium',
                        STATUS_PILL[w.status] ?? STATUS_PILL.open
                      )}>
                        {w.status.replace('_', ' ')}
                      </span>
                    </div>
                    {w.description && (
                      <p className="text-xs text-muted mt-0.5 truncate">{w.description}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <Stat icon={<StickyNote size={11} />} count={w.note_count} label="notes" />
                    <Stat icon={<Flag size={11} />} count={w.flag_count} label="flags" />
                    <Stat icon={<FileText size={11} />} count={w.evidence_count} label="files" />
                    <Link
                      to={`/investigations/${w.id}`}
                      onClick={e => e.stopPropagation()}
                      className="text-[10px] text-muted hover:text-accent transition-colors ml-1"
                    >
                      Open →
                    </Link>
                  </div>
                </button>

                {/* Expanded notes area */}
                {isOpen && (
                  <div className="border-t border-border bg-surface">
                    {w.notes.length === 0 && addingNoteFor !== w.id ? (
                      <div className="px-5 py-6 text-center text-xs text-muted">
                        No notes yet.{' '}
                        <button
                          onClick={() => setAddingNoteFor(w.id)}
                          className="text-accent hover:underline"
                        >
                          Add one
                        </button>
                      </div>
                    ) : (
                      <div className="divide-y divide-border/50">
                        {w.notes.map(note => (
                          <div key={note.id} className="flex items-start gap-3 px-5 py-3 group hover:bg-white/2">
                            <div className="w-5 h-5 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                              <span className="text-[9px] font-bold text-accent">
                                {(note.author ?? 'U').slice(0, 2).toUpperCase()}
                              </span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-white/90 whitespace-pre-wrap">{note.content}</p>
                              <p className="text-[10px] text-subtle mt-1">
                                {note.author ?? 'Unknown'} ·{' '}
                                {note.created_at ? format(new Date(note.created_at), 'MMM d, HH:mm') : '—'}
                              </p>
                            </div>
                            <button
                              onClick={() => deleteNote.mutate({ invId: w.id, noteId: note.id })}
                              className="p-1 rounded text-subtle hover:text-danger opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                              title="Delete note"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {addingNoteFor === w.id ? (
                      <div className="px-5 py-4 border-t border-border/50 bg-panel-2">
                        <textarea
                          autoFocus
                          value={noteContent}
                          onChange={e => setNoteContent(e.target.value)}
                          placeholder="Write a note..."
                          rows={3}
                          className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-xs text-white mb-2 resize-none focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
                        />
                        <div className="flex items-center gap-2">
                          <input
                            value={noteAuthor}
                            onChange={e => setNoteAuthor(e.target.value)}
                            placeholder="Author"
                            className="w-24 bg-surface border border-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
                          />
                          <button
                            onClick={() => addNote.mutate({ invId: w.id, content: noteContent, author: noteAuthor })}
                            disabled={!noteContent.trim() || addNote.isPending}
                            className="px-3 py-1.5 bg-accent hover:bg-accent-2 disabled:opacity-50 rounded-md text-xs font-medium text-white transition-colors flex items-center gap-1"
                          >
                            {addNote.isPending ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />}
                            Save note
                          </button>
                          <button
                            onClick={() => { setAddingNoteFor(null); setNoteContent('') }}
                            className="px-3 py-1.5 bg-transparent border border-border rounded-md text-xs text-muted hover:text-white transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="px-5 py-3 border-t border-border/50">
                        <button
                          onClick={() => setAddingNoteFor(w.id)}
                          className="flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors"
                        >
                          <Plus size={12} />
                          Add note
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Stat({ icon, count, label }: { icon: React.ReactNode; count: number; label: string }) {
  return (
    <div className="flex items-center gap-1 text-[10px] text-muted">
      {icon}
      <span className={count > 0 ? 'text-white/70' : ''}>{count}</span>
      <span className="hidden sm:inline">{label}</span>
    </div>
  )
}
