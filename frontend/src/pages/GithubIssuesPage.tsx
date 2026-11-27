import { useState, useEffect, useRef } from 'react'
import { Github, Search, Loader2, ChevronDown, ChevronUp, Sparkles, ExternalLink, AlertCircle, Tag, MessageSquare, KeyRound, Star, X } from 'lucide-react'
import { api } from '../services/api'
import clsx from 'clsx'

interface GithubIssue {
  number: number
  title: string
  body: string
  state: string
  html_url: string
  user: string | null
  created_at: string
  labels: string[]
  comments: number
}

interface FetchResult {
  repo: string
  issues: GithubIssue[]
}

interface RepoResult {
  full_name: string
  description: string
  html_url: string
  stars: number
  language: string
  open_issues: number
}

function formatStars(n: number) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export default function GithubIssuesPage() {
  const [repoUrl, setRepoUrl] = useState('')
  const [githubToken, setGithubToken] = useState('')
  const [anthropicKey, setAnthropicKey] = useState('')
  const [showSettings, setShowSettings] = useState(false)

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<RepoResult[]>([])
  const [searching, setSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<FetchResult | null>(null)

  const [expandedIssue, setExpandedIssue] = useState<number | null>(null)
  const [analyzing, setAnalyzing] = useState<number | null>(null)
  const [solutions, setSolutions] = useState<Record<number, string>>({})
  const [analyzeError, setAnalyzeError] = useState<Record<number, string>>({})

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!searchQuery.trim()) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const params = new URLSearchParams({ q: searchQuery.trim() })
        if (githubToken.trim()) params.append('github_token', githubToken.trim())
        const res = await api.get(`/github-issues/search?${params}`)
        setSearchResults(res.data.repos)
        setShowDropdown(true)
      } catch {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 400)
  }, [searchQuery, githubToken])

  function pickRepo(repo: RepoResult) {
    setRepoUrl(repo.html_url)
    setSearchQuery(repo.full_name)
    setShowDropdown(false)
  }

  function clearSearch() {
    setSearchQuery('')
    setRepoUrl('')
    setSearchResults([])
    setShowDropdown(false)
    setResult(null)
    setSolutions({})
  }

  async function handleFetch() {
    if (!repoUrl.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setSolutions({})
    setExpandedIssue(null)
    try {
      const res = await api.post('/github-issues/fetch', {
        repo_url: repoUrl.trim(),
        github_token: githubToken.trim() || undefined,
      })
      setResult(res.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to fetch issues.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function handleAnalyze(issue: GithubIssue) {
    if (!result) return
    setAnalyzing(issue.number)
    setAnalyzeError(prev => ({ ...prev, [issue.number]: '' }))
    try {
      const res = await api.post('/github-issues/analyze', {
        issue_number: issue.number,
        issue_title: issue.title,
        issue_body: issue.body,
        repo: result.repo,
        anthropic_key: anthropicKey.trim() || undefined,
      })
      setSolutions(prev => ({ ...prev, [issue.number]: res.data.solution }))
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Analysis failed.'
      setAnalyzeError(prev => ({ ...prev, [issue.number]: msg }))
    } finally {
      setAnalyzing(null)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-bold text-foreground flex items-center gap-2">
            <Github size={18} />
            GitHub Issue Analyzer
          </h1>
          <p className="text-xs text-muted mt-0.5">Search OSS repos, fetch open issues, and get AI-generated solutions</p>
        </div>
      </div>

      {/* Config tile */}
      <div className="bg-panel border border-border rounded-xl p-5 mb-5">
        {/* Repo search */}
        <div className="mb-3" ref={searchRef}>
          <label className="block text-[10px] text-muted mb-1.5 font-medium uppercase tracking-wider">Search OSS repositories</label>
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none" />
            <input
              className="w-full bg-surface border border-border rounded-lg pl-8 pr-8 py-2 text-xs text-foreground focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
              placeholder="Search by name, topic, or description…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
            />
            {searching && (
              <Loader2 size={12} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted animate-spin" />
            )}
            {!searching && searchQuery && (
              <button onClick={clearSearch} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-foreground transition-colors">
                <X size={12} />
              </button>
            )}

            {showDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-panel border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
                {searchResults.map(repo => (
                  <button
                    key={repo.full_name}
                    onClick={() => pickRepo(repo)}
                    className="w-full flex items-start gap-3 px-4 py-3 hover:bg-black/5 transition-colors text-left border-b border-border last:border-b-0"
                  >
                    <Github size={13} className="text-muted mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium text-foreground">{repo.full_name}</span>
                        {repo.language && (
                          <span className="text-[10px] text-muted">{repo.language}</span>
                        )}
                        <span className="flex items-center gap-0.5 text-[10px] text-warning ml-auto flex-shrink-0">
                          <Star size={9} />
                          {formatStars(repo.stars)}
                        </span>
                      </div>
                      {repo.description && (
                        <p className="text-[11px] text-muted mt-0.5 truncate">{repo.description}</p>
                      )}
                      <p className="text-[10px] text-subtle mt-0.5">
                        {repo.open_issues} open issue{repo.open_issues !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Repo URL + fetch */}
        <div className="flex gap-2 mb-3">
          <div className="relative flex-1">
            <Github size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              className="w-full bg-surface border border-border rounded-lg pl-8 pr-3 py-2 text-xs text-foreground focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
              placeholder="https://github.com/owner/repo  or  owner/repo"
              value={repoUrl}
              onChange={e => setRepoUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleFetch()}
            />
          </div>
          <button
            onClick={handleFetch}
            disabled={!repoUrl.trim() || loading}
            className="flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent-2 disabled:opacity-50 rounded-lg text-xs font-medium text-white transition-colors"
          >
            {loading ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
            {loading ? 'Fetching…' : 'Fetch Issues'}
          </button>
        </div>

        {/* Optional settings toggle */}
        <button
          onClick={() => setShowSettings(s => !s)}
          className="flex items-center gap-1 text-[11px] text-muted hover:text-foreground transition-colors"
        >
          <KeyRound size={11} />
          API keys &amp; tokens (optional)
          {showSettings ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>

        {showSettings && (
          <div className="mt-3 grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] text-muted mb-1">GitHub Token (for private repos / higher rate limit)</label>
              <input
                type="password"
                className="w-full bg-surface border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
                placeholder="ghp_…"
                value={githubToken}
                onChange={e => setGithubToken(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-[10px] text-muted mb-1">Anthropic API Key (for AI solutions)</label>
              <input
                type="password"
                className="w-full bg-surface border border-border rounded-lg px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent/50 placeholder-muted transition-colors"
                placeholder="sk-ant-…"
                value={anthropicKey}
                onChange={e => setAnthropicKey(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 bg-danger/10 border border-danger/30 rounded-xl px-4 py-3 mb-4 text-xs text-danger">
          <AlertCircle size={13} />
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-muted">
              <span className="text-foreground font-medium">{result.issues.length}</span> open issue{result.issues.length !== 1 ? 's' : ''} in{' '}
              <span className="text-accent">{result.repo}</span>
            </p>
          </div>

          {result.issues.length === 0 ? (
            <div className="text-center py-16 text-muted">
              <Github size={28} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No open issues found.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {result.issues.map(issue => {
                const isExpanded = expandedIssue === issue.number
                const solution = solutions[issue.number]
                const isAnalyzing = analyzing === issue.number
                const err = analyzeError[issue.number]

                return (
                  <div
                    key={issue.number}
                    className="bg-panel border border-border hover:border-border-2 rounded-xl transition-colors"
                  >
                    <button
                      onClick={() => setExpandedIssue(isExpanded ? null : issue.number)}
                      className="w-full flex items-start gap-3 px-5 py-4 text-left"
                    >
                      <div className="w-8 h-8 rounded-md bg-panel-2 border border-border flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-[10px] font-mono text-muted">#{issue.number}</span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{issue.title}</p>
                        <div className="flex items-center gap-3 mt-1 flex-wrap">
                          {issue.user && <span className="text-[10px] text-muted">by {issue.user}</span>}
                          {issue.comments > 0 && (
                            <span className="flex items-center gap-0.5 text-[10px] text-muted">
                              <MessageSquare size={9} />
                              {issue.comments}
                            </span>
                          )}
                          {issue.labels.map(l => (
                            <span key={l} className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent border border-accent/20">
                              <Tag size={8} />
                              {l}
                            </span>
                          ))}
                          {solution && (
                            <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-success/10 text-success border border-success/20">
                              <Sparkles size={8} />
                              solved
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                        <a
                          href={issue.html_url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="p-1 text-muted hover:text-foreground transition-colors"
                        >
                          <ExternalLink size={12} />
                        </a>
                        {isExpanded ? <ChevronUp size={14} className="text-muted" /> : <ChevronDown size={14} className="text-muted" />}
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="px-5 pb-5 border-t border-border">
                        {issue.body && (
                          <div className="mt-4 mb-4">
                            <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2">Issue description</p>
                            <div className="bg-surface border border-border rounded-lg px-4 py-3 text-xs text-muted whitespace-pre-wrap max-h-48 overflow-y-auto">
                              {issue.body}
                            </div>
                          </div>
                        )}

                        {!solution && (
                          <button
                            onClick={() => handleAnalyze(issue)}
                            disabled={isAnalyzing}
                            className={clsx(
                              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors',
                              isAnalyzing
                                ? 'bg-panel-2 text-muted cursor-not-allowed'
                                : 'bg-accent/10 hover:bg-accent/20 text-accent border border-accent/20'
                            )}
                          >
                            {isAnalyzing
                              ? <><Loader2 size={12} className="animate-spin" /> Analyzing…</>
                              : <><Sparkles size={12} /> Generate AI Solution</>
                            }
                          </button>
                        )}

                        {err && (
                          <div className="flex items-center gap-2 mt-3 text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
                            <AlertCircle size={12} />
                            {err}
                          </div>
                        )}

                        {solution && (
                          <div className="mt-4">
                            <p className="text-[10px] font-semibold text-muted uppercase tracking-wider mb-2 flex items-center gap-1">
                              <Sparkles size={10} className="text-accent" />
                              AI-Generated Solution
                            </p>
                            <div className="bg-surface border border-accent/20 rounded-lg px-4 py-3 text-xs text-foreground whitespace-pre-wrap leading-relaxed">
                              {solution}
                            </div>
                            <button
                              onClick={() => handleAnalyze(issue)}
                              disabled={isAnalyzing}
                              className="mt-2 flex items-center gap-1 text-[10px] text-muted hover:text-foreground transition-colors"
                            >
                              {isAnalyzing ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
                              Regenerate
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
        </>
      )}
    </div>
  )
}
