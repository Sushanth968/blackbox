from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from db.base import Base
from db.types import UUIDType


class LinkedRepo(Base):
    """A GitHub repository linked to an investigation ("environment").

    One repo per investigation. A manual "Sync now" fetches recent repo activity
    and ingests it as evidence; ``last_synced_at`` records the last manual sync.
    (Automated/scheduled sync is intentionally out of scope.)
    """
    __tablename__ = "linked_repos"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("investigations.id"), nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255))  # "owner/repo"
    html_url: Mapped[str] = mapped_column(String(500))
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
