from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models.season import SeasonPhase
from app.services.season import PHASE_DURATION, advance_phase_if_due, next_phase_transition

START = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def _season(phase: SeasonPhase = SeasonPhase.construccion, started: datetime = START) -> SimpleNamespace:
    return SimpleNamespace(phase=phase, phase_started_at=started)


def test_no_transition_before_a_week():
    now = START + PHASE_DURATION - timedelta(seconds=1)

    assert next_phase_transition(SeasonPhase.construccion, START, now) is None


def test_transition_after_a_week_keeps_calendar_cadence():
    now = START + PHASE_DURATION + timedelta(hours=3)

    result = next_phase_transition(SeasonPhase.construccion, START, now)

    assert result == (SeasonPhase.conflicto, START + PHASE_DURATION)


def test_phases_follow_the_cycle_order():
    now = START + PHASE_DURATION
    expected = {
        SeasonPhase.construccion: SeasonPhase.conflicto,
        SeasonPhase.conflicto: SeasonPhase.convergencia,
        SeasonPhase.convergencia: SeasonPhase.colapso,
    }
    for current, following in expected.items():
        assert next_phase_transition(current, START, now)[0] == following


def test_never_goes_past_colapso():
    now = START + PHASE_DURATION * 5

    assert next_phase_transition(SeasonPhase.colapso, START, now) is None


def test_advance_phase_if_due_updates_season_and_reports_change():
    season = _season()
    now = START + PHASE_DURATION

    changed = advance_phase_if_due(season, now)

    assert changed is True
    assert season.phase == SeasonPhase.conflicto
    assert season.phase_started_at == START + PHASE_DURATION


def test_advance_phase_if_due_leaves_season_untouched_when_not_due():
    season = _season()

    changed = advance_phase_if_due(season, START + timedelta(days=1))

    assert changed is False
    assert season.phase == SeasonPhase.construccion
    assert season.phase_started_at == START


def test_advances_at_most_one_phase_per_call_even_if_late():
    season = _season()

    advance_phase_if_due(season, START + PHASE_DURATION * 3)

    assert season.phase == SeasonPhase.conflicto
    assert season.phase_started_at == START + PHASE_DURATION
