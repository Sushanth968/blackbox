from typing import Optional
import uuid
from pydantic import BaseModel


class CausalLinkOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    source_event_id: uuid.UUID
    target_event_id: uuid.UUID
    relation: str
    link_type: str
    confidence: float
    basis: Optional[str]

    class Config:
        from_attributes = True
