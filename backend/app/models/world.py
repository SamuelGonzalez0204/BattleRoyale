import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorldState(Base):
    """Snapshot vivo de las 5 stats del mundo para una temporada."""

    __tablename__ = "world_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    season_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"), unique=True)

    poblacion: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    comida: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    moral: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    defensa: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    oro: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
