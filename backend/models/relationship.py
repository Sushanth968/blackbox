from typing import Optional
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
from db.types import UUIDType

class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("entities.id"), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("entities.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(255))
    event_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDType, ForeignKey("events.id"))
