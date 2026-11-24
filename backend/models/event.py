from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base
from db.types import UUIDType

class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    evidence_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("evidence_files.id"))

    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    timestamp_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[Optional[str]] = mapped_column(String(255))
    actor: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[Optional[str]] = mapped_column(String(255))
    object: Mapped[Optional[str]] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(50), default="info")
    raw: Mapped[Optional[str]] = mapped_column(Text)
    source_line: Mapped[Optional[int]] = mapped_column(Integer)
    extra: Mapped[Optional[dict]] = mapped_column(JSON)
    label_type: Mapped[Optional[str]] = mapped_column(String(50))  # fact | inference | hypothesis

    investigation: Mapped["Investigation"] = relationship(back_populates="events")
    evidence_file: Mapped["EvidenceFile"] = relationship(back_populates="events")
