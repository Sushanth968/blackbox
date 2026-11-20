from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base
from db.types import UUIDType

class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    investigation: Mapped["Investigation"] = relationship(back_populates="evidence_files")
    events: Mapped[list["Event"]] = relationship(back_populates="evidence_file")
