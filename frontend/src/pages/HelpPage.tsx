import { ChevronDown, BookOpen, MessageCircle, FileText, ExternalLink, Search } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

const FAQS = [
  {
    q: 'How do I create a new investigation?',
    a: 'Go to the Investigations page and click "New Investigation". Fill in the title, severity, and optional description. You can add evidence and link entities after creation.',
  },
  {
    q: 'How is confidence score calculated?',
    a: 'Confidence is derived from the number of corroborating evidence items, their source reliability, and cross-entity link strength. It updates automatically as new evidence is added.',
  },
  {
    q: 'Can I export investigation data?',
    a: 'Yes. Open any investigation and use the Export panel (top-right of the detail view). Supported formats are JSON, CSV, and PDF report.',
  },
  {
    q: 'How do GitHub Issues sync?',
    a: 'Connect a GitHub token in Settings → API Keys. Blackbox polls your configured repositories every 15 minutes and surfaces issues matching your entity keywords.',
  },
  {
    q: 'What does "stalled" mean for an investigation?',
    a: 'An investigation is marked stalled when no evidence has been added and no status change has occurred for 7 consecutive days. You can override this in the investigation detail.',
  },
]

const DOCS = [
  { title: 'Getting started guide', description: 'Set up your first investigation end-to-end', icon: BookOpen },
  { title: 'Evidence library reference', description: 'Supported evidence types, formats and metadata', icon: FileText },
  { title: 'API documentation', description: 'REST API reference and authentication', icon: FileText },
  { title: 'Contact support', description: 'Open a ticket or chat with the team', icon: MessageCircle },
]

export default function HelpPage() {
  const [search, setSearch] = useState('')
  const [openFaq, setOpenFaq] = useState<number | null>(null)

  const filtered = FAQS.filter(f =>
    f.q.toLowerCase().includes(search.toLowerCase()) ||
    f.a.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="text-sm font-semibold text-foreground mb-1">Help & Documentation</h1>
      <p className="text-xs text-muted mb-6">Find answers, guides, and support resources</p>

      <div className="grid grid-cols-2 gap-3 mb-8">
        {DOCS.map(d => (
          <button
            key={d.title}
            className="flex items-start gap-3 p-4 bg-panel border border-border rounded-lg hover:border-accent/40 hover:bg-accent/5 transition-colors text-left group"
          >
            <d.icon size={16} className="text-muted group-hover:text-accent mt-0.5 flex-shrink-0 transition-colors" />
            <div>
              <p className="text-xs font-medium text-foreground flex items-center gap-1.5">
                {d.title}
                <ExternalLink size={10} className="text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
              </p>
              <p className="text-[11px] text-muted mt-0.5">{d.description}</p>
            </div>
          </button>
        ))}
      </div>

      <div className="mb-4">
        <h2 className="text-xs font-semibold text-foreground">Frequently asked questions</h2>
      </div>

      <div className="relative mb-4">
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search questions..."
          className="w-full bg-surface border border-border rounded-md pl-8 pr-4 py-2 text-xs text-foreground placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
        />
      </div>

      <div className="space-y-1">
        {filtered.length === 0 && (
          <p className="text-xs text-muted py-4 text-center">No results for "{search}"</p>
        )}
        {filtered.map((faq, i) => (
          <div key={i} className="border border-border rounded-lg overflow-hidden">
            <button
              onClick={() => setOpenFaq(openFaq === i ? null : i)}
              className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-black/5 transition-colors"
            >
              <span className="text-xs font-medium text-foreground">{faq.q}</span>
              <ChevronDown size={13} className={clsx('text-muted flex-shrink-0 transition-transform', openFaq === i && 'rotate-180')} />
            </button>
            {openFaq === i && (
              <div className="px-4 pb-4 text-xs text-muted border-t border-border pt-3">
                {faq.a}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
