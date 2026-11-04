"""Regla pura de selección de la plantilla del día (services/template_selection.py)."""

import uuid
from datetime import date

from app.models.season import SeasonPhase
from app.services.template_selection import TemplateCandidate, choose_template

CONFLICTO = SeasonPhase.conflicto


def _candidate(
    order: int,
    phase: SeasonPhase | None = CONFLICTO,
    *,
    used_this_season: bool = False,
    last_used_on: date | None = None,
) -> TemplateCandidate:
    return TemplateCandidate(
        id=uuid.UUID(int=order),
        order=order,
        phase=phase,
        used_this_season=used_this_season,
        last_used_on=last_used_on,
    )


def test_returns_none_without_candidates_for_the_phase() -> None:
    assert choose_template([_candidate(1, SeasonPhase.colapso)], CONFLICTO, yesterday_id=None) is None
    assert choose_template([], CONFLICTO, yesterday_id=None) is None


def test_ignores_templates_of_other_phases() -> None:
    chosen = choose_template(
        [_candidate(1, SeasonPhase.construccion), _candidate(9, CONFLICTO)], CONFLICTO, yesterday_id=None
    )

    assert chosen == uuid.UUID(int=9)


def test_prefers_phase_specific_over_generic_when_both_are_fresh() -> None:
    chosen = choose_template([_candidate(1, None), _candidate(20, CONFLICTO)], CONFLICTO, yesterday_id=None)

    assert chosen == uuid.UUID(int=20)


def test_picks_the_lowest_order_among_fresh_phase_templates() -> None:
    chosen = choose_template([_candidate(30), _candidate(25), _candidate(27)], CONFLICTO, yesterday_id=None)

    assert chosen == uuid.UUID(int=25)


def test_falls_back_to_generic_when_phase_templates_were_used_this_season() -> None:
    candidates = [_candidate(25, used_this_season=True), _candidate(3, None)]

    assert choose_template(candidates, CONFLICTO, yesterday_id=None) == uuid.UUID(int=3)


def test_recycles_the_least_recently_used_when_everything_was_used() -> None:
    candidates = [
        _candidate(25, used_this_season=True, last_used_on=date(2026, 11, 5)),
        _candidate(26, used_this_season=True, last_used_on=date(2026, 11, 2)),
        _candidate(3, None, used_this_season=True, last_used_on=date(2026, 11, 4)),
    ]

    assert choose_template(candidates, CONFLICTO, yesterday_id=None) == uuid.UUID(int=26)


def test_never_used_counts_as_the_oldest_when_recycling() -> None:
    candidates = [
        _candidate(25, used_this_season=True, last_used_on=date(2026, 11, 2)),
        _candidate(26, used_this_season=True, last_used_on=None),
    ]

    assert choose_template(candidates, CONFLICTO, yesterday_id=None) == uuid.UUID(int=26)


def test_never_repeats_yesterday_even_if_it_would_be_the_best_pick() -> None:
    # Temporada nueva: nada usado aún en ella, pero la 25 cerró la temporada anterior ayer.
    candidates = [_candidate(25, last_used_on=date(2026, 11, 3)), _candidate(26)]

    assert choose_template(candidates, CONFLICTO, yesterday_id=uuid.UUID(int=25)) == uuid.UUID(int=26)


def test_repeats_yesterday_only_when_it_is_the_single_candidate() -> None:
    candidates = [_candidate(25, used_this_season=True, last_used_on=date(2026, 11, 3))]

    assert choose_template(candidates, CONFLICTO, yesterday_id=uuid.UUID(int=25)) == uuid.UUID(int=25)


def test_does_not_mutate_the_candidates() -> None:
    candidates = [_candidate(26), _candidate(25)]
    snapshot = list(candidates)

    choose_template(candidates, CONFLICTO, yesterday_id=None)

    assert candidates == snapshot
