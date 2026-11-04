"""Fase E: banco de 60 decisiones por fase y región, ranking e índices de lectura

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-04

Añade `region` (una de las 7 regiones del mapa) y `phase` (NULL = cualquier fase)
a `decision_templates`; `region` y `template_id` a `decisions`. Siembra las 60
plantillas del snapshot congelado `app.data.decision_bank` (su huella sha256 la
fija tests/test_decision_bank.py, así que editarlo rompe CI en vez de reescribir
la historia) y rellena la región de las 8 plantillas originales.
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.data.decision_bank import BANK_TEMPLATES, LEGACY_REGIONS

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Copia literal: la migración no depende de que app.data.regions cambie en el futuro.
REGION_IDS = ("plaza", "bahia", "muralla", "cementerio", "campos", "bosque", "cumbres")
REGION_CHECK = "region IN ({})".format(", ".join(f"'{region}'" for region in REGION_IDS))

# Tipos ya existentes (0001): solo se referencian.
season_phase = postgresql.ENUM(
    "construccion", "conflicto", "convergencia", "colapso", name="season_phase", create_type=False
)
user_role = postgresql.ENUM("mercader", "guardia", "cronista", "explorador", name="user_role", create_type=False)
UUID = postgresql.UUID(as_uuid=True)


def _add_columns() -> None:
    op.add_column("decision_templates", sa.Column("region", sa.String(32), nullable=True))
    op.add_column("decision_templates", sa.Column("phase", season_phase, nullable=True))
    op.create_check_constraint("ck_decision_template_region", "decision_templates", REGION_CHECK)

    op.add_column("decisions", sa.Column("region", sa.String(32), nullable=True))
    op.add_column(
        "decisions", sa.Column("template_id", UUID, sa.ForeignKey("decision_templates.id"), nullable=True)
    )
    op.create_check_constraint("ck_decision_region", "decisions", f"region IS NULL OR {REGION_CHECK}")


def _create_indexes() -> None:
    # Selección diaria: plantillas usadas por temporada / la usada hace más tiempo.
    op.create_index("ix_decisions_template_day", "decisions", ["template_id", "day"])
    # Lore: últimas decisiones cerradas.
    op.create_index("ix_decisions_closed_day", "decisions", ["day"], postgresql_where=sa.text("closed_at IS NOT NULL"))
    # Ranking por votos: votos de un usuario (se une con decisions por temporada).
    op.create_index("ix_votes_user_decision", "votes", ["user_id", "decision_id"])
    # Ranking por Chispas y miembros de una facción.
    op.create_index("ix_users_chispas_handle", "users", [sa.text("chispas DESC"), "handle"])
    op.create_index("ix_users_faction_handle", "users", ["faction_id", "handle"])


def _backfill_legacy() -> None:
    templates = sa.table("decision_templates", sa.column("order", sa.Integer), sa.column("region", sa.String))
    for order, region in LEGACY_REGIONS.items():
        op.execute(templates.update().where(templates.c.order == order).values(region=region))
    op.alter_column("decision_templates", "region", nullable=False)


def _seed_bank() -> None:
    table = sa.table(
        "decision_templates",
        sa.column("id", UUID),
        sa.column("order", sa.Integer),
        sa.column("question", sa.String),
        sa.column("option_a", sa.String),
        sa.column("option_b", sa.String),
        sa.column("used", sa.Boolean),
        sa.column("effects_a", postgresql.JSONB),
        sa.column("effects_b", postgresql.JSONB),
        # Columnas ENUM tipadas como el ENUM: si no, Postgres rechaza el VARCHAR.
        sa.column("role_affinity", user_role),
        sa.column("phase", season_phase),
        sa.column("region", sa.String),
    )
    op.bulk_insert(table, [{**template, "id": uuid.uuid4(), "used": False} for template in BANK_TEMPLATES])


def _backfill_decisions() -> None:
    # Las decisiones ya creadas no guardan su plantilla: se emparejan por la pregunta.
    op.execute(
        sa.text(
            """
            UPDATE decisions AS d
            SET template_id = t.id, region = t.region
            FROM decision_templates AS t
            WHERE d.question = t.question AND d.template_id IS NULL
            """
        )
    )


def upgrade() -> None:
    _add_columns()
    _create_indexes()
    _backfill_legacy()
    _seed_bank()
    _backfill_decisions()


def downgrade() -> None:
    orders = [template["order"] for template in BANK_TEMPLATES]
    op.execute(sa.text("UPDATE decisions SET template_id = NULL"))
    op.execute(
        sa.text('DELETE FROM decision_templates WHERE "order" = ANY(:orders)').bindparams(orders=orders)
    )
    for index, table in (
        ("ix_users_faction_handle", "users"),
        ("ix_users_chispas_handle", "users"),
        ("ix_votes_user_decision", "votes"),
        ("ix_decisions_closed_day", "decisions"),
        ("ix_decisions_template_day", "decisions"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_constraint("ck_decision_region", "decisions", type_="check")
    op.drop_column("decisions", "template_id")
    op.drop_column("decisions", "region")
    op.drop_constraint("ck_decision_template_region", "decision_templates", type_="check")
    op.drop_column("decision_templates", "phase")
    op.drop_column("decision_templates", "region")
