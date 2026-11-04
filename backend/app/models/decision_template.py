import uuid

from sqlalchemy import Boolean, CheckConstraint, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.data.regions import REGION_IDS
from app.db.base import Base
from app.models.season import SeasonPhase
from app.models.user import UserRole

REGION_CHECK = "region IN ({})".format(", ".join(f"'{region}'" for region in REGION_IDS))


class DecisionTemplate(Base):
    """Banco de preguntas del que se instancia la decisión diaria.

    Cada plantilla ocurre en una región del mapa y puede limitarse a una fase de
    la temporada (`phase` NULL = cualquier fase). Qué plantilla sale cada día lo
    decide services/template_selection.py a partir de las decisiones ya creadas;
    `used` es un resto de la Fase A y ya no interviene en la selección."""

    __tablename__ = "decision_templates"
    __table_args__ = (CheckConstraint(REGION_CHECK, name="ck_decision_template_region"),)

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

    region: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[SeasonPhase | None] = mapped_column(Enum(SeasonPhase, name="season_phase"), nullable=True)
