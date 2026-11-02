"""decision templates bank

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-03

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATES = [
    {
        "order": 1,
        "question": "¿Reforzamos la muralla norte o el puerto?",
        "option_a": "Muralla norte",
        "option_b": "El puerto",
    },
    {
        "order": 2,
        "question": "¿El mercado abre temprano o se espera a que llegue la caravana?",
        "option_a": "Abrir temprano",
        "option_b": "Esperar la caravana",
    },
    {
        "order": 3,
        "question": "¿Racionamos la comida o confiamos en la próxima cosecha?",
        "option_a": "Racionar",
        "option_b": "Confiar en la cosecha",
    },
    {
        "order": 4,
        "question": "¿La guardia entrena hoy o descansa para la próxima crisis?",
        "option_a": "Entrenar",
        "option_b": "Descansar",
    },
    {
        "order": 5,
        "question": "¿Se celebra una fiesta esta noche o se guarda el oro?",
        "option_a": "Celebrar",
        "option_b": "Guardar el oro",
    },
    {
        "order": 6,
        "question": "¿Exploramos el Bosque Gris o reforzamos el campamento?",
        "option_a": "Explorar",
        "option_b": "Reforzar el campamento",
    },
    {
        "order": 7,
        "question": "¿Se perdona una deuda del pueblo vecino o se cobra con intereses?",
        "option_a": "Perdonar",
        "option_b": "Cobrar con intereses",
    },
    {
        "order": 8,
        "question": "¿Se consulta a los Arquitectos o se actúa por cuenta propia?",
        "option_a": "Consultar",
        "option_b": "Actuar solos",
    },
]


def upgrade() -> None:
    op.create_table(
        "decision_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("question", sa.String(280), nullable=False),
        sa.Column("option_a", sa.String(120), nullable=False),
        sa.Column("option_b", sa.String(120), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default=sa.false()),
    )

    table = sa.table(
        "decision_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("order", sa.Integer),
        sa.column("question", sa.String),
        sa.column("option_a", sa.String),
        sa.column("option_b", sa.String),
    )
    op.bulk_insert(table, [{**t, "id": uuid.uuid4()} for t in TEMPLATES])


def downgrade() -> None:
    op.drop_table("decision_templates")
