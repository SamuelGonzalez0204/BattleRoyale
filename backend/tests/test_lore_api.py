"""GET /api/lore (Fase E3): vista pública combinada para la wiki."""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, BrSeal, Champion
from app.models.decision import Decision
from app.models.season import Season, SeasonPhase
from tests.br_support import STATS, faction, make_season, member

pytestmark = pytest.mark.integration

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
URL = "/api/lore"
DECISIONS_SHOWN = 30


def _closed(db: Session, season: Season, day: date, *, winner: str | None, region: str | None) -> Decision:
    decision = Decision(
        season_id=season.id,
        day=day,
        question=f"¿Qué hacemos el {day.isoformat()}?",
        option_a="Plantar trigo",
        option_b="Vender el grano",
        closes_at=datetime.combine(day, time(23, 59), tzinfo=timezone.utc),
        effects_a={"comida": 5, "oro": -3},
        effects_b={"oro": 4, "comida": -2},
        region=region,
        closed_at=datetime.combine(day, time(23, 59), tzinfo=timezone.utc),
        winner=winner,
    )
    db.add(decision)
    db.commit()
    return decision


def _past_event(db: Session, season: Season) -> tuple[BattleRoyaleEvent, str]:
    orden = faction(db, "orden")
    champion_user, _ = member(db, orden, handle="campeona_lore")
    event = BattleRoyaleEvent(
        season_id=season.id,
        status=BrEventStatus.sealed,
        round_number=7,
        fallen_zones=[],
        started_at=NOW - timedelta(days=40),
        finished_at=NOW - timedelta(days=33),
        winner_faction_id=orden.id,
        seal=BrSeal.muralla,
        sealed_at=NOW - timedelta(days=33),
    )
    db.add(event)
    db.flush()
    db.add(Champion(event_id=event.id, faction_id=orden.id, user_id=champion_user.id))
    db.commit()
    return event, champion_user.handle


def test_is_public_and_shows_current_season_world_and_factions(db: Session, api) -> None:
    make_season(db, 980, SeasonPhase.convergencia, NOW)

    response = api.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["season"] == {"number": 980, "name": "Temporada de pruebas 980", "phase": "convergencia"}
    assert body["world"] == STATS
    slugs = [f["slug"] for f in body["factions"]]
    assert {"gremio", "orden", "culto"} <= set(slugs)
    assert {"members", "influence_pct", "name", "color"} <= set(body["factions"][0])


def test_lists_the_last_thirty_closed_decisions_newest_first(db: Session, api) -> None:
    season = make_season(db, 981, SeasonPhase.colapso, NOW)
    first = date(2026, 10, 1)
    for offset in range(DECISIONS_SHOWN + 2):
        _closed(db, season, first + timedelta(days=offset), winner="a", region="campos")
    _closed(db, season, first + timedelta(days=60), winner="b", region="bahia")
    open_day = first + timedelta(days=61)
    db.add(
        Decision(
            season_id=season.id,
            day=open_day,
            question="¿Abierta?",
            option_a="Sí",
            option_b="No",
            closes_at=datetime.combine(open_day, time(23, 59), tzinfo=timezone.utc),
        )
    )
    db.commit()

    decisions = api.get(URL).json()["decisions"]

    assert len(decisions) == DECISIONS_SHOWN
    assert decisions[0] == {
        "date": (first + timedelta(days=60)).isoformat(),
        "season_number": 981,
        "question": f"¿Qué hacemos el {(first + timedelta(days=60)).isoformat()}?",
        "region": "bahia",
        "region_name": "Bahía del Gremio",
        "winner": "b",
        "winner_option": "Vender el grano",
        "effects_applied": {"oro": 4, "comida": -2},
    }
    assert decisions[1]["winner_option"] == "Plantar trigo"
    assert decisions[1]["region_name"] == "Campos y Molinos"
    days = [d["date"] for d in decisions]
    assert days == sorted(days, reverse=True)


def test_closed_decision_without_votes_applied_nothing(db: Session, api) -> None:
    season = make_season(db, 982, SeasonPhase.construccion, NOW)
    _closed(db, season, date(2026, 11, 20), winner=None, region=None)

    decision = api.get(URL).json()["decisions"][0]

    assert decision["winner"] is None
    assert decision["winner_option"] is None
    assert decision["effects_applied"] == {}
    assert decision["region"] is None and decision["region_name"] is None


def test_lists_past_battle_royale_results(db: Session, api) -> None:
    old = make_season(db, 983, SeasonPhase.colapso, NOW - timedelta(days=60))
    old.is_active = False
    db.commit()
    make_season(db, 984, SeasonPhase.construccion, NOW)
    _, champion_handle = _past_event(db, old)

    results = api.get(URL).json()["battle_royales"]

    assert results[0] == {
        "season_number": 983,
        "winner_faction_slug": "orden",
        "winner_faction_name": "Orden de la Muralla",
        "champion_handle": champion_handle,
        "seal": "muralla",
    }


def test_without_active_season_season_and_world_are_null(db: Session, api) -> None:
    db.query(Season).update({Season.is_active: False})
    db.commit()

    body = api.get(URL).json()

    assert body["season"] is None
    assert body["world"] is None
    assert isinstance(body["decisions"], list)


def test_is_rate_limited_like_other_public_reads(db: Session, api) -> None:
    assert get_settings().rate_limit_public_read == "60/minute"

    codes = [api.get(URL).status_code for _ in range(61)]

    assert 429 not in codes[:60]
    assert codes[60] == 429
