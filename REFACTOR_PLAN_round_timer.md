# Refactor plan: replace the reveal button with a 30-second round timer

## Goal

The wrangler no longer clicks **Reveal**. Instead they press **Start**, a
30-second countdown runs for everyone, and when it hits zero every client goes
to the scoreboard. Only answers already submitted are locked in for the herd
grouping; late answers are accepted but arrive after the clock and are recorded
the same way as any other answer (see step 6).

Decisions confirmed:

- The countdown starts when the **wrangler** presses Start (or Next round),
  not on first login.
- At zero, everyone goes straight to the scoreboard.
- Answers after zero are discarded for the current round — they were not locked
  in, so a player who misses the window appears under "Did not answer".
- Timers do not need to be in lockstep between clients; polling is fine.

## Current design, and what has to change

Right now "the round is over" is a single boolean, `Game_State["revealed"]`,
flipped by `POST /game/reveal`. That one flag drives five things: the
`current_page()` redirects, `/game`, `/game/answered`, `/game/scoreboard`, and
the `/game/status` payload.

The timer needs a *deadline* instead of a flag. The deadline is a timestamp on
the server, compared against `time.time()`, so nobody has to trust a client
clock. Keeping `revealed` as the source of truth would mean either a
background task or a write on every request, so this plan replaces it with a
derived check.

## 1. State: `herd_mentality/state.py`

Replace the `revealed` boolean with:

```python
"round_ends_at": None,   # epoch seconds; None while the round is not running
```

- `None` = the round has not been started (or the round is over).
- A float = the round is running and answers are open until that time.

`conftest.py`'s reset fixture swaps `revealed` for `round_ends_at = None`.

## 2. New module: `herd_mentality/rounds.py`

Keep the clock logic out of the routes, mirroring how `questions.py` keeps
prompt selection separate:

```python
ROUND_SECONDS = 30

def round_deadline(now: float | None = None) -> float:
    """The timestamp a round started now should end at."""

def seconds_left(round_ends_at: float | None, now: float | None = None) -> int:
    """Whole seconds remaining, clamped at zero; 0 when no round is running."""

def round_is_over(round_ends_at: float | None, now: float | None = None) -> bool:
    """True once the deadline has passed (or none was ever set)."""
```

`now` is injectable so tests never sleep. `main.py` passes
`time.time()` by default.

## 3. Routes: `herd_mentality/main.py`

**Remove `POST /game/reveal` entirely.** Leftover bookmarks to it will hit the
404 handler and land on whichever page the state says is right, which is the
existing behaviour for unknown URLs.

**New `POST /game/start`** (wrangler only):

- Non-wrangler: redirect to `/game` and start nothing.
- Wrangler: set `Game_State["round_ends_at"] = round_deadline()` and redirect
  to `/game`.
- Calling it again *restarts* the 30 seconds — useful if the host hits Start
  by accident. Answers already given are kept.

**`POST /game/next-round`** (wrangler only) keeps its job of clearing answers
and advancing `round`, plus it now starts the clock:

```python
Game_State["answers"] = {}
Game_State["round"] += 1
start_round()                              # new prompt
Game_State["round_ends_at"] = round_deadline()   # new: begin the countdown
```

**Redirect helper:** add

```python
def answered_page() -> str:
    """Where a player who has answered belongs, now or after the clock."""
    return "/game/scoreboard" if round_is_over(Game_State["round_ends_at"]) else "/game/answered"
```

and use it in `root` and `current_page` so the "round just ended" transition is
handled in one place.

**`GET /game`**:

- If the round is over → redirect to `/game/scoreboard`.
- If no round is running → render normally, telling the template
  `round_started=False` so it shows "Waiting for the wrangler to start".
- Otherwise pass `question`, `seconds_left`, and `round`.

**`POST /game/answer`**:

- Answers are accepted while the round is running.
- If the round is over when the answer arrives, do **not** record it — redirect
  to the scoreboard instead, so the herd grouping is what everyone agreed on.
- If the round never started, redirect back to `/game`.

**`GET /game/answered`**: unchanged except it redirects to the scoreboard once
the round is over, and passes `seconds_left` so the waiting page can show the
countdown next to its cow fact.

**`GET /game/scoreboard`**: redirects to the answered page (or `/game` if not
answered and the round is still running) only while the clock is running.

**`GET /game/status`**: grows one field so the pages can poll for everything at
once without a separate timer endpoint:

```json
{"revealed": false, "round": 0, "seconds_left": 27}
```

`revealed` stays in the payload as the derived `round_is_over(...)` value so the
scoreboard, answered page, and any old client script keep working unchanged.

## 4. Who starts the clock

- **First login must not start it**, so remove the `start_round()` call from
  `POST /login` and from the `GET /game` safety net — a round only begins with
  the wrangler's Start.
- The prompt, however, still has to exist for everyone to see before Start, so
  keep `start_round()` (prompt selection only) where it is and add the clock
  separately in `/game/start` and `/game/next-round`.

This is the one structural wrinkle: "round has a prompt" and "round clock is
running" become two independent pieces of state. Document that in
`state.py`.

## 5. Templates

**`templates/game.html`** — two states:

- Round running: prompt, input, and a live `mm:ss` countdown that ticks down
  locally from `seconds_left`. Disable the input and the Submit button when it
  reaches zero, and let the polling script do the redirect.
- Not started: prompt, input disabled, and "Waiting for the wrangler to start".

Countdown script:

```js
let remaining = {{ seconds_left }};
const tick = () => {
    if (remaining <= 0) { /* disable form */ return; }
    render(remaining); remaining -= 1;
};
setInterval(tick, 1000);
```

Because each client counts down independently from the value the server sent,
clocks will drift by a second or two. That is fine: the server decides whether
an answer counts, and all clients redirect on the next poll once
`seconds_left` is 0.

Also add a polling loop to this page (it currently has none) so `Start` reaches
players already sitting on `/game`. Reuse the same 2-second `setInterval` and
`/game/status` call as `answered.html`.

**`templates/answered.html`** — show "Answers close in 0:18" under the answer,
driven by the same `seconds_left` value, and keep the existing poll that sends
the player to the scoreboard when the round ends. Remove the Reveal form.

**`templates/scoreboard.html`** — the wrangler's button stays but is relabelled
**Next round**. No Reveal button anywhere.

## 6. Tests

Delete or rewrite: `tests/test_reveal.py` (all of it — `POST /game/reveal`
no longer exists), and the reveal steps in `tests/test_next_round.py`,
`tests/test_questions.py`, and `tests/test_unknown_routes.py`.

**New `tests/test_round_timer.py`**

- `POST /game/start` as the wrangler sets `round_ends_at` about 30 seconds out.
- `POST /game/start` as a non-wrangler changes nothing and redirects to `/game`.
- `POST /game/start` twice restarts the clock.
- `GET /game/status` reports a `seconds_left` that decreases as time passes
  (pass a fake `now`).
- An answer submitted before the deadline is recorded.
- An answer submitted after the deadline is **not** recorded and redirects to
  the scoreboard.
- Player who never answered appears under "Did not answer" on the scoreboard.
- Before Start, `/game` shows the waiting state and `seconds_left` is 0.
- An answer submitted before Start is not recorded.
- `/game/answered` → scoreboard redirect once the deadline passes.
- `/game` → scoreboard redirect once the deadline passes.
- Unknown URL after the deadline lands on the scoreboard.
- `POST /game/next-round` clears answers, bumps the round, and restarts the
  clock.

**`tests/conftest.py`** — replace `revealed` with `round_ends_at` in the reset
fixture, and add a helper `started_round(seconds=30)` that sets a deadline
relative to a fixed `now` so tests stay fast.

## 7. Docs

- `README.md`: step 3 becomes "Wrangler hits Start. Everyone answers within 30
  seconds. The scoreboard appears automatically."
- Remove any mention of the Reveal button.

## Verification

1. `uv run pytest`.
2. `RELOAD=1 uv run herd-mentality`, log in as wrangler in one browser and a
   player in another.
3. Player's `/game` says "Waiting for the wrangler to start".
4. Wrangler presses Start — both browsers flip to a live countdown within about
   2 seconds.
5. Answer in one browser; the other does not answer. Let the clock run out.
6. Both land on the scoreboard with no button press, and the silent player is
   under "Did not answer".
7. Press Next round — a fresh prompt, a fresh 30 seconds, answers cleared.
8. Reload mid-round in both browsers and confirm the countdown resumes at
   roughly the same point, and that Start is only visible to the wrangler.

## Risks / notes

- **No background scheduler.** Using a deadline timestamp rather than a
  background task means nothing has to wake up at zero; every request just
  compares times. It also survives a reloaded server process badly — an
  in-memory deadline is lost on restart, same as all other game state.
- **Round starts only by the wrangler.** If the wrangler closes their tab
  mid-game, nobody can start the next round. That is already true of Next
  round today, so it does not regress.
- **Clock skew between phones is cosmetic.** The server's check is what counts.
