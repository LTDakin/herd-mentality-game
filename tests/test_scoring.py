"""Unit tests for the answer grouping that drives the scoreboard."""

from herd_mentality.scoring import group_answers, normalise


def answers(*pairs):
    return group_answers(list(pairs))


def test_matching_answers_are_grouped_case_insensitively():
    result = answers(("Tai", "Corn"), ("Maggie", "corn"), ("Bob", "CORN"))

    assert len(result["groups"]) == 1
    assert result["groups"][0]["players"] == ["Bob", "Maggie", "Tai"]


def test_extra_whitespace_is_ignored():
    result = answers(("Tai", "ice cream"), ("Maggie", "  ice   cream  "))

    assert len(result["groups"]) == 1
    assert len(result["groups"][0]["players"]) == 2


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
    result = answers(
        ("Tai", "corn"),
        ("Maggie", "corn"),
        ("Bob", "cows"),
    )

    winner = [group for group in result["groups"] if group["is_winner"]]
    assert len(winner) == 1
    assert winner[0]["answer"] == "corn"


def test_tie_for_largest_group_awards_no_medal():
    result = answers(
        ("Tai", "corn"),
        ("Maggie", "corn"),
        ("Bob", "cows"),
        ("Amy", "cows"),
    )

    assert not any(group["is_winner"] for group in result["groups"])


def test_tie_with_a_clear_larger_herd_still_awards_medal():
    result = answers(
        ("Tai", "corn"),
        ("Maggie", "corn"),
        ("Bob", "corn"),
        ("Amy", "cows"),
        ("Dan", "cows"),
        ("Eve", "hay"),
    )

    winner = [group for group in result["groups"] if group["is_winner"]]
    assert len(winner) == 1
    assert winner[0]["answer"] == "corn"


def test_single_player_gets_both_badge_and_medal():
    result = answers(("Tai", "corn"))

    group = result["groups"][0]
    assert group["is_unique"] is True
    assert group["is_winner"] is True


def test_groups_are_sorted_by_popularity():
    result = answers(
        ("A", "hay"),
        ("B", "corn"),
        ("C", "corn"),
        ("D", "corn"),
        ("E", "cows"),
        ("F", "cows"),
    )

    assert [group["answer"] for group in result["groups"]] == [
        "corn",
        "cows",
        "hay",
    ]


def test_equal_sized_groups_are_sorted_alphabetically():
    result = answers(("A", "zebra"), ("B", "apple"))

    assert [group["answer"] for group in result["groups"]] == ["apple", "zebra"]


def test_players_who_did_not_answer_are_separate():
    result = answers(("Tai", "corn"), ("Maggie", "   "))

    assert result["no_answer"] == ["Maggie"]
    assert result["groups"][0]["players"] == ["Tai"]


def test_no_answer_group_never_wins():
    result = answers(("Tai", "corn"), ("Maggie", ""), ("Bob", ""))

    assert result["groups"][0]["is_winner"] is True


def test_empty_round_produces_nothing():
    result = answers()

    assert result == {"groups": [], "no_answer": []}


def test_normalise_collapses_case_and_whitespace():
    assert normalise("  Ice   CREAM ") == "icecream"


def test_normalise_ignores_punctuation():
    assert normalise("Corn!") == "corn"
    assert normalise("corn?") == normalise("corn")


def test_normalise_ignores_word_breaks():
    assert normalise("ice-cream") == "icecream"
    assert normalise("ice cream") == "icecream"
    assert normalise("ice_cream") == "icecream"


def test_normalise_treats_apostrophes_as_nothing():
    assert normalise("farmer's") == "farmers"


def test_punctuation_and_spacing_are_grouped():
    result = answers(
        ("Tai", "ice cream"),
        ("Maggie", "Ice-Cream!"),
        ("Bob", "icecream"),
    )

    assert len(result["groups"]) == 1
    assert result["groups"][0]["players"] == ["Bob", "Maggie", "Tai"]


def test_plural_and_singular_are_grouped():
    result = answers(("Tai", "cow"), ("Maggie", "Cows"), ("Bob", "cow,"))

    assert len(result["groups"]) == 1
    assert result["groups"][0]["players"] == ["Bob", "Maggie", "Tai"]
    assert result["groups"][0]["answer"] == "cow"


def test_words_ending_in_double_s_are_not_singularised():
    result = answers(("Tai", "grass"), ("Maggie", "gras"))

    assert len(result["groups"]) == 2


def test_different_answers_are_still_separate():
    result = answers(("Tai", "corn"), ("Maggie", "cows"))

    assert len(result["groups"]) == 2
    assert all(group["is_unique"] for group in result["groups"])


def test_punctuation_only_answer_counts_as_no_answer():
    result = answers(("Tai", "corn"), ("Maggie", "!!!"))

    assert result["no_answer"] == ["Maggie"]
    assert len(result["groups"]) == 1


def test_plural_merge_can_decide_the_winner():
    result = answers(
        ("Tai", "corn"),
        ("Maggie", "cows"),
        ("Bob", "cow"),
    )

    winner = [group for group in result["groups"] if group["is_winner"]]
    assert len(winner) == 1
    assert winner[0]["answer"] == "cows"
