from typing import Optional
import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
from db.types import UUIDType

class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100))
    canonical_name: Mapped[Optional[str]] = mapped_column(String(255))
