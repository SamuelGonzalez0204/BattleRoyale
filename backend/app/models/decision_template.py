import uuid

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import UserRole


class DecisionTemplate(Base):
    """Banco de preguntas del que se instancia la decisión diaria.
    Se recicla (used vuelve a False) cuando se agota."""

    __tablename__ = "decision_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(String(280), nullable=False)
    option_a: Mapped[str] = mapped_column(String(120), nullable=False)
    option_b: Mapped[str] = mapped_column(String(120), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Deltas sobre las stats del mundo según gane A o B: {"comida": 8, "oro": -5}
    effects_a: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    effects_b: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict, nullable=False)
    role_affinity: Mapped[UserRole | None] = mapped_column(Enum(UserRole, name="user_role"), nullable=True)
