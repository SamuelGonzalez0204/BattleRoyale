"""Banco de la Fase E contra Postgres: migración 0008, selección diaria y GET /today."""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data.decision_bank import BANK_TEMPLATES, LEGACY_REGIONS
from app.models.decision import Decision
from app.models.decision_template import DecisionTemplate
from app.models.season import Season, SeasonPhase
from app.models.world import WorldState
from app.services.daily_decision import ensure_decision_for_today

pytestmark = pytest.mark.integration

START = date(2026, 12, 1)
NOON = datetime.combine(START, time(12, 0), tzinfo=timezone.utc)
STATS = {"poblacion": 50, "comida": 50, "moral": 50, "defensa": 50, "oro": 50}
PER_PHASE = 15
LEGACY_COUNT = len(LEGACY_REGIONS)


def _season(db: Session, phase: SeasonPhase, number: int = 950) -> Season:
    season = Season(
        number=number,
        name=f"Temporada banco {number}",
        phase=phase,
        is_active=True,
        started_at=NOON,
        phase_started_at=NOON,
    )
    db.add(season)
    db.flush()
    db.add(WorldState(season_id=season.id, **STATS))
    db.commit()
    return season


def _templates_by_id(db: Session) -> dict:
    return {template.id: template for template in db.query(DecisionTemplate).all()}


def test_migration_seeds_fifteen_templates_per_phase(db: Session) -> None:
    rows = dict(db.query(DecisionTemplate.phase, func.count(DecisionTemplate.id)).group_by(DecisionTemplate.phase))

    assert rows == {**{phase: PER_PHASE for phase in SeasonPhase}, None: LEGACY_COUNT}


def test_migration_backfills_legacy_regions_and_keeps_their_phase_open(db: Session) -> None:
    legacy = db.query(DecisionTemplate).filter(DecisionTemplate.order <= LEGACY_COUNT).all()

    assert {t.order: t.region for t in legacy} == LEGACY_REGIONS
    assert all(t.phase is None for t in legacy)


def test_migration_rows_match_the_snapshot(db: Session) -> None:
    by_order = {t.order: t for t in db.query(DecisionTemplate).all()}

    for seed in BANK_TEMPLATES:
        row = by_order[seed["order"]]
        assert row.question == seed["question"]
        assert row.region == seed["region"]
        assert row.phase == SeasonPhase(seed["phase"])
        assert row.role_affinity.value == seed["role_affinity"]
        assert row.effects_a == seed["effects_a"] and row.effects_b == seed["effects_b"]


def test_daily_decision_uses_the_current_phase_and_copies_region(db: Session) -> None:
    season = _season(db, SeasonPhase.conflicto)
    templates = _templates_by_id(db)

    decision = ensure_decision_for_today(db, season, today=START, now=NOON)

    template = templates[decision.template_id]
    assert template.phase == SeasonPhase.conflicto
    assert decision.region == template.region
    assert decision.question == template.question


def test_season_walks_phase_bank_then_generic_then_recycles(db: Session) -> None:
    season = _season(db, SeasonPhase.conflicto)
    templates = _templates_by_id(db)

    chosen = []
    for offset in range(PER_PHASE + LEGACY_COUNT + 2):
        day = START + timedelta(days=offset)
        decision = ensure_decision_for_today(db, season, today=day, now=NOON)
        chosen.append(templates[decision.template_id])

    first_phase = chosen[:PER_PHASE]
    generic = chosen[PER_PHASE : PER_PHASE + LEGACY_COUNT]
    recycled = chosen[PER_PHASE + LEGACY_COUNT :]
    assert all(t.phase == SeasonPhase.conflicto for t in first_phase)
    assert len({t.id for t in first_phase}) == PER_PHASE
    assert all(t.phase is None for t in generic)
    assert len({t.id for t in generic}) == LEGACY_COUNT
    # Agotado: se recicla la usada hace más tiempo (la primera del recorrido).
    assert [t.id for t in recycled] == [chosen[0].id, chosen[1].id]
    for yesterday, today in zip(chosen, chosen[1:]):
        assert yesterday.id != today.id


def test_new_season_does_not_repeat_the_last_template_of_the_previous_one(db: Session) -> None:
    previous = _season(db, SeasonPhase.colapso, number=951)
    last = ensure_decision_for_today(db, previous, today=START, now=NOON)
    previous.is_active = False
    db.commit()
    following = _season(db, SeasonPhase.colapso, number=952)

    decision = ensure_decision_for_today(db, following, today=START + timedelta(days=1), now=NOON)

    assert decision.template_id != last.template_id


def test_today_endpoint_exposes_region_and_region_name(db: Session, api, make_user) -> None:
    _season(db, SeasonPhase.convergencia)
    _, headers = make_user()

    response = api.get("/api/decisions/today", headers=headers)

    assert response.status_code == 200
    body = response.json()
    stored = db.query(Decision).filter(Decision.id == body["id"]).one()
    assert body["region"] == stored.region
    assert body["region"] in {"plaza", "bahia", "muralla", "cementerio", "campos", "bosque", "cumbres"}
    assert isinstance(body["region_name"], str) and body["region_name"]
