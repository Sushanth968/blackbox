from typing import Optional
import uuid
from sqlalchemy import String, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
from db.types import UUIDType


class CausalLink(Base):
    """A directed, evidence-backed link between two events: source (cause) →
    target (effect). Produced by the correlation engine, never hand-entered.

    ``link_type`` records how the link was inferred (``causal_rule`` or
    ``shared_identifier``); ``basis`` is a human-readable justification; and
    ``confidence`` is the engine's score in [0, 1]. Every link is an *inferred*
    relationship in BlackBox's provenance model — it points at two events whose
    own evidence is hashed, but the link itself is a deterministic inference.
    """
    __tablename__ = "causal_links"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    source_event_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("events.id"), nullable=False)
    target_event_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("events.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(255))
    link_type: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    basis: Mapped[Optional[str]] = mapped_column(Text)
