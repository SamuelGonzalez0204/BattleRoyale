"""Fase B: resolución pura de un duelo de La Última Luz y del ganador del evento."""

import pytest

from app.services.battle_royale.resolution import (
    MAX_WOUNDS,
    WIN_MULTIPLIER,
    WOUND_GAP_RATIO,
    Contender,
    Standing,
    beats,
    count_wins,
    event_is_over,
    faction_tactic,
    is_alive,
    participation,
    pick_event_winner,
    pick_wounded,
    resolve_round,
)


def _contender(slug: str, members: int = 1, wounds: int = 0, **weights: int) -> Contender:
    return Contender(faction_slug=slug, members=members, wounds=wounds, tactic_weights=weights)


# --- Participación y táctica -------------------------------------------------


def test_participation_is_total_weight_over_members() -> None:
    assert participation(total_weight=9, members=3) == 3.0
    assert participation(total_weight=1, members=4) == 0.25


def test_participation_is_zero_without_members() -> None:
    assert participation(total_weight=5, members=0) == 0.0


def test_faction_tactic_is_weighted_majority() -> None:
    assert faction_tactic({"ataque": 2, "defensa": 5, "astucia": 1}) == "defensa"


def test_faction_tactic_ties_follow_ataque_defensa_astucia() -> None:
    assert faction_tactic({"ataque": 3, "defensa": 3}) == "ataque"
    assert faction_tactic({"defensa": 2, "astucia": 2}) == "defensa"


def test_faction_tactic_is_none_without_votes() -> None:
    assert faction_tactic({}) is None
    assert faction_tactic({"ataque": 0}) is None


def test_faction_tactic_rejects_unknown_tactics() -> None:
    with pytest.raises(ValueError):
        faction_tactic({"magia": 3})


@pytest.mark.parametrize(
    ("winner", "loser"),
    [("ataque", "astucia"), ("astucia", "defensa"), ("defensa", "ataque")],
)
def test_tactic_triangle(winner: str, loser: str) -> None:
    assert beats(winner, loser) is True
    assert beats(loser, winner) is False
    assert beats(winner, winner) is False


def test_no_tactic_never_wins_nor_loses() -> None:
    assert beats(None, "ataque") is False
    assert beats("ataque", None) is False


def test_count_wins_counts_each_beaten_rival() -> None:
    assert count_wins("ataque", ["astucia", "astucia", "defensa"]) == 2
    assert count_wins(None, ["astucia"]) == 0


# --- Resolución de una ronda -------------------------------------------------


def test_lowest_score_takes_the_wound() -> None:
    outcome = resolve_round(
        [
            _contender("gremio", members=2, ataque=6),  # 3.0
            _contender("orden", members=2, ataque=4),  # 2.0
            _contender("culto", members=2, ataque=2),  # 1.0
        ]
    )

    assert outcome.wounded_faction == "culto"
    assert outcome.outcome_for("culto").wounded is True
    assert outcome.outcome_for("gremio").wounded is False
    assert outcome.outcome_for("gremio").score == 3.0


def test_each_beaten_rival_multiplies_the_score() -> None:
    outcome = resolve_round(
        [
            _contender("gremio", members=1, ataque=10),
            _contender("orden", members=1, astucia=10),
            _contender("culto", members=1, astucia=10),
        ]
    )

    gremio = outcome.outcome_for("gremio")
    assert gremio.wins == 2
    assert gremio.score == pytest.approx(10 * WIN_MULTIPLIER**2)
    assert outcome.outcome_for("orden").wins == 0


def test_tactic_advantage_can_flip_the_ranking() -> None:
    # Orden participa menos (1.8 frente a 2.0) pero su defensa gana al ataque: 1.8 * 1.15 = 2.07.
    # Gremio queda último, pero a menos del 15 % del primero: nadie recibe herida.
    outcome = resolve_round(
        [
            _contender("gremio", members=5, ataque=10),
            _contender("orden", members=5, defensa=9),
        ]
    )

    assert outcome.outcome_for("orden").score > outcome.outcome_for("gremio").score
    assert outcome.wounded_faction is None and outcome.reason == "within_gap"


def test_faction_without_votes_scores_zero_and_has_no_tactic() -> None:
    outcome = resolve_round([_contender("gremio", members=3, ataque=3), _contender("culto", members=3)])

    culto = outcome.outcome_for("culto")
    assert culto.tactic is None and culto.score == 0.0
    assert outcome.wounded_faction == "culto"


def test_score_tie_wounds_the_champion_with_more_wounds() -> None:
    outcome = resolve_round(
        [_contender("gremio", ataque=10), _contender("culto", wounds=0), _contender("orden", wounds=1)]
    )

    assert outcome.wounded_faction == "orden"


def test_full_tie_wounds_the_first_slug_alphabetically() -> None:
    outcome = resolve_round(
        [_contender("zeta", ataque=10), _contender("orden"), _contender("culto"), _contender("gremio")]
    )

    assert outcome.wounded_faction == "culto"


def test_resolution_reports_every_faction_in_slug_order() -> None:
    outcome = resolve_round([_contender("orden", ataque=1), _contender("culto", defensa=2)])

    assert [item.faction_slug for item in outcome.outcomes] == ["culto", "orden"]
    assert outcome.outcome_for("culto").total_weight == 2


def test_resolution_without_contenders_wounds_nobody() -> None:
    assert resolve_round([]).wounded_faction is None


def test_lowest_score_must_trail_the_leader_by_the_gap() -> None:
    assert WOUND_GAP_RATIO == 0.85


@pytest.mark.parametrize(
    ("low", "wounded", "reason"),
    [(84, "culto", "below_gap"), (85, None, "within_gap"), (86, None, "within_gap")],
)
def test_gap_rule_just_below_exactly_at_and_above(low: int, wounded: str | None, reason: str) -> None:
    outcome = resolve_round([_contender("gremio", ataque=100), _contender("culto", ataque=low)])

    assert outcome.wounded_faction == wounded
    assert outcome.reason == reason
    assert outcome.outcome_for("culto").wounded is (wounded == "culto")


def test_nobody_is_wounded_when_nobody_votes() -> None:
    outcome = resolve_round([_contender("gremio"), _contender("culto")])

    assert outcome.wounded_faction is None and outcome.reason == "within_gap"


def test_final_round_scores_but_wounds_nobody() -> None:
    outcome = resolve_round([_contender("gremio", ataque=10), _contender("culto")], is_final=True)

    assert outcome.wounded_faction is None and outcome.reason == "final_round"
    assert outcome.outcome_for("gremio").score == 10.0
    assert not any(item.wounded for item in outcome.outcomes)


def test_wounding_round_reports_below_gap() -> None:
    outcome = resolve_round([_contender("gremio", ataque=10), _contender("culto", ataque=1)])

    assert outcome.reason == "below_gap"


def test_pick_wounded_directly() -> None:
    assert pick_wounded({"a": 1.0, "b": 0.5}, {"a": 0, "b": 0}) == "b"
    assert pick_wounded({}, {}) is None


# --- Fin del evento ----------------------------------------------------------


def test_champion_dies_at_max_wounds() -> None:
    assert MAX_WOUNDS == 3
    assert is_alive(2) is True
    assert is_alive(3) is False


def test_event_is_over_with_one_survivor_or_after_final_round() -> None:
    assert event_is_over(alive_count=1, round_number=3) is True
    assert event_is_over(alive_count=2, round_number=7) is True
    assert event_is_over(alive_count=2, round_number=6) is False


def test_sole_survivor_wins() -> None:
    standings = [Standing("gremio", wounds=1, total_score=1.0), Standing("culto", wounds=3, total_score=9.0)]

    assert pick_event_winner(standings) == "gremio"


def test_highest_cumulative_score_among_survivors_wins() -> None:
    standings = [
        Standing("gremio", wounds=0, total_score=4.0),
        Standing("orden", wounds=1, total_score=6.5),
        Standing("culto", wounds=3, total_score=20.0),
    ]

    assert pick_event_winner(standings) == "orden"


def test_winner_tie_breaks_by_fewer_wounds_then_slug() -> None:
    assert pick_event_winner([Standing("orden", 1, 3.0), Standing("gremio", 0, 3.0)]) == "gremio"
    assert pick_event_winner([Standing("orden", 0, 3.0), Standing("gremio", 0, 3.0)]) == "gremio"


def test_no_survivors_means_no_winner() -> None:
    assert pick_event_winner([Standing("gremio", 3, 1.0)]) is None
