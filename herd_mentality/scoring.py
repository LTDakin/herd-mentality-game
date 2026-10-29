"""Group revealed answers so the scoreboard reads like a herd, not a list."""

import re
import string

WHITESPACE = re.compile(r"\s+")
APOSTROPHES = re.compile(r"['\u2019]")
PUNCTUATION = str.maketrans("", "", string.punctuation)


def normalise(answer: str) -> str:
    """Reduce an answer to the form used for matching.

    Case, whitespace, punctuation and word breaks are ignored, so 'Ice-CREAM!'
    and 'ice cream' both become 'icecream'.
    """
    # Apostrophes go first so "farmer's" and "farmers" agree.
    text = APOSTROPHES.sub("", answer.casefold())
    # Drop punctuation and spaces together so "ice-cream", "ice cream" and
    # "icecream" all collapse to the same word.
    text = WHITESPACE.sub("", text).translate(PUNCTUATION)
    return text


def singular(word: str) -> str:
    """Strip a trailing plural 's', so 'cows' matches 'cow'."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def match_key(answer: str) -> str:
    """The key two answers must share to be scored as the same herd."""
    return singular(normalise(answer))


def group_answers(items: list[tuple[str, str]]) -> dict:
    """Group (player_name, answer) pairs by their matching key.

    `items` must be in submission order: the first spelling seen for an answer
    is the one shown, and that group is listed before later-created groups.

    Returns {"groups": [...], "no_answer": [...]} where each group has:
    answer (first spelling), players (sorted names), is_unique, is_winner.
    """
    buckets: dict[str, dict] = {}
    no_answer: list[str] = []

    for player_name, answer in items:
        whole = normalise(answer)
        if not whole:
            no_answer.append(player_name)
            continue
        key = match_key(answer)
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
