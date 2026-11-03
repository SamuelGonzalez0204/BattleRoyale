"""seed factions and season 1

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-02

"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FACTIONS = [
    {"id": uuid.uuid4(), "slug": "gremio", "name": "Gremio del Comercio", "color": "#d9a94f"},
    {"id": uuid.uuid4(), "slug": "orden", "name": "Orden de la Muralla", "color": "#7c92ad"},
    {"id": uuid.uuid4(), "slug": "culto", "name": "Culto de la Grieta", "color": "#a06bdb"},
]
SEASON_ID = uuid.uuid4()
WORLD_STATE_ID = uuid.uuid4()


def upgrade() -> None:
    factions_table = sa.table(
        "factions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("color", sa.String),
    )
    op.bulk_insert(factions_table, FACTIONS)

    seasons_table = sa.table(
        "seasons",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("number", sa.Integer),
        sa.column("name", sa.String),
        sa.column(
            "phase",
            postgresql.ENUM(name="season_phase", create_type=False),
        ),
        sa.column("is_active", sa.Boolean),
        sa.column("started_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        seasons_table,
        [
            {
                "id": SEASON_ID,
                "number": 1,
                "name": "La Grieta Despierta",
                "phase": "construccion",
                "is_active": True,
                "started_at": datetime.now(timezone.utc),
            }
        ],
    )

    world_states_table = sa.table(
        "world_states",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("season_id", postgresql.UUID(as_uuid=True)),
        sa.column("poblacion", sa.Integer),
        sa.column("comida", sa.Integer),
        sa.column("moral", sa.Integer),
        sa.column("defensa", sa.Integer),
        sa.column("oro", sa.Integer),
    )
    op.bulk_insert(
        world_states_table,
        [
            {
                "id": WORLD_STATE_ID,
                "season_id": SEASON_ID,
                "poblacion": 68,
                "comida": 41,
                "moral": 55,
                "defensa": 72,
                "oro": 36,
            }
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM world_states"))
    op.execute(sa.text("DELETE FROM seasons"))
    op.execute(sa.text("DELETE FROM factions"))
