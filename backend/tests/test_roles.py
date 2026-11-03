from app.services.roles import MIN_VOTES_FOR_ROLE, choose_role


def test_no_role_below_vote_threshold():
    counts = {"mercader": MIN_VOTES_FOR_ROLE - 1}

    assert choose_role(counts) is None


def test_role_is_the_most_voted_affinity():
    counts = {"mercader": 1, "guardia": 3, "cronista": 1, "explorador": 0}

    assert choose_role(counts) == "guardia"


def test_threshold_counts_votes_across_all_affinities():
    counts = {"mercader": 2, "guardia": 1, "cronista": 1, "explorador": 1}

    assert choose_role(counts) == "mercader"


def test_tie_is_broken_by_fixed_role_order():
    # mercader > guardia > cronista > explorador
    counts = {"explorador": 3, "cronista": 3}

    assert choose_role(counts) == "cronista"


def test_tie_break_is_independent_of_dict_order():
    first = choose_role({"guardia": 3, "mercader": 3})
    second = choose_role({"mercader": 3, "guardia": 3})

    assert first == second == "mercader"


def test_ignores_unknown_affinities():
    counts = {"pirata": 10, "explorador": 5}

    assert choose_role(counts) == "explorador"


def test_does_not_mutate_input():
    counts = {"guardia": 5}

    choose_role(counts)

    assert counts == {"guardia": 5}
