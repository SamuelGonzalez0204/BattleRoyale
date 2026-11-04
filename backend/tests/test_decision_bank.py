"""Reglas de calidad del banco de plantillas de la Fase E (app/data/decision_bank.py)."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from app.data.decision_bank import BANK_TEMPLATES, LEGACY_REGIONS
from app.data.regions import REGION_IDS, REGION_NAMES, region_name
from app.models.season import SeasonPhase
from app.models.user import UserRole
from app.services.world_effects import STAT_KEYS, validate_effects

PER_PHASE = 15
MAX_QUESTION = 160
MAX_OPTION = 60
MAX_DELTA = 10
MAX_NET = 3
# Huella del snapshot que siembra la migración 0008. Si cambia, la historia de las
# migraciones cambiaría también: los textos nuevos van en una migración nueva.
SNAPSHOT_SHA256 = "d4da01272babdda0a5f299f100fdcc47131fcf3469703540114da1fe69b6e4e2"
MAP_DATA = Path(__file__).resolve().parents[2] / "frontend" / "public" / "mapa" / "map-data.json"


def _effects():
    for template in BANK_TEMPLATES:
        yield template["order"], template["effects_a"]
        yield template["order"], template["effects_b"]


def _dominates(first: dict[str, int], second: dict[str, int]) -> bool:
    stats = set(first) | set(second)
    return all(first.get(stat, 0) >= second.get(stat, 0) for stat in stats)


def test_bank_has_fifteen_templates_per_phase() -> None:
    counts = Counter(template["phase"] for template in BANK_TEMPLATES)

    assert counts == {phase.value: PER_PHASE for phase in SeasonPhase}
    assert len(BANK_TEMPLATES) >= 60


def test_orders_and_questions_are_unique_and_follow_the_legacy_bank() -> None:
    orders = [template["order"] for template in BANK_TEMPLATES]
    questions = [template["question"] for template in BANK_TEMPLATES]

    assert len(set(orders)) == len(orders)
    assert len(set(questions)) == len(questions)
    assert min(orders) > max(LEGACY_REGIONS)


def test_every_template_is_anchored_to_a_known_region() -> None:
    assert {template["region"] for template in BANK_TEMPLATES} <= set(REGION_IDS)
    assert set(LEGACY_REGIONS.values()) <= set(REGION_IDS)
    assert sorted(LEGACY_REGIONS) == list(range(1, 9))


def test_texts_respect_length_limits() -> None:
    for template in BANK_TEMPLATES:
        assert len(template["question"]) <= MAX_QUESTION, template["order"]
        assert len(template["option_a"]) <= MAX_OPTION, template["order"]
        assert len(template["option_b"]) <= MAX_OPTION, template["order"]
        assert template["option_a"] != template["option_b"]


@pytest.mark.parametrize(("order", "effects"), list(_effects()))
def test_effects_are_valid_small_trade_offs(order: int, effects: dict[str, int]) -> None:
    validate_effects(effects)
    assert 2 <= len(effects) <= 3, order
    assert all(0 < abs(delta) <= MAX_DELTA for delta in effects.values()), order
    assert any(delta > 0 for delta in effects.values()), order
    assert any(delta < 0 for delta in effects.values()), order
    assert abs(sum(effects.values())) <= MAX_NET, order


def test_no_option_dominates_the_other_on_every_stat() -> None:
    for template in BANK_TEMPLATES:
        a, b = template["effects_a"], template["effects_b"]
        assert not _dominates(a, b), f"A domina a B en {template['order']}"
        assert not _dominates(b, a), f"B domina a A en {template['order']}"


def test_role_affinity_is_balanced_within_each_phase() -> None:
    for phase in SeasonPhase:
        roles = Counter(t["role_affinity"] for t in BANK_TEMPLATES if t["phase"] == phase.value)
        assert set(roles) == {role.value for role in UserRole}, phase
        assert max(roles.values()) - min(roles.values()) <= 1, (phase, roles)


def test_role_affinity_is_balanced_across_the_whole_bank() -> None:
    roles = Counter(template["role_affinity"] for template in BANK_TEMPLATES)

    assert max(roles.values()) - min(roles.values()) <= 1


def test_only_known_stats_are_used() -> None:
    for _, effects in _effects():
        assert set(effects) <= set(STAT_KEYS)


def test_snapshot_is_frozen() -> None:
    canonical = json.dumps(
        {"bank": BANK_TEMPLATES, "legacy": LEGACY_REGIONS}, ensure_ascii=False, sort_keys=True
    )
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == SNAPSHOT_SHA256


def test_region_name_returns_the_map_name_or_none() -> None:
    assert region_name("campos") == "Campos y Molinos"
    assert region_name(None) is None
    assert region_name("atlantida") is None


def test_region_names_mirror_map_data() -> None:
    if not MAP_DATA.exists():
        pytest.skip("map-data.json no está disponible en este entorno (p. ej. dentro del contenedor)")
    regions = json.loads(MAP_DATA.read_text(encoding="utf-8"))["regions"]

    assert {region["id"]: region["name"] for region in regions} == REGION_NAMES
