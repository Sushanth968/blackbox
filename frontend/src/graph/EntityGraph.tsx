import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Network, RefreshCw, Loader2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react'
import { api } from '../services/api'
import type { GraphData, Entity } from '../services/types'
import { useMemo, useState, useRef, useCallback, useEffect } from 'react'
import clsx from 'clsx'

const TYPE_COLOR: Record<string, string> = {
  user:  '#6366f1',
  ip:    '#f59e0b',
  email: '#10b981',
  path:  '#3b82f6',
  url:   '#8b5cf6',
  hash:  '#6b7280',
}

function useLayout(nodes: Entity[], edges: { source: string; target: string; relation?: string }[], width: number, height: number) {
  return useMemo(() => {
    if (!nodes.length) return { positions: {}, links: [] }
    const positions: Record<string, { x: number; y: number }> = {}
    const cx = width / 2, cy = height / 2
    const r = Math.min(width, height) * 0.36

    nodes.forEach((n, i) => {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2
      positions[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) }
    })

    for (let iter = 0; iter < 60; iter++) {
      const forces: Record<string, { fx: number; fy: number }> = {}
      nodes.forEach(n => { forces[n.id] = { fx: 0, fy: 0 } })

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = positions[nodes[i].id], b = positions[nodes[j].id]
          const dx = a.x - b.x, dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy) || 1
          const force = 2000 / (dist * dist)
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
        const target = 140
        const force = (dist - target) * 0.05
        forces[e.source].fx += (dx / dist) * force
        forces[e.source].fy += (dy / dist) * force
        forces[e.target].fx -= (dx / dist) * force
        forces[e.target].fy -= (dy / dist) * force
      })

      nodes.forEach(n => {
        const p = positions[n.id]
        forces[n.id].fx += (cx - p.x) * 0.008
        forces[n.id].fy += (cy - p.y) * 0.008
      })

      nodes.forEach(n => {
        const p = positions[n.id]
        const f = forces[n.id]
        p.x = Math.max(48, Math.min(width - 48, p.x + f.fx * 0.4))
        p.y = Math.max(48, Math.min(height - 48, p.y + f.fy * 0.4))
      })
    }

    const links = edges.map(e => ({
      ...e,
      relation: e.relation ?? '',
      x1: positions[e.source]?.x ?? 0,
      y1: positions[e.source]?.y ?? 0,
      x2: positions[e.target]?.x ?? 0,
      y2: positions[e.target]?.y ?? 0,
    }))
    return { positions, links }
  }, [nodes, edges, width, height])
}

interface Tooltip {
  nodeId: string
  x: number
  y: number
}

export default function EntityGraph({ investigationId }: { investigationId: string }) {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string | null>(null)
  const [tooltip, setTooltip] = useState<Tooltip | null>(null)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const dragging = useRef<{ startX: number; startY: number; panX: number; panY: number } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 800, h: 480 })

  useEffect(() => {
    if (!containerRef.current) return
    const obs = new ResizeObserver(([entry]) => {
      setSize({ w: entry.contentRect.width, h: Math.max(400, entry.contentRect.width * 0.55) })
    })
    obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [])

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    setZoom(z => Math.min(4, Math.max(0.2, z * (e.deltaY < 0 ? 1.12 : 0.9))))
  }, [])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as Element).closest('.graph-node')) return
    dragging.current = { startX: e.clientX, startY: e.clientY, panX: pan.x, panY: pan.y }
  }, [pan])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current) return
    setTooltip(null)
    setPan({
      x: dragging.current.panX + (e.clientX - dragging.current.startX),
      y: dragging.current.panY + (e.clientY - dragging.current.startY),
    })
  }, [])

  const onMouseUp = useCallback(() => { dragging.current = null }, [])
  const resetView = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }) }, [])

  const { data: graph, isLoading } = useQuery<GraphData>({
    queryKey: ['graph', investigationId],
    queryFn: () => api.get(`/investigations/${investigationId}/graph`).then(r => r.data),
  })

  const resolve = useMutation({
    mutationFn: () => api.post(`/investigations/${investigationId}/entities/resolve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['graph', investigationId] }),
  })

  const { w: W, h: H } = size

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

  const tooltipNode = tooltip ? graph?.nodes.find(n => n.id === tooltip.nodeId) : null
  const tooltipEdges = tooltip ? graph?.edges.filter(
    e => e.source_entity_id === tooltip.nodeId || e.target_entity_id === tooltip.nodeId
  ) || [] : []

  const selectedConnectedIds = selected ? new Set(
    (graph?.edges || [])
      .filter(e => e.source_entity_id === selected || e.target_entity_id === selected)
      .flatMap(e => [e.source_entity_id, e.target_entity_id])
  ) : null

  if (isLoading) return (
    <div className="bg-panel border border-border rounded-xl p-4 flex justify-center py-16">
      <Loader2 size={20} className="animate-spin text-muted" />
    </div>
  )

  return (
    <div className="bg-panel border border-border rounded-xl overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Network size={14} className="text-accent" />
          Entity Relationship Graph
        </h2>
        <div className="flex items-center gap-3">
          {graph && (
            <span className="text-xs text-muted">
              {graph.nodes.length} nodes · {dedupEdges.length} edges
            </span>
          )}
          <div className="flex items-center gap-1">
            <button onClick={() => setZoom(z => Math.min(4, z * 1.2))} className="w-7 h-7 bg-surface border border-border rounded flex items-center justify-center hover:bg-black/5 transition-colors" title="Zoom in"><ZoomIn size={13} className="text-muted" /></button>
            <button onClick={() => setZoom(z => Math.max(0.2, z * 0.8))} className="w-7 h-7 bg-surface border border-border rounded flex items-center justify-center hover:bg-black/5 transition-colors" title="Zoom out"><ZoomOut size={13} className="text-muted" /></button>
            <button onClick={resetView} className="w-7 h-7 bg-surface border border-border rounded flex items-center justify-center hover:bg-black/5 transition-colors" title="Reset view"><Maximize2 size={12} className="text-muted" /></button>
          </div>
          <button
            onClick={() => resolve.mutate()}
            disabled={resolve.isPending}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-accent text-white rounded-lg hover:bg-accent-2 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={resolve.isPending ? 'animate-spin' : ''} />
            Resolve
          </button>
        </div>
      </div>

      {!graph || graph.nodes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-muted">
          <Network size={40} className="mb-3 opacity-20" />
          <p className="text-sm font-medium">No entities yet</p>
          <p className="text-xs mt-1">Upload evidence files then click Resolve</p>
        </div>
      ) : (
        <div className="flex-1 relative" ref={containerRef}>
          <svg
            width={W} height={H}
            className="w-full bg-slate-50"
            style={{ cursor: dragging.current ? 'grabbing' : 'grab' }}
            onWheel={onWheel}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={() => { onMouseUp(); setTooltip(null) }}
          >
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#cbd5e1" />
              </marker>
              {Object.entries(TYPE_COLOR).map(([type]) => (
                <filter key={type} id={`glow-${type}`} x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              ))}
            </defs>

            <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
              {/* Edges */}
              {links.map((l, i) => {
                const isHighlighted = selected && (l.source === selected || l.target === selected)
                const dx = l.x2 - l.x1, dy = l.y2 - l.y1
                const dist = Math.sqrt(dx * dx + dy * dy) || 1
                const offset = 22
                const ex2 = l.x2 - (dx / dist) * offset
                const ey2 = l.y2 - (dy / dist) * offset
                return (
                  <g key={i}>
                    <line
                      x1={l.x1} y1={l.y1} x2={ex2} y2={ey2}
                      stroke={isHighlighted ? '#6366f1' : '#e2e8f0'}
                      strokeWidth={isHighlighted ? 2 : 1.5}
                      strokeOpacity={selected && !isHighlighted ? 0.3 : 1}
                      markerEnd="url(#arrowhead)"
                    />
                    {l.relation && (
                      <text
                        x={(l.x1 + ex2) / 2} y={(l.y1 + ey2) / 2 - 5}
                        textAnchor="middle" fontSize={9}
                        fill={isHighlighted ? '#6366f1' : '#94a3b8'}
                        fontFamily="sans-serif"
                        opacity={selected && !isHighlighted ? 0.3 : 1}
                      >
                        {l.relation}
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Nodes */}
              {graph.nodes.map(node => {
                const pos = positions[node.id]
                if (!pos) return null
                const color = TYPE_COLOR[node.entity_type] || '#6b7280'
                const isSelected = selected === node.id
                const isHovered = tooltip?.nodeId === node.id
                const isDimmed = selected && !isSelected && selectedConnectedIds && !selectedConnectedIds.has(node.id)
                const r = isSelected ? 26 : isHovered ? 24 : 20

                return (
                  <g
                    key={node.id}
                    className="graph-node"
                    transform={`translate(${pos.x},${pos.y})`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelected(isSelected ? null : node.id)}
                    onMouseEnter={e => {
                      const rect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect()
                      setTooltip({ nodeId: node.id, x: pos.x * zoom + pan.x + rect.left, y: pos.y * zoom + pan.y + rect.top })
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  >
                    {/* Glow ring for selected */}
                    {isSelected && (
                      <circle r={r + 8} fill={color} fillOpacity={0.15} />
                    )}
                    {/* Shadow */}
                    <circle r={r} fill={color} fillOpacity={isDimmed ? 0.15 : isSelected ? 1 : isHovered ? 0.9 : 0.75}
                      stroke={isSelected ? color : isHovered ? color : 'white'}
                      strokeWidth={isSelected ? 3 : isHovered ? 2 : 1.5}
                      strokeOpacity={isSelected || isHovered ? 1 : 0.6}
                      style={{ transition: 'r 0.15s, fill-opacity 0.15s' }}
                    />
                    {/* Icon letter */}
                    <text textAnchor="middle" dy="0.35em" fontSize={11} fontWeight="600" fill="white" fontFamily="system-ui" opacity={isDimmed ? 0.3 : 1}>
                      {node.entity_type.slice(0, 1).toUpperCase()}
                    </text>
                    {/* Label below */}
                    <text
                      textAnchor="middle" dy={r + 14} fontSize={10}
                      fill={isDimmed ? '#cbd5e1' : isSelected ? '#0f172a' : '#475569'}
                      fontFamily="system-ui" fontWeight={isSelected ? '600' : '400'}
                    >
                      {node.name.length > 16 ? node.name.slice(0, 14) + '…' : node.name}
                    </text>
                  </g>
                )
              })}
            </g>
          </svg>

          {/* Hover tooltip */}
          {tooltipNode && tooltip && (
            <div
              className="absolute z-30 bg-white border border-border rounded-xl shadow-lg p-3 w-56 pointer-events-none"
              style={{
                left: Math.min(tooltip.x - (containerRef.current?.getBoundingClientRect().left ?? 0) + 20, W - 240),
                top: Math.max(8, tooltip.y - (containerRef.current?.getBoundingClientRect().top ?? 0) - 40),
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                  style={{ backgroundColor: TYPE_COLOR[tooltipNode.entity_type] || '#6b7280' }}>
                  {tooltipNode.entity_type.slice(0, 1).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-foreground truncate">{tooltipNode.name}</p>
                  <p className="text-[10px] text-muted capitalize">{tooltipNode.entity_type}</p>
                </div>
              </div>
              {tooltipEdges.length > 0 && (
                <div className="border-t border-border pt-2 space-y-1">
                  <p className="text-[10px] text-muted uppercase tracking-wide font-medium mb-1">{tooltipEdges.length} connection{tooltipEdges.length !== 1 ? 's' : ''}</p>
                  {tooltipEdges.slice(0, 4).map((e, i) => {
                    const other = graph.nodes.find(n => n.id === (e.source_entity_id === tooltipNode.id ? e.target_entity_id : e.source_entity_id))
                    const isSource = e.source_entity_id === tooltipNode.id
                    return (
                      <div key={i} className="flex items-center gap-1.5 text-[11px]">
                        <span className={clsx('px-1 py-0.5 rounded text-[9px] font-mono', isSource ? 'bg-accent/10 text-accent' : 'bg-black/5 text-muted')}>
                          {isSource ? '→' : '←'}
                        </span>
                        <span className="text-foreground font-medium truncate">{other?.name || '?'}</span>
                        <span className="text-muted truncate shrink-0">{e.relation}</span>
                      </div>
                    )
                  })}
                  {tooltipEdges.length > 4 && <p className="text-[10px] text-muted">+{tooltipEdges.length - 4} more</p>}
                </div>
              )}
              <p className="text-[9px] text-muted mt-2">Click to pin · scroll to zoom</p>
            </div>
          )}

          {/* Legend + hint */}
          <div className="absolute bottom-2 left-3 flex flex-wrap gap-3">
            {Object.entries(TYPE_COLOR).map(([type, color]) => (
              <span key={type} className="flex items-center gap-1 text-[10px] text-muted bg-white/80 px-1.5 py-0.5 rounded-full border border-border">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                {type}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
