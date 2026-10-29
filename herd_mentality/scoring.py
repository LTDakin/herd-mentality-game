"""Group revealed answers so the scoreboard reads like a herd, not a list."""

import re

WHITESPACE = re.compile(r"\s+")


def normalise(answer: str) -> str:
    """Collapse whitespace and case so 'Ice  CREAM' matches 'ice cream'."""
    return WHITESPACE.sub(" ", answer.strip()).casefold()


def group_answers(items: list[tuple[str, str]]) -> dict:
    """Group (player_name, answer) pairs by their normalised answer.

    `items` must be in submission order: the first spelling seen for an answer
    is the one shown, and that group is listed before later-created groups.

    Returns {"groups": [...], "no_answer": [...]} where each group has:
    answer (first spelling), players (sorted names), is_unique, is_winner.
    """
    buckets: dict[str, dict] = {}
    no_answer: list[str] = []

    for player_name, answer in items:
        key = normalise(answer)
        if not key:
            no_answer.append(player_name)
            continue
        bucket = buckets.get(key)
        if bucket is None:
            buckets[key] = {"answer": answer.strip(), "players": [player_name]}
        else:
            bucket["players"].append(player_name)

    groups = list(buckets.values())
    # Most popular first; alphabetical by answer breaks ties so the order is
    # stable between refreshes.
    groups.sort(key=lambda group: (-len(group["players"]), group["answer"].lower()))

    largest = len(groups[0]["players"]) if groups else 0
    # No single winning herd when two answers tie for the biggest group.
    winner_size = largest
    contenders = [group for group in groups if len(group["players"]) == winner_size]
    has_winner = len(contenders) == 1

    for group in groups:
        group["players"] = sorted(group["players"])
        group["is_unique"] = len(group["players"]) == 1
        group["is_winner"] = has_winner and len(group["players"]) == winner_size

    return {"groups": groups, "no_answer": sorted(no_answer)}
