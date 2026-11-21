from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel

class EvidenceFileOut(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    original_name: str
    file_type: Optional[str]
    file_size: Optional[int]
    sha256: Optional[str]
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True
