import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Network, RefreshCw, Loader2, User, Globe, FileText, Hash, Mail } from 'lucide-react'
import { api } from '../services/api'
import type { GraphData, Entity } from '../services/types'
import { useMemo, useState } from 'react'
import clsx from 'clsx'

const TYPE_ICON: Record<string, React.ReactNode> = {
  user:  <User size={11} />,
  ip:    <Globe size={11} />,
  email: <Mail size={11} />,
  path:  <FileText size={11} />,
  url:   <Globe size={11} />,
  hash:  <Hash size={11} />,
}

const TYPE_COLOR: Record<string, string> = {
  user:  '#6366f1',
  ip:    '#f59e0b',
  email: '#10b981',
  path:  '#3b82f6',
  url:   '#8b5cf6',
  hash:  '#6b7280',
}

function useLayout(nodes: Entity[], edges: { source: string; target: string }[], width: number, height: number) {
  return useMemo(() => {
    if (!nodes.length) return { positions: {}, links: [] }

    const positions: Record<string, { x: number; y: number }> = {}
    const cx = width / 2, cy = height / 2
    const r = Math.min(width, height) * 0.38

    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2
      positions[n.id] = {
        x: cx + r * Math.cos(angle),
        y: cy + r * Math.sin(angle),
      }
    })

    for (let iter = 0; iter < 30; iter++) {
      const forces: Record<string, { fx: number; fy: number }> = {}
      nodes.forEach(n => { forces[n.id] = { fx: 0, fy: 0 } })

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = positions[nodes[i].id], b = positions[nodes[j].id]
          const dx = a.x - b.x, dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 1200 / (dist * dist)
          forces[nodes[i].id].fx += (dx / dist) * force
          forces[nodes[i].id].fy += (dy / dist) * force
          forces[nodes[j].id].fx -= (dx / dist) * force
          forces[nodes[j].id].fy -= (dy / dist) * force
        }
      }

      edges.forEach(e => {
        const a = positions[e.source], b = positions[e.target]
        if (!a || !b) return
        const dx = b.x - a.x, dy = b.y - a.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = dist / 300
        forces[e.source].fx += (dx / dist) * force * dist
        forces[e.source].fy += (dy / dist) * force * dist
        forces[e.target].fx -= (dx / dist) * force * dist
        forces[e.target].fy -= (dy / dist) * force * dist
      })

      nodes.forEach(n => {
        const p = positions[n.id]
        forces[n.id].fx += (cx - p.x) * 0.01
        forces[n.id].fy += (cy - p.y) * 0.01
      })

      nodes.forEach(n => {
        const p = positions[n.id]
        const f = forces[n.id]
        p.x = Math.max(32, Math.min(width - 32, p.x + f.fx * 0.3))
        p.y = Math.max(20, Math.min(height - 20, p.y + f.fy * 0.3))
      })
    }

    const links = edges.map(e => ({
      ...e,
      x1: positions[e.source]?.x ?? 0,
      y1: positions[e.source]?.y ?? 0,
      x2: positions[e.target]?.x ?? 0,
      y2: positions[e.target]?.y ?? 0,
    }))

    return { positions, links }
  }, [nodes, edges, width, height])
}

export default function EntityGraph({ investigationId }: { investigationId: string }) {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string | null>(null)

  const { data: graph, isLoading } = useQuery<GraphData>({
    queryKey: ['graph', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/graph`).then(r => r.data),
  })

  const resolve = useMutation({
    mutationFn: () => api.post(`/investigations/${investigationId}/entities/resolve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['graph', investigationId] }),
  })

  const W = 640, H = 380

  const dedupEdges = useMemo(() => {
    if (!graph) return []
    const seen = new Set<string>()
    return graph.edges.filter(e => {
      const key = [e.source_entity_id, e.target_entity_id].sort().join('|')
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }).map(e => ({ source: e.source_entity_id, target: e.target_entity_id, relation: e.relation }))
  }, [graph])

  const { positions, links } = useLayout(graph?.nodes || [], dedupEdges, W, H)

  const selectedNode = graph?.nodes.find(n => n.id === selected)
  const connectedEdges = graph?.edges.filter(
    e => e.source_entity_id === selected || e.target_entity_id === selected
  ) || []

  if (isLoading) return (
    <div className="bg-panel border border-border rounded-xl p-4 flex justify-center py-12">
      <Loader2 size={20} className="animate-spin text-gray-500" />
    </div>
  )

  return (
    <div className="bg-panel border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
          <Network size={14} />
          Entity Graph
        </h2>
        <div className="flex items-center gap-2">
          {graph && (
            <span className="text-xs text-gray-500">
              {graph.nodes.length} nodes · {graph.edges.length} edges
            </span>
          )}
          <button
            onClick={() => resolve.mutate()}
            disabled={resolve.isPending}
            title="Re-resolve entities from events"
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-border rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={resolve.isPending ? 'animate-spin' : ''} />
            Resolve
          </button>
        </div>
      </div>

      {!graph || graph.nodes.length === 0 ? (
        <div className="text-center py-10 text-gray-600 text-sm">
          <Network size={32} className="mx-auto mb-2 opacity-30" />
          <p>No entities yet.</p>
          <p className="text-xs mt-1">Click Resolve after uploading evidence files.</p>
        </div>
      ) : (
        <div className="flex gap-4">
          <svg
            width={W} height={H}
            className="flex-shrink-0 rounded-lg bg-surface border border-border overflow-visible"
            style={{ maxWidth: '100%' }}
          >
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="#374151" />
              </marker>
            </defs>

            {links.map((l, i) => (
              <line
                key={i}
                x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
                stroke="#374151"
                strokeWidth={1.5}
                strokeOpacity={0.6}
                markerEnd="url(#arrow)"
              />
            ))}

            {graph.nodes.map(node => {
              const pos = positions[node.id]
              if (!pos) return null
              const color = TYPE_COLOR[node.entity_type] || '#6b7280'
              const isSelected = selected === node.id
              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x},${pos.y})`}
                  onClick={() => setSelected(isSelected ? null : node.id)}
                  className="cursor-pointer"
                >
                  <circle
                    r={isSelected ? 18 : 14}
                    fill={color}
                    fillOpacity={isSelected ? 0.9 : 0.7}
                    stroke={isSelected ? color : 'transparent'}
                    strokeWidth={2}
                    strokeOpacity={0.5}
                  />
                  <text textAnchor="middle" dy="0.35em" fontSize={9} fill="white" fontFamily="monospace">
                    {node.name.slice(0, 8)}
                  </text>
                  <text textAnchor="middle" dy={isSelected ? 32 : 26} fontSize={9} fill="#9ca3af" fontFamily="sans-serif">
                    {node.name.length > 14 ? node.name.slice(0, 12) + '…' : node.name}
                  </text>
                </g>
              )
            })}
          </svg>

          {selectedNode && (
            <div className="flex-1 min-w-0 space-y-3">
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Selected</p>
                <div className="flex items-center gap-2">
                  <span style={{ color: TYPE_COLOR[selectedNode.entity_type] }}>
                    {TYPE_ICON[selectedNode.entity_type] || <User size={11} />}
                  </span>
                  <span className="text-sm font-medium text-white break-all">{selectedNode.name}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1 capitalize">{selectedNode.entity_type}</p>
              </div>

              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                  Connections ({connectedEdges.length})
                </p>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {connectedEdges.slice(0, 20).map((e, i) => {
                    const other = graph.nodes.find(n =>
                      n.id === (e.source_entity_id === selected ? e.target_entity_id : e.source_entity_id)
                    )
                    const isSource = e.source_entity_id === selected
                    return (
                      <div key={i} className="text-xs flex items-center gap-1.5 text-gray-400">
                        <span className={clsx('font-mono text-[10px] px-1 py-0.5 rounded', isSource ? 'bg-accent/20 text-accent' : 'bg-gray-700 text-gray-400')}>
                          {isSource ? '→' : '←'}
                        </span>
                        <span className="font-medium text-gray-300 truncate">{other?.name || 'unknown'}</span>
                        <span className="text-gray-600 truncate">via {e.relation}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-border">
        {Object.entries(TYPE_COLOR).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1 text-xs text-gray-500">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            {type}
          </span>
        ))}
      </div>
    </div>
  )
}
