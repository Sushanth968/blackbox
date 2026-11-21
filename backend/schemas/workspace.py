from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel

class NoteCreate(BaseModel):
    content: str
    author: Optional[str] = None
    event_id: Optional[uuid.UUID] = None

class NoteOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    event_id: Optional[uuid.UUID]
    content: str
    author: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FlagCreate(BaseModel):
    event_id: uuid.UUID
    label: Optional[str] = None

class FlagOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    event_id: uuid.UUID
    label: Optional[str]
    flagged_at: datetime

    class Config:
        from_attributes = True
