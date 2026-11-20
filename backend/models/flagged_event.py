from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
from db.types import UUIDType

class FlaggedEvent(Base):
    __tablename__ = "flagged_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("events.id"), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(255))
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
