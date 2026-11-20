import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, FolderOpen, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import type { Investigation } from '../services/types'
import { format } from 'date-fns'

export default function InvestigationsPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

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

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Investigations</h1>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent/80 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} />
          New Investigation
        </button>
      </div>

      {showForm && (
        <div className="bg-panel border border-border rounded-xl p-5 mb-6">
          <h2 className="text-sm font-semibold mb-4 text-gray-300">New Investigation</h2>
          <input
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:border-accent"
            placeholder="Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <textarea
            className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm mb-3 resize-none focus:outline-none focus:border-accent"
            placeholder="Description (optional)"
            rows={2}
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              onClick={() => create.mutate({ title, description })}
              disabled={!title || create.isPending}
              className="px-4 py-2 bg-accent hover:bg-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
            >
              {create.isPending ? 'Creating…' : 'Create'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-gray-500" /></div>
      ) : investigations?.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <FolderOpen size={40} className="mx-auto mb-3 opacity-40" />
          <p>No investigations yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {investigations?.map(inv => (
            <Link
              key={inv.id}
              to={`/investigations/${inv.id}`}
              className="block bg-panel border border-border hover:border-accent/50 rounded-xl p-4 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-white">{inv.title}</h3>
                  {inv.description && <p className="text-sm text-gray-400 mt-0.5">{inv.description}</p>}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  inv.status === 'open' ? 'bg-success/20 text-success' : 'bg-gray-500/20 text-gray-400'
                }`}>
                  {inv.status}
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-2">{format(new Date(inv.created_at), 'MMM d, yyyy HH:mm')}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
