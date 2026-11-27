from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel

class InvestigationCreate(BaseModel):
    title: str
    description: Optional[str] = None

class InvestigationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class InvestigationOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    status: str
    owner_email: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
