from typing import Optional
import uuid
from pydantic import BaseModel


class EntityOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    name: str
    entity_type: str
    canonical_name: Optional[str]

    class Config:
        from_attributes = True


class RelationshipOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relation: str
    event_id: Optional[uuid.UUID]

    class Config:
        from_attributes = True


class GraphOut(BaseModel):
    nodes: list[EntityOut]
    edges: list[RelationshipOut]
