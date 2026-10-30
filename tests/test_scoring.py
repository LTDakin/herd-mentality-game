"""Unit tests for the answer grouping that drives the scoreboard."""

from herd_mentality.scoring import group_answers, normalise


def answers(*pairs):
    return group_answers(list(pairs))


def winners(result):
    return [group["answer"] for group in result["groups"] if group["is_winner"]]


def test_matching_answers_are_grouped_case_insensitively():
    result = answers(("Tai", "Corn"), ("Maggie", "corn"), ("Bob", "CORN"))

    assert len(result["groups"]) == 1
    assert result["groups"][0]["players"] == ["Bob", "Maggie", "Tai"]


def test_group_uses_first_submitted_spelling():
    result = answers(("Tai", "Corn"), ("Maggie", "corn"))

    assert result["groups"][0]["answer"] == "Corn"


def test_unique_answer_gets_badge():
    result = answers(("Tai", "corn"), ("Maggie", "cows"))

    assert all(group["is_unique"] for group in result["groups"])


def test_shared_answer_is_not_unique():
    result = answers(("Tai", "corn"), ("Maggie", "corn"))

    assert result["groups"][0]["is_unique"] is False


def test_largest_group_is_the_winner():
    result = answers(("Tai", "corn"), ("Maggie", "corn"), ("Bob", "cows"))

    assert winners(result) == ["corn"]


def test_tie_for_largest_group_awards_no_medal():
    result = answers(
        ("Tai", "corn"),
        ("Maggie", "corn"),
        ("Bob", "cows"),
        ("Amy", "cows"),
    )

    assert winners(result) == []


def test_single_player_gets_both_badge_and_medal():
    group = answers(("Tai", "corn"))["groups"][0]

    assert group["is_unique"] is True
    assert group["is_winner"] is True


def test_groups_are_sorted_by_popularity_then_alphabetically():
    result = answers(
        ("A", "hay"),
        ("B", "corn"),
        ("C", "corn"),
        ("D", "corn"),
        ("E", "cows"),
        ("F", "cows"),
        ("G", "zebra"),
        ("H", "apple"),
    )

    assert [group["answer"] for group in result["groups"]] == [
        "corn",
        "cows",
        "apple",
        "hay",
        "zebra",
    ]


def test_players_who_did_not_answer_are_separate():
    result = answers(("Tai", "corn"), ("Maggie", "   "))

    assert result["no_answer"] == ["Maggie"]
    assert result["groups"][0]["players"] == ["Tai"]


def test_punctuation_only_answer_counts_as_no_answer():
    result = answers(("Tai", "corn"), ("Maggie", "!!!"))

    assert result["no_answer"] == ["Maggie"]
    assert len(result["groups"]) == 1


def test_empty_round_produces_nothing():
    assert answers() == {"groups": [], "no_answer": []}


def test_normalise_ignores_case_whitespace_and_punctuation():
    for variant in ["  Ice   CREAM ", "Ice-Cream!", "icecream", "ice_cream"]:
        assert normalise(variant) == "icecream"


def test_normalise_treats_apostrophes_as_nothing():
    assert normalise("farmer's") == "farmers"


def test_plural_and_singular_are_grouped():
    result = answers(("Tai", "cow"), ("Maggie", "Cows"), ("Bob", "cow,"))

    assert len(result["groups"]) == 1
    assert result["groups"][0]["answer"] == "cow"


def test_words_ending_in_double_s_are_not_singularised():
    result = answers(("Tai", "grass"), ("Maggie", "gras"))

    assert len(result["groups"]) == 2


def test_plural_merge_can_decide_the_winner():
    result = answers(("Tai", "corn"), ("Maggie", "cows"), ("Bob", "cow"))

    assert winners(result) == ["cows"]
