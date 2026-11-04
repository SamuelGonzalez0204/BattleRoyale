from app.services.daily_decision import pick_winner


def test_option_with_more_weighted_votes_wins():
    assert pick_winner(10, 3) == "a"
    assert pick_winner(2, 7) == "b"


def test_tie_with_votes_goes_to_option_a():
    assert pick_winner(5, 5) == "a"


def test_no_votes_means_no_winner():
    assert pick_winner(0, 0) is None
