from app.services.sorting import compute_weights


def test_underrepresented_faction_gets_more_weight():
    # 0 culto, 10 gremio, 10 orden -> culto debe tener el mayor peso
    weights = compute_weights([10, 10, 0], target_share=1 / 3, base_weight=0.15)
    assert weights[2] > weights[0]
    assert weights[2] > weights[1]


def test_balanced_factions_get_equal_weight():
    weights = compute_weights([10, 10, 10], target_share=1 / 3, base_weight=0.15)
    assert weights[0] == weights[1] == weights[2]


def test_no_faction_ever_reaches_zero_weight():
    # incluso una facción ya sobrerrepresentada conserva el peso base
    weights = compute_weights([0, 0, 1000], target_share=1 / 3, base_weight=0.15)
    assert weights[2] == 0.15
    assert all(w > 0 for w in weights)


def test_empty_world_splits_evenly():
    weights = compute_weights([0, 0, 0], target_share=1 / 3, base_weight=0.15)
    assert weights[0] == weights[1] == weights[2]
