"""Integración contra Postgres real (BD battleroyale_test, ver conftest.py)."""

import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.decision import Decision, Vote
from app.models.season import Season, SeasonPhase
from app.models.user import User, UserRole
from app.models.world import WorldState
from app.services.daily_cycle import run_daily_close
from app.services.daily_decision import close_decision, ensure_decision_for_today
from app.services.season import PHASE_DURATION, get_world_state, world_stats

pytestmark = pytest.mark.integration

DAY = date(2026, 11, 10)
NOON = datetime.combine(DAY, time(12, 0), tzinfo=timezone.utc)
INITIAL = {"poblacion": 50, "comida": 50, "moral": 50, "defensa": 50, "oro": 50}


@pytest.fixture()
def season(db: Session) -> Season:
    # Número alto para que sea la temporada activa por encima de la sembrada en 0002.
    new_season = Season(
        number=900,
        name="Temporada de pruebas",
        phase=SeasonPhase.construccion,
        is_active=True,
        started_at=NOON,
        phase_started_at=NOON,
    )
    db.add(new_season)
    db.flush()
    db.add(WorldState(season_id=new_season.id, **INITIAL))
    db.commit()
    return new_season


def _user(db: Session) -> User:
    tag = uuid.uuid4().hex[:10]
    user = User(email=f"{tag}@test.local", handle=f"u_{tag}", hashed_password="x")
    db.add(user)
    db.flush()
    return user


def _decision(db: Session, season: Season, day: date, effects_a: dict, effects_b: dict) -> Decision:
    decision = ensure_decision_for_today(db, season, today=day, now=NOON)
    decision.effects_a = effects_a
    decision.effects_b = effects_b
    db.commit()
    return decision


def _vote(db: Session, decision: Decision, option: str, weight: int = 1) -> User:
    user = _user(db)
    db.add(Vote(decision_id=decision.id, user_id=user.id, option=option, weight=weight))
    db.commit()
    return user


def _stats(db: Session, season: Season) -> dict[str, int]:
    db.expire_all()
    return world_stats(get_world_state(db, season))


def test_new_decision_copies_effects_and_affinity_from_template(db: Session, season: Season) -> None:
    decision = ensure_decision_for_today(db, season, today=DAY, now=NOON)

    assert decision.effects_a and decision.effects_b
    assert decision.role_affinity in set(UserRole)
    assert decision.is_closed is False


def test_closing_applies_chispas_weighted_winner_effects(db: Session, season: Season) -> None:
    decision = _decision(db, season, DAY, {"comida": 8, "oro": -5}, {"defensa": 6, "moral": -3})
    _vote(db, decision, "a")
    _vote(db, decision, "a")
    _vote(db, decision, "b", weight=4)  # 1 voto + 3 Chispas pesa más que dos votos simples

    closed = close_decision(db, decision, now=NOON)

    assert closed.winner == "b"
    assert closed.closed_at == NOON
    assert _stats(db, season) == {**INITIAL, "defensa": 56, "moral": 47}


def test_closing_twice_is_idempotent(db: Session, season: Season) -> None:
    decision = _decision(db, season, DAY, {"comida": 8}, {"oro": 8})
    _vote(db, decision, "a")
    close_decision(db, decision, now=NOON)

    again = close_decision(db, decision, now=NOON + timedelta(hours=5))

    assert again.closed_at == NOON
    assert _stats(db, season)["comida"] == 58


def test_closing_without_votes_leaves_world_untouched(db: Session, season: Season) -> None:
    decision = _decision(db, season, DAY, {"comida": 8}, {"oro": 8})

    closed = close_decision(db, decision, now=NOON)

    assert closed.is_closed and closed.winner is None
    assert _stats(db, season) == INITIAL


def test_weighted_tie_goes_to_option_a(db: Session, season: Season) -> None:
    decision = _decision(db, season, DAY, {"comida": 8}, {"oro": 8})
    _vote(db, decision, "a", weight=2)
    _vote(db, decision, "b", weight=2)

    assert close_decision(db, decision, now=NOON).winner == "a"


def test_lazy_fallback_closes_yesterday_when_opening_today(db: Session, season: Season) -> None:
    yesterday = _decision(db, season, DAY, {"comida": -10}, {"oro": 10})
    _vote(db, yesterday, "a")

    today = ensure_decision_for_today(db, season, today=DAY + timedelta(days=1), now=NOON)

    db.refresh(yesterday)
    assert yesterday.is_closed and yesterday.winner == "a"
    assert _stats(db, season)["comida"] == 40
    assert today.day == DAY + timedelta(days=1)
    assert today.is_closed is False


def test_daily_close_job_closes_today_without_advancing_early(db: Session, season: Season) -> None:
    decision = _decision(db, season, DAY, {"moral": 5}, {"oro": 5})
    _vote(db, decision, "a")

    result = run_daily_close(db, now=NOON + timedelta(hours=11, minutes=59))

    db.refresh(decision)
    assert result.closed_decisions == 1 and decision.is_closed
    assert result.phase_changed is False
    assert _stats(db, season)["moral"] == 55


def test_daily_close_advances_phase_after_a_week(db: Session, season: Season) -> None:
    result = run_daily_close(db, now=NOON + PHASE_DURATION)

    db.refresh(season)
    assert result.phase_changed is True
    assert season.phase == SeasonPhase.conflicto
    assert season.phase_started_at == NOON + PHASE_DURATION


def test_stat_at_zero_does_not_advance_phase_before_a_week(db: Session, season: Season) -> None:
    state = get_world_state(db, season)
    state.comida = 4
    db.commit()
    decision = _decision(db, season, DAY, {"comida": -10}, {"oro": 1})
    _vote(db, decision, "a")

    result = run_daily_close(db, now=NOON + timedelta(hours=11))
    later = run_daily_close(db, now=NOON + PHASE_DURATION - timedelta(minutes=1))

    db.refresh(season)
    assert _stats(db, season)["comida"] == 0
    assert result.phase_changed is False and later.phase_changed is False
    assert season.phase == SeasonPhase.construccion
    assert season.phase_started_at == NOON


def test_season_walks_all_four_phases_and_stops_at_colapso(db: Session, season: Season) -> None:
    phases = []
    for day_offset in range(1, 36):
        result = run_daily_close(db, now=NOON + timedelta(days=day_offset))
        phases.append(result.phase)

    assert phases[6] == SeasonPhase.conflicto
    assert phases[13] == SeasonPhase.convergencia
    assert phases[20] == SeasonPhase.colapso
    assert phases[-1] == SeasonPhase.colapso


def test_voter_gets_role_after_five_votes(db: Session, season: Season) -> None:
    voter = _user(db)
    affinities = [UserRole.guardia] * 3 + [UserRole.mercader] * 2
    for offset, affinity in enumerate(affinities):
        decision = _decision(db, season, DAY + timedelta(days=offset), {"moral": 1}, {"oro": 1})
        decision.role_affinity = affinity
        db.add(Vote(decision_id=decision.id, user_id=voter.id, option="a", weight=1))
        db.commit()
        close_decision(db, decision, now=NOON + timedelta(days=offset))
        db.refresh(voter)
        if offset < len(affinities) - 1:
            assert voter.role is None

    assert voter.role == UserRole.guardia


def test_phase_change_recomputes_existing_roles(db: Session, season: Season) -> None:
    voter = _user(db)
    voter.role = UserRole.mercader
    for offset in range(5):
        decision = _decision(db, season, DAY + timedelta(days=offset), {"moral": 1}, {"oro": 1})
        decision.role_affinity = UserRole.explorador
        db.add(Vote(decision_id=decision.id, user_id=voter.id, option="b", weight=1))
        db.commit()
        close_decision(db, decision, now=NOON + timedelta(days=offset))
    db.refresh(voter)
    assert voter.role == UserRole.mercader  # ya tenía rol: no se toca hasta cambiar de fase

    result = run_daily_close(db, now=NOON + PHASE_DURATION)

    db.refresh(voter)
    assert result.phase_changed is True
    assert voter.role == UserRole.explorador
