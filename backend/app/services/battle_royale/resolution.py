"""Resolución pura de un duelo de La Última Luz y del ganador del evento.

Reglas (Fase B):
- Participación de una facción = suma de pesos de sus votos / nº de miembros
  (0 si no tiene miembros). Peso de cada voto = 1 + Chispas gastadas.
- Táctica de la facción = mayoría ponderada; empates por TACTIC_ORDER
  (ataque > defensa > astucia). Sin votos, la facción no tiene táctica: ni gana
  ni pierde el triángulo y su puntuación es 0.
- Triángulo: ataque vence a astucia, astucia a defensa, defensa a ataque. Cada
  rival vivo vencido multiplica la puntuación por WIN_MULTIPLIER (1.15).
- Rondas 1–6: la facción con MENOR puntuación (empate: la del campeón más
  herido; si sigue, la primera por slug) recibe una herida SOLO si su puntuación
  queda por debajo de WOUND_GAP_RATIO (85 %) de la mejor de la ronda. Si está
  dentro del margen, nadie es herido (reason "within_gap").
- Ronda 7 (la Arena, cumbres): duelo final sin heridas (reason "final_round");
  sus puntuaciones se suman al total acumulado de cada campeón.
- Un campeón cae con MAX_WOUNDS (3) heridas.
- El evento acaba cuando queda un único campeón vivo o tras la ronda final; gana
  el vivo con más puntuación acumulada (empate: menos heridas, luego slug).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.services.battle_royale.zones import TOTAL_ROUNDS

TACTIC_ORDER: tuple[str, ...] = ("ataque", "defensa", "astucia")
BEATS: dict[str, str] = {"ataque": "astucia", "astucia": "defensa", "defensa": "ataque"}
WIN_MULTIPLIER = 1.15
MAX_WOUNDS = 3
# El último solo es herido si puntúa por debajo de este porcentaje del primero.
WOUND_GAP_RATIO = 0.85
# Se redondea antes de comparar para que el ruido de coma flotante no rompa empates.
SCORE_PRECISION = 6

REASON_BELOW_GAP = "below_gap"
REASON_WITHIN_GAP = "within_gap"
REASON_FINAL_ROUND = "final_round"
REASON_NO_CONTENDERS = "no_contenders"


@dataclass(frozen=True)
class Contender:
    """Facción con campeón vivo en el duelo: miembros, heridas y pesos por táctica."""

    faction_slug: str
    members: int
    wounds: int
    tactic_weights: Mapping[str, int]


@dataclass(frozen=True)
class FactionOutcome:
    faction_slug: str
    tactic: str | None
    total_weight: int
    participation: float
    wins: int
    score: float
    wounded: bool


@dataclass(frozen=True)
class RoundOutcome:
    outcomes: tuple[FactionOutcome, ...]
    wounded_faction: str | None
    reason: str  # below_gap | within_gap | final_round | no_contenders

    def outcome_for(self, faction_slug: str) -> FactionOutcome:
        for outcome in self.outcomes:
            if outcome.faction_slug == faction_slug:
                return outcome
        raise KeyError(faction_slug)


@dataclass(frozen=True)
class Standing:
    faction_slug: str
    wounds: int
    total_score: float


def participation(total_weight: int, members: int) -> float:
    if members <= 0:
        return 0.0
    return total_weight / members


def _validate_tactics(weights: Mapping[str, int]) -> None:
    unknown = [tactic for tactic in weights if tactic not in TACTIC_ORDER]
    if unknown:
        raise ValueError(f"Táctica desconocida: {', '.join(unknown)}")


def faction_tactic(weights: Mapping[str, int]) -> str | None:
    _validate_tactics(weights)
    known = {tactic: int(weights.get(tactic, 0)) for tactic in TACTIC_ORDER}
    if sum(known.values()) <= 0:
        return None
    return max(TACTIC_ORDER, key=lambda tactic: (known[tactic], -TACTIC_ORDER.index(tactic)))


def beats(tactic: str | None, rival: str | None) -> bool:
    if tactic is None or rival is None:
        return False
    return BEATS[tactic] == rival


def count_wins(tactic: str | None, rival_tactics: Iterable[str | None]) -> int:
    return sum(1 for rival in rival_tactics if beats(tactic, rival))


def pick_wounded(scores: Mapping[str, float], wounds: Mapping[str, int]) -> str | None:
    if not scores:
        return None
    return min(scores, key=lambda slug: (round(scores[slug], SCORE_PRECISION), -wounds.get(slug, 0), slug))


def _score(base: float, wins: int) -> float:
    return round(base * WIN_MULTIPLIER**wins, SCORE_PRECISION)


def is_below_gap(score: float, best: float) -> bool:
    """¿La puntuación queda por debajo de WOUND_GAP_RATIO de la mejor? (exacto al 85 % no)."""
    return round(score, SCORE_PRECISION) < round(best * WOUND_GAP_RATIO, SCORE_PRECISION)


def decide_wound(
    scores: Mapping[str, float], wounds: Mapping[str, int], is_final: bool
) -> tuple[str | None, str]:
    """(facción herida o None, motivo) según la regla del margen y la ronda final."""
    if not scores:
        return None, REASON_NO_CONTENDERS
    if is_final:
        return None, REASON_FINAL_ROUND
    lowest = pick_wounded(scores, wounds)
    if lowest is not None and is_below_gap(scores[lowest], max(scores.values())):
        return lowest, REASON_BELOW_GAP
    return None, REASON_WITHIN_GAP


def resolve_round(contenders: Sequence[Contender], is_final: bool = False) -> RoundOutcome:
    """Resuelve un duelo entre todos los campeones vivos. `is_final` = la ronda de la
    Arena: puntúa pero no hiere. No toca nada fuera."""
    ordered = sorted(contenders, key=lambda contender: contender.faction_slug)
    tactics = {item.faction_slug: faction_tactic(item.tactic_weights) for item in ordered}
    partial: list[tuple[Contender, int, float, int, float]] = []
    for item in ordered:
        total = sum(int(weight) for weight in item.tactic_weights.values())
        base = participation(total, item.members)
        rivals = [tactics[other.faction_slug] for other in ordered if other.faction_slug != item.faction_slug]
        wins = count_wins(tactics[item.faction_slug], rivals)
        partial.append((item, total, base, wins, _score(base, wins)))

    wounded, reason = decide_wound(
        {item.faction_slug: score for item, *_, score in partial},
        {item.faction_slug: item.wounds for item in ordered},
        is_final,
    )
    outcomes = tuple(
        FactionOutcome(
            faction_slug=item.faction_slug,
            tactic=tactics[item.faction_slug],
            total_weight=total,
            participation=round(base, SCORE_PRECISION),
            wins=wins,
            score=score,
            wounded=item.faction_slug == wounded,
        )
        for item, total, base, wins, score in partial
    )
    return RoundOutcome(outcomes=outcomes, wounded_faction=wounded, reason=reason)


def is_alive(wounds: int) -> bool:
    return wounds < MAX_WOUNDS


def event_is_over(alive_count: int, round_number: int) -> bool:
    """Tras resolver `round_number`: ¿se acabó el evento?"""
    return alive_count <= 1 or round_number >= TOTAL_ROUNDS


def pick_event_winner(standings: Sequence[Standing]) -> str | None:
    alive = [standing for standing in standings if is_alive(standing.wounds)]
    if not alive:
        return None
    best = min(
        alive,
        key=lambda item: (-round(item.total_score, SCORE_PRECISION), item.wounds, item.faction_slug),
    )
    return best.faction_slug
