export interface Investigation {
  id: string
  title: string
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface EvidenceFile {
  id: string
  investigation_id: string
  original_name: string
  file_type: string | null
  file_size: number | null
  sha256: string | null
  status: string
  uploaded_at: string
}

export interface Event {
  id: string
  investigation_id: string
  evidence_file_id: string | null
  timestamp: string | null
  timestamp_confidence: number
  source: string | null
  actor: string | null
  action: string | null
  object: string | null
  severity: string
  raw: string | null
  source_line: number | null
  extra: Record<string, unknown> | null
  label_type: string | null  // "fact" | "inference" | "hypothesis" | null
}

export interface TimelineResponse {
  events: Event[]
  conflicts: Conflict[]
  total: number
}

export interface Conflict {
  type: string
  source: string
  event_a_id: string
  event_b_id: string
  delta_seconds: number
  description: string
}

export interface Entity {
  id: string
  investigation_id: string
  name: string
  entity_type: string
  canonical_name: string | null
}

export interface GraphEdge {
  id: string
  investigation_id: string
  source_entity_id: string
  target_entity_id: string
  relation: string
  event_id: string | null
}

export type Relationship = GraphEdge

export interface GraphData {
  nodes: Entity[]
  edges: GraphEdge[]
}

export interface Note {
  id: string
  investigation_id: string
  event_id: string | null
  content: string
  author: string | null
  created_at: string
  updated_at: string
}

export interface FlaggedEvent {
  id: string
  investigation_id: string
  event_id: string
  label: string | null
  flagged_at: string
}

export interface ConfidenceDimension {
  name: string
  score: number
  weight: number
  detail: string
  penalty: number
}

export interface ConfidenceScore {
  overall: number
  label: string
  summary: string
  dimensions: ConfidenceDimension[]
  gaps: EvidenceGap[]
}

export interface EvidenceGap {
  start_time: string
  end_time: string
  duration_seconds: number
  before_event_id: string
  after_event_id: string
  description: string
}
