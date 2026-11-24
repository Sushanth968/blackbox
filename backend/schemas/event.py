import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Any, Optional

class EventOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    evidence_file_id: Optional[uuid.UUID]
    timestamp: Optional[datetime]
    timestamp_confidence: float
    source: Optional[str]
    actor: Optional[str]
    action: Optional[str]
    object: Optional[str]
    severity: str
    raw: Optional[str]
    source_line: Optional[int]
    extra: Optional[dict]
    label_type: Optional[str]

    class Config:
        from_attributes = True

class EventLabelUpdate(BaseModel):
    label_type: Optional[str]  # "fact" | "inference" | "hypothesis" | None

class TimelineOut(BaseModel):
    events: list[EventOut]
    conflicts: list[dict]
    total: int

class ConfidenceDimensionOut(BaseModel):
    name: str
    score: float
    weight: float
    detail: str
    penalty: float

class ConfidenceOut(BaseModel):
    overall: float
    label: str
    summary: str
    dimensions: list[ConfidenceDimensionOut]
    gaps: list[dict]
