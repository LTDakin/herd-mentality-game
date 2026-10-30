"""Pick the prompt the whole herd answers each round."""

import random


def pick_question(
    remaining: list[str], all_questions: list[str], previous: str | None = None
) -> tuple[str, list[str]]:
    """Choose a prompt, avoiding repeats until the list is used up.

    `remaining` is what is left from earlier rounds. When it runs out, a fresh
    shuffled copy of `all_questions` is started with `previous` left out, so the
    same prompt never comes up twice in a row.

    Returns (question, leftover) where leftover is the updated remaining list
    for the caller to store.
    """
    # Copy so the caller's list (and the shared question pool) is never mutated.
    remaining = list(remaining)
    if not remaining:
        remaining = [question for question in all_questions if question != previous]
        random.shuffle(remaining)

    # A one-entry pool (or a previous prompt that is not in the list) can still
    # leave this empty; fall back to the whole list rather than failing.
    if not remaining:
        remaining = list(all_questions)

    return remaining.pop(), remaining
