import pytest

from app.services.world_effects import STAT_KEYS, apply_effects

BASE_STATS = {"poblacion": 50, "comida": 50, "moral": 50, "defensa": 50, "oro": 50}


def test_applies_positive_and_negative_deltas():
    result = apply_effects(BASE_STATS, {"comida": 8, "oro": -5})

    assert result["comida"] == 58
    assert result["oro"] == 45
    assert result["moral"] == 50


def test_does_not_mutate_input_stats():
    stats = dict(BASE_STATS)

    apply_effects(stats, {"comida": 8})

    assert stats == BASE_STATS


def test_returns_a_new_object():
    result = apply_effects(BASE_STATS, {})

    assert result == BASE_STATS
    assert result is not BASE_STATS


def test_clamps_values_to_upper_bound():
    stats = {**BASE_STATS, "defensa": 95}

    result = apply_effects(stats, {"defensa": 20})

    assert result["defensa"] == 100


def test_clamps_values_to_lower_bound():
    stats = {**BASE_STATS, "oro": 3}

    result = apply_effects(stats, {"oro": -10})

    assert result["oro"] == 0


def test_clamps_out_of_range_input_even_without_effects():
    stats = {**BASE_STATS, "moral": 140, "comida": -7}

    result = apply_effects(stats, {})

    assert result["moral"] == 100
    assert result["comida"] == 0


def test_result_always_contains_the_five_stats():
    result = apply_effects(BASE_STATS, {"poblacion": 1})

    assert set(result) == set(STAT_KEYS)


def test_rejects_unknown_stat_in_effects():
    with pytest.raises(ValueError, match="desconocida"):
        apply_effects(BASE_STATS, {"magia": 5})


def test_rejects_non_integer_delta():
    with pytest.raises(ValueError, match="entero"):
        apply_effects(BASE_STATS, {"oro": "5"})


def test_rejects_missing_stat_in_input():
    incomplete = {k: v for k, v in BASE_STATS.items() if k != "oro"}

    with pytest.raises(ValueError, match="oro"):
        apply_effects(incomplete, {"comida": 1})
