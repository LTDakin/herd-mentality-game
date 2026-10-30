"""In-memory game state, shared by the routes and the auth helpers."""

Game_State = {
    "wrangler": None,
    "player_names": set(),
    "answers": {},
    "round": 0,
    # The prompt every player answers this round, and the prompts not yet used.
    # Both are set when a round's prompt is picked, which is not the same
    # moment the answer clock starts: the wrangler presses Start later.
    "question": None,
    "questions_left": [],
    # The moment the current round's answers close, in epoch seconds. None
    # means no clock is running (never started, or the round is over).
    "round_ends_at": None,
}
