"""Fase B: La Última Luz de principio a fin vía el cierre diario (BD de tests).

Se simulan los días inyectando `now` en run_daily_close: colapso + 7 días →
arranca el evento → una ronda por día → ganador → sello → Temporada N+1.
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.battle_royale import BattleRoyaleEvent, BrEventStatus, BrSeal, BrTactic, Champion, Duel
from app.models.season import Season, SeasonPhase
from app.models.user import User
from app.services.battle_royale.lifecycle import BrStep, event_for_season
from app.services.battle_royale.resolution import MAX_WOUNDS
from app.services.battle_royale.seals import SealForbidden, SealNotAvailable, apply_seal
from app.services.battle_royale.voting import cast_tactic_vote
from app.services.battle_royale.zones import ARENA, FALL_ORDER
from app.services.daily_cycle import run_daily_close
from app.services.daily_decision import BattleRoyaleInProgress, ensure_decision_for_today
from app.services.season import WORLD_BASELINE, get_active_season, get_world_state, world_stats
from app.services.sponsorship import sponsor_member
from tests.br_support import faction, make_season, member

pytestmark = pytest.mark.integration

COLAPSO_START = datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc)
START_DAY = date(2026, 12, 8)  # colapso + 7 días


def _close_of(day: date) -> datetime:
    return datetime.combine(day, time(23, 59), tzinfo=timezone.utc)


def _round_close(round_number: int) -> datetime:
    return _close_of(START_DAY + timedelta(days=round_number))


@pytest.fixture()
def season(db: Session) -> Season:
    return make_season(db, 960, SeasonPhase.colapso, COLAPSO_START)


@pytest.fixture()
def three_factions(db: Session, season: Season) -> dict[str, User]:
    """Dos miembros por facción; campeones: gremio y culto por patrocinio, orden por saldo."""
    gremio, orden, culto = (faction(db, slug) for slug in ("gremio", "orden", "culto"))
    users = {
        "g1": member(db, gremio, chispas=10)[0],
        "g2": member(db, gremio)[0],
        "o1": member(db, orden, chispas=20)[0],
        "o2": member(db, orden)[0],
        "c1": member(db, culto, chispas=5)[0],
        "c2": member(db, culto)[0],
    }
    sponsor_member(db, season, users["g1"], users["g2"].id, 5, now=COLAPSO_START + timedelta(days=1))
    sponsor_member(db, season, users["c1"], users["c2"].id, 2, now=COLAPSO_START + timedelta(days=2))
    return users


def _event(db: Session, season: Season) -> BattleRoyaleEvent:
    db.expire_all()
    event = event_for_season(db, season)
    assert event is not None
    return event


def _champion_user_ids(db: Session, event: BattleRoyaleEvent) -> set:
    return {champion.user_id for champion in db.query(Champion).filter(Champion.event_id == event.id).all()}


def _current_duel(db: Session, event: BattleRoyaleEvent) -> Duel:
    return db.query(Duel).filter(Duel.event_id == event.id, Duel.round_number == event.round_number).one()


def test_event_does_not_start_before_seven_days_of_colapso(db: Session, season: Season, three_factions) -> None:
    result = run_daily_close(db, now=_close_of(START_DAY) - timedelta(days=1))

    assert result.battle_royale is None
    assert event_for_season(db, season) is None


def test_event_starts_after_seven_days_with_sponsored_champions(
    db: Session, season: Season, three_factions
) -> None:
    result = run_daily_close(db, now=_close_of(START_DAY))

    event = _event(db, season)
    users = three_factions
    assert result.battle_royale == BrStep.started
    assert result.phase == SeasonPhase.colapso
    assert event.status == BrEventStatus.active and event.round_number == 1
    assert _champion_user_ids(db, event) == {users["g2"].id, users["o1"].id, users["c2"].id}
    duel = _current_duel(db, event)
    assert duel.zone == "bahia" and duel.resolves_on == START_DAY + timedelta(days=1)


def test_event_needs_two_factions_with_members(db: Session, season: Season) -> None:
    member(db, faction(db, "gremio"))

    result = run_daily_close(db, now=_close_of(START_DAY))

    assert result.battle_royale == BrStep.waiting
    assert event_for_season(db, season) is None
    assert result.phase == SeasonPhase.colapso


def test_daily_job_is_idempotent_within_a_day(db: Session, season: Season, three_factions) -> None:
    run_daily_close(db, now=_close_of(START_DAY))
    again = run_daily_close(db, now=_close_of(START_DAY) + timedelta(seconds=30))
    first = run_daily_close(db, now=_round_close(1))
    repeat = run_daily_close(db, now=_round_close(1) + timedelta(seconds=30))

    event = _event(db, season)
    assert again.battle_royale == BrStep.waiting
    assert first.battle_royale == BrStep.round_resolved
    assert repeat.battle_royale == BrStep.waiting
    assert event.round_number == 2 and event.fallen_zones == ["bahia"]


def test_no_daily_decision_while_the_event_runs(db: Session, season: Season, three_factions) -> None:
    run_daily_close(db, now=_close_of(START_DAY))

    with pytest.raises(BattleRoyaleInProgress):
        ensure_decision_for_today(db, season, today=START_DAY + timedelta(days=1))


def _vote_round(db: Session, event: BattleRoyaleEvent, users: dict[str, User]) -> None:
    duel = _current_duel(db, event)
    alive_rows = db.query(Champion).filter(Champion.event_id == event.id, Champion.wounds < MAX_WOUNDS)
    alive = {champion.user_id for champion in alive_rows}
    ballots = {"g1": BrTactic.ataque, "g2": BrTactic.ataque, "o1": BrTactic.defensa}
    for key, tactic in ballots.items():
        champion_of_faction_alive = any(
            db.get(User, uid).faction_id == users[key].faction_id for uid in alive
        )
        if champion_of_faction_alive:
            cast_tactic_vote(db, duel.id, users[key], tactic, 0)


def test_early_elimination_ends_the_event_and_the_seal_opens_the_next_season(
    db: Session, season: Season, three_factions
) -> None:
    users = three_factions
    run_daily_close(db, now=_close_of(START_DAY))

    # Gremio: 2 votos/2 miembros = 1.0 · Orden: 1/2 = 0.5, pero defensa vence a ataque → 0.575 · Culto: 0.
    wounded_order = []
    for round_number in range(1, 7):
        event = _event(db, season)
        _vote_round(db, event, users)
        run_daily_close(db, now=_round_close(round_number))
        duel = db.query(Duel).filter(Duel.event_id == event.id, Duel.round_number == round_number).one()
        wounded_order.append(duel.result["wounded"])

    event = _event(db, season)
    assert wounded_order == ["culto"] * 3 + ["orden"] * 3
    assert event.status == BrEventStatus.finished and event.round_number == 6  # sin llegar a la Arena
    assert event.fallen_zones == list(FALL_ORDER)
    assert event.winner_faction_id == faction(db, "gremio").id
    scores = {c.faction_id: c.total_score for c in db.query(Champion).filter(Champion.event_id == event.id)}
    assert scores[faction(db, "gremio").id] == pytest.approx(6.0)
    assert scores[faction(db, "orden").id] == pytest.approx(3.45)

    with pytest.raises(SealForbidden):
        apply_seal(db, event.id, BrSeal.abundancia, _round_close(6), chosen_by=users["g1"])
    new_season = apply_seal(db, event.id, BrSeal.abundancia, _round_close(6), chosen_by=users["g2"])

    db.expire_all()
    assert get_active_season(db).id == new_season.id
    assert new_season.number == 961 and new_season.name == "Temporada 961"
    assert new_season.phase == SeasonPhase.construccion
    assert db.get(Season, season.id).is_active is False
    assert world_stats(get_world_state(db, new_season)) == {**WORLD_BASELINE, "comida": 56}
    assert db.get(User, users["o1"].id).chispas == 20  # las Chispas persisten
    assert db.get(User, users["g2"].id).faction_id == faction(db, "gremio").id
    with pytest.raises(SealNotAvailable):
        apply_seal(db, event.id, BrSeal.oro, _round_close(6), chosen_by=users["g2"])


def _duels(db: Session, event: BattleRoyaleEvent) -> list[Duel]:
    return db.query(Duel).filter(Duel.event_id == event.id).order_by(Duel.round_number).all()


def test_balanced_factions_reach_the_arena_and_cumulative_score_decides(db: Session, season: Season) -> None:
    # Un miembro por facción: participación = peso. Rondas 1–6: gremio 7, orden 6, culto 6
    # (6/7 ≈ 0.857 ≥ 0.85: nadie herido). Ronda 7: culto gana el duelo final (10) pero
    # gremio suma más en total: 49 frente a 46 (culto) y 42 (orden).
    users = {slug: member(db, faction(db, slug), chispas=100)[0] for slug in ("gremio", "orden", "culto")}
    run_daily_close(db, now=_close_of(START_DAY))
    weights_by_round = {r: {"gremio": 7, "orden": 6, "culto": 6} for r in range(1, 7)}
    weights_by_round[7] = {"gremio": 7, "orden": 6, "culto": 10}

    steps = []
    for round_number, weights in weights_by_round.items():
        duel = _current_duel(db, _event(db, season))
        for slug, weight in weights.items():
            cast_tactic_vote(db, duel.id, users[slug], BrTactic.ataque, weight - 1)
        steps.append(run_daily_close(db, now=_round_close(round_number)).battle_royale)

    event = _event(db, season)
    duels = _duels(db, event)
    champions = {c.faction_id: c for c in db.query(Champion).filter(Champion.event_id == event.id)}
    assert steps == [BrStep.round_resolved] * 7
    assert [d.zone for d in duels] == [*FALL_ORDER, ARENA]
    assert event.fallen_zones == list(FALL_ORDER)
    assert [d.result["wounded"] for d in duels] == [None] * 7
    assert [d.result["reason"] for d in duels] == ["within_gap"] * 6 + ["final_round"]
    assert all(c.wounds == 0 for c in champions.values())
    assert champions[faction(db, "gremio").id].total_score == pytest.approx(49.0)
    assert champions[faction(db, "culto").id].total_score == pytest.approx(46.0)
    assert event.status == BrEventStatus.finished and event.round_number == 7
    assert event.winner_faction_id == faction(db, "gremio").id


def test_arena_final_with_wounds_only_counts_survivors(db: Session, season: Season) -> None:
    # Culto no vota nunca: 0 < 0.85 · 1 → herido en rondas 1–3 y eliminado. Gremio y orden
    # empatan a 1.0 hasta la Arena (sin heridas); el empate a puntos lo rompe el slug.
    users = {slug: member(db, faction(db, slug))[0] for slug in ("gremio", "orden")}
    member(db, faction(db, "culto"))
    run_daily_close(db, now=_close_of(START_DAY))

    for round_number in range(1, 8):
        duel = _current_duel(db, _event(db, season))
        for user in users.values():
            cast_tactic_vote(db, duel.id, user, BrTactic.ataque, 0)
        run_daily_close(db, now=_round_close(round_number))

    event = _event(db, season)
    assert [d.result["wounded"] for d in _duels(db, event)] == ["culto"] * 3 + [None] * 4
    assert event.fallen_zones == list(FALL_ORDER)
    assert event.winner_faction_id == faction(db, "gremio").id


def test_nobody_voting_reaches_the_arena_and_the_seal_defaults_to_eco(db: Session, season: Season) -> None:
    for slug in ("gremio", "orden", "culto"):
        member(db, faction(db, slug))
    run_daily_close(db, now=_close_of(START_DAY))
    for round_number in range(1, 8):
        run_daily_close(db, now=_round_close(round_number))

    waiting = run_daily_close(db, now=_round_close(7) + timedelta(hours=23))
    sealed = run_daily_close(db, now=_round_close(8))

    db.expire_all()
    event = _event(db, season)
    new_season = get_active_season(db)
    assert event.winner_faction_id == faction(db, "culto").id  # empate total: primer slug
    assert waiting.battle_royale == BrStep.waiting
    assert sealed.battle_royale == BrStep.sealed and sealed.phase == SeasonPhase.construccion
    assert event.seal == BrSeal.eco and event.sealed_by_id is None
    assert event.next_season_id == new_season.id
    assert world_stats(get_world_state(db, new_season)) == {**WORLD_BASELINE, "moral": 70}


def test_late_seal_is_only_allowed_for_admins(db: Session, season: Season) -> None:
    for slug in ("gremio", "orden"):
        member(db, faction(db, slug))
    admin, _ = member(db, None, is_admin=True)
    run_daily_close(db, now=_close_of(START_DAY))
    for round_number in range(1, 8):
        run_daily_close(db, now=_round_close(round_number))
    event = _event(db, season)
    winner = (
        db.query(Champion)
        .filter(Champion.event_id == event.id, Champion.faction_id == event.winner_faction_id)
        .one()
    )
    late = event.seal_deadline + timedelta(minutes=1)

    with pytest.raises(SealForbidden):
        apply_seal(db, event.id, BrSeal.oro, late, chosen_by=db.get(User, winner.user_id))
    new_season = apply_seal(db, event.id, BrSeal.oro, late, chosen_by=admin)

    assert world_stats(get_world_state(db, new_season))["oro"] == 51
