import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Github, Loader2, RefreshCw, CheckCircle, AlertCircle, ExternalLink, Link2, Pencil } from 'lucide-react'
import axios from 'axios'
import { api } from '../services/api'

type LinkState = {
  linked: boolean
  repo_full_name?: string
  html_url?: string
  last_synced_at?: string | null
}

type SyncResult = {
  synced: boolean
  events_ingested: number
  evidence_id: string
  last_synced_at: string | null
}

function errMessage(e: unknown, fallback: string): string {
  if (axios.isAxiosError(e)) {
    const detail = e.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

function formatTime(iso?: string | null): string {
  if (!iso) return 'never'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return 'never'
  return d.toLocaleString()
}

export default function ConnectedRepoPanel({ investigationId }: { investigationId: string }) {
  const qc = useQueryClient()
  const [repoUrl, setRepoUrl] = useState('')
  const [editing, setEditing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)

  const { data: link, isLoading } = useQuery<LinkState>({
    queryKey: ['linked-repo', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/github`).then(r => r.data),
  })

  const linkRepo = useMutation({
    mutationFn: (url: string) =>
      api.post(`/investigations/${investigationId}/github/link`, { repo_url: url }).then(r => r.data),
    onSuccess: () => {
      setRepoUrl('')
      setEditing(false)
      setSyncResult(null)
      qc.invalidateQueries({ queryKey: ['linked-repo', investigationId] })
    },
  })

  const sync = useMutation({
    mutationFn: () =>
      api.post(`/investigations/${investigationId}/github/sync`).then(r => r.data as SyncResult),
    onSuccess: (data) => {
      setSyncResult(data)
      // Synced activity lands as a new evidence file and timeline events.
      qc.invalidateQueries({ queryKey: ['linked-repo', investigationId] })
      qc.invalidateQueries({ queryKey: ['evidence', investigationId] })
      qc.invalidateQueries({ queryKey: ['timeline', investigationId] })
      qc.invalidateQueries({ queryKey: ['confidence', investigationId] })
    },
  })

  const submitLink = (e: React.FormEvent) => {
    e.preventDefault()
    const url = repoUrl.trim()
    if (url) linkRepo.mutate(url)
  }

  if (isLoading) {
    return (
      <div className="bg-panel border border-border rounded-xl p-4 flex justify-center">
        <Loader2 size={16} className="animate-spin text-muted" />
      </div>
    )
  }

  const isLinked = !!link?.linked
  const showForm = !isLinked || editing

  return (
    <div className="bg-panel border border-border rounded-xl p-4 max-w-2xl">
      <div className="flex items-center gap-2 mb-1">
        <Github size={15} className="text-foreground" />
        <h2 className="text-sm font-semibold text-foreground">Connected Repository</h2>
      </div>
      <p className="text-xs text-muted mb-4">
        Link a GitHub repository to this environment, then <span className="font-medium">Sync now</span> to
        ingest recent commits &amp; issues as hashed evidence — normalized, secret-scanned and placed on the timeline
        like any uploaded file. Sync is manual; nothing runs on a schedule.
      </p>

      {showForm ? (
        <form onSubmit={submitLink} className="space-y-2">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 focus-within:border-accent/50 transition-colors">
            <Github size={14} className="text-muted flex-shrink-0" />
            <input
              autoFocus={editing}
              value={repoUrl}
              onChange={e => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo  or  owner/repo"
              className="flex-1 bg-transparent text-xs text-foreground placeholder:text-subtle outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={!repoUrl.trim() || linkRepo.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-2 disabled:opacity-50 rounded-md text-xs font-medium text-white transition-colors"
            >
              {linkRepo.isPending ? <Loader2 size={13} className="animate-spin" /> : <Link2 size={13} />}
              {isLinked ? 'Update link' : 'Link repository'}
            </button>
            {editing && (
              <button
                type="button"
                onClick={() => { setEditing(false); setRepoUrl('') }}
                className="px-3 py-1.5 text-xs text-muted hover:text-foreground bg-panel-2 border border-border rounded-md transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
          {linkRepo.isError && (
            <p className="flex items-center gap-1.5 text-xs text-danger">
              <AlertCircle size={13} />
              {errMessage(linkRepo.error, 'Could not link that repository.')}
            </p>
          )}
        </form>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 p-3 bg-surface border border-border rounded-lg">
            <div className="min-w-0">
              <a
                href={link!.html_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-sm font-medium text-foreground hover:text-accent transition-colors truncate"
              >
                {link!.repo_full_name}
                <ExternalLink size={12} className="flex-shrink-0 text-muted" />
              </a>
              <p className="text-xs text-muted mt-0.5">Last synced: {formatTime(link!.last_synced_at)}</p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => { setEditing(true); setRepoUrl(link!.repo_full_name || '') }}
                title="Change repository"
                className="p-1.5 text-muted hover:text-foreground border border-border rounded-md transition-colors"
              >
                <Pencil size={13} />
              </button>
              <button
                onClick={() => sync.mutate()}
                disabled={sync.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-2 disabled:opacity-50 rounded-md text-xs font-medium text-white transition-colors"
              >
                {sync.isPending
                  ? <><Loader2 size={13} className="animate-spin" /> Syncing…</>
                  : <><RefreshCw size={13} /> Sync now</>}
              </button>
            </div>
          </div>

          {sync.isError && (
            <p className="flex items-center gap-1.5 text-xs text-danger">
              <AlertCircle size={13} />
              {errMessage(sync.error, 'Sync failed. Check the repo name / GITHUB_TOKEN.')}
            </p>
          )}
          {syncResult && !sync.isError && (
            <p className="flex items-center gap-1.5 text-xs text-success">
              <CheckCircle size={13} />
              Synced {syncResult.events_ingested} event{syncResult.events_ingested !== 1 ? 's' : ''} into evidence &amp; timeline.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
