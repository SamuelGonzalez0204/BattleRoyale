"""Fase B: reglas puras de zonas, elección de campeón, calendario, sellos y reset."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.season import SeasonPhase
from app.services.battle_royale.champions import ChampionCandidate, choose_champion
from app.services.battle_royale.lifecycle import EVENT_START_DELAY, is_battle_royale_due
from app.services.battle_royale.seals import (
    DEFAULT_SEAL,
    SEAL_BONUSES,
    SEAL_WINDOW,
    seal_deadline,
    seal_is_overdue,
)
from app.services.battle_royale.zones import (
    ARENA,
    FALL_ORDER,
    TOTAL_ROUNDS,
    ZONE_IDS,
    ZONE_NAMES,
    zone_falls,
    zone_for_round,
)
from app.services.season import WORLD_BASELINE, next_season_world

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


# --- Zonas -------------------------------------------------------------------


def test_fall_order_goes_from_outer_regions_to_plaza() -> None:
    assert FALL_ORDER == ("bahia", "campos", "bosque", "cementerio", "muralla", "plaza")
    assert ARENA == "cumbres"
    assert set(ZONE_IDS) == {*FALL_ORDER, ARENA}
    assert set(ZONE_NAMES) == set(ZONE_IDS)


def test_one_zone_per_round_and_the_arena_last() -> None:
    assert TOTAL_ROUNDS == 7
    assert [zone_for_round(r) for r in range(1, 8)] == [*FALL_ORDER, ARENA]


@pytest.mark.parametrize("round_number", [0, 8, -1])
def test_rounds_out_of_range_are_rejected(round_number: int) -> None:
    with pytest.raises(ValueError):
        zone_for_round(round_number)


def test_the_arena_never_falls() -> None:
    assert zone_falls("bahia") is True
    assert zone_falls(ARENA) is False


# --- Campeón -----------------------------------------------------------------


def _candidate(handle: str, sponsored: int = 0, first: datetime | None = None, chispas: int = 0, joined=T0):
    return ChampionCandidate(
        user_id=uuid.uuid4(),
        handle=handle,
        sponsored_chispas=sponsored,
        first_sponsored_at=first,
        chispas=chispas,
        joined_at=joined,
    )


def test_most_sponsored_member_is_champion() -> None:
    chosen = choose_champion(
        [_candidate("ana", 5, T0, chispas=99), _candidate("bea", 8, T0 + timedelta(hours=1))]
    )

    assert chosen is not None and chosen.handle == "bea"


def test_sponsorship_tie_goes_to_the_earliest_sponsored() -> None:
    chosen = choose_champion([_candidate("ana", 5, T0 + timedelta(hours=2)), _candidate("bea", 5, T0)])

    assert chosen is not None and chosen.handle == "bea"


def test_without_sponsorships_the_richest_member_is_champion() -> None:
    chosen = choose_champion([_candidate("ana", chispas=3), _candidate("bea", chispas=12)])

    assert chosen is not None and chosen.handle == "bea"


def test_balance_tie_goes_to_the_oldest_account_then_handle() -> None:
    older = choose_champion(
        [_candidate("ana", chispas=4, joined=T0 + timedelta(days=1)), _candidate("bea", chispas=4, joined=T0)]
    )
    by_handle = choose_champion([_candidate("zoe", chispas=4), _candidate("ana", chispas=4)])

    assert older is not None and older.handle == "bea"
    assert by_handle is not None and by_handle.handle == "ana"


def test_faction_without_members_has_no_champion() -> None:
    assert choose_champion([]) is None


# --- Calendario --------------------------------------------------------------


def test_event_is_due_after_seven_days_of_colapso() -> None:
    assert EVENT_START_DELAY == timedelta(days=7)
    assert is_battle_royale_due(SeasonPhase.colapso, T0, T0 + timedelta(days=7)) is True
    assert is_battle_royale_due(SeasonPhase.colapso, T0, T0 + timedelta(days=7) - timedelta(seconds=1)) is False


@pytest.mark.parametrize("phase", [SeasonPhase.construccion, SeasonPhase.conflicto, SeasonPhase.convergencia])
def test_event_is_never_due_before_colapso(phase: SeasonPhase) -> None:
    assert is_battle_royale_due(phase, T0, T0 + timedelta(days=30)) is False


# --- Sellos y reset ----------------------------------------------------------


def test_seal_bonuses() -> None:
    assert SEAL_BONUSES == {
        "abundancia": {"comida": 15},
        "muralla": {"defensa": 15},
        "oro": {"oro": 15},
        "eco": {"moral": 15},
        "cuna": {"poblacion": 15},
    }
    assert DEFAULT_SEAL == "eco"


def test_seal_window_is_24_hours() -> None:
    assert SEAL_WINDOW == timedelta(hours=24)
    deadline = seal_deadline(T0)
    assert deadline == T0 + timedelta(hours=24)
    assert seal_is_overdue(deadline, deadline) is True
    assert seal_is_overdue(deadline, deadline - timedelta(seconds=1)) is False


def test_next_season_world_is_seed_baseline_plus_seal() -> None:
    assert WORLD_BASELINE == {"poblacion": 68, "comida": 41, "moral": 55, "defensa": 72, "oro": 36}
    assert next_season_world({"comida": 15}) == {**WORLD_BASELINE, "comida": 56}


def test_next_season_world_is_clamped_and_does_not_mutate_baseline() -> None:
    world = next_season_world({"defensa": 40})

    assert world["defensa"] == 100
    assert WORLD_BASELINE["defensa"] == 72
