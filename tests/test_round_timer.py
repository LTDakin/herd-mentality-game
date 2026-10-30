"""Tests for the round clock that replaced the wrangler's reveal button.

The clock predicates themselves are covered in test_rounds.py; these tests
drive the routes. Rounds are set up with `start_clock`, which moves the
deadline instead of sleeping.
"""

from fastapi.testclient import TestClient

from herd_mentality.rounds import seconds_left
from herd_mentality.state import Game_State
from round_clock import start_clock


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


def relogin(client: TestClient, name: str):
    """Return to an existing player without hitting the name-taken guard."""
    client.cookies.set("player_name", name)


def play_round(client: TestClient, whos_answering: dict[str, str], view_as: str):
    """Have `whos_answering` answer while the clock runs, then let it run out.

    Leaves the client logged in as `view_as`, ready to read a page as them.
    """
    start_clock()
    for name, answer in whos_answering.items():
        relogin(client, name)
        client.post("/game/answer", data={"answer": answer})
    Game_State["round_ends_at"] = 0
    relogin(client, view_as)


# ---------- Starting the clock ----------


def test_wrangler_start_begins_the_clock(client: TestClient):
    login(client, "alice", wrangler=True)

    response = client.post("/game/start", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"
    assert 0 < seconds_left(Game_State["round_ends_at"]) <= 30


def test_non_wrangler_cannot_start_the_clock(client: TestClient):
    login(client, "alice", wrangler=True)
    login(client, "bob")

    response = client.post("/game/start", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"
    assert Game_State["round_ends_at"] is None


def test_start_requires_login(client: TestClient):
    response = client.post("/game/start", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert Game_State["round_ends_at"] is None


def test_starting_again_restarts_the_clock(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/start")
    # Wind the clock back as if some time had passed, then start again.
    Game_State["round_ends_at"] -= 20

    client.post("/game/start")

    assert seconds_left(Game_State["round_ends_at"]) > 20


def test_starting_keeps_answers_already_given(client: TestClient):
    login(client, "bob")
    start_clock()
    client.post("/game/answer", data={"answer": "cow"})

    relogin(client, "bob")
    client.post("/game/start")

    assert Game_State["answers"] == {"bob": "cow"}


# ---------- Answering against the clock ----------


def test_game_page_waits_before_the_wrangler_starts(logged_in_client: TestClient):
    response = logged_in_client.get("/game", follow_redirects=False)

    assert response.status_code == 200
    assert "Waiting for the wrangler to start" in response.text
    assert "disabled" in response.text


def test_wrangler_sees_the_start_button(client: TestClient):
    login(client, "alice", wrangler=True)

    response = client.get("/game", follow_redirects=False)

    assert 'action="/game/start"' in response.text
    assert "Start the round" in response.text
    # The host waits for nobody, so no waiting message.
    assert "Waiting for the wrangler to start" not in response.text


def test_regular_players_do_not_see_the_start_button(client: TestClient):
    login(client, "alice", wrangler=True)
    client.cookies.clear()
    login(client, "bob")

    response = client.get("/game", follow_redirects=False)

    assert "/game/start" not in response.text
    assert "Waiting for the wrangler to start" in response.text


def test_start_button_goes_once_the_clock_runs(client: TestClient):
    login(client, "alice", wrangler=True)
    start_clock()

    response = client.get("/game", follow_redirects=False)

    assert "/game/start" not in response.text
    assert 'id="timer-value"' in response.text


def test_answer_before_the_deadline_is_recorded(logged_in_client: TestClient):
    start_clock(5)

    logged_in_client.post("/game/answer", data={"answer": "cow"})

    assert Game_State["answers"] == {"alice": "cow"}


def test_answer_after_the_deadline_is_discarded(logged_in_client: TestClient):
    start_clock(-1)

    response = logged_in_client.post(
        "/game/answer", data={"answer": "cow"}, follow_redirects=False
    )

    assert response.headers["location"] == "/game/scoreboard"
    assert Game_State["answers"] == {}


def test_answer_before_the_clock_starts_is_discarded(logged_in_client: TestClient):
    response = logged_in_client.post(
        "/game/answer", data={"answer": "cow"}, follow_redirects=False
    )

    assert response.headers["location"] == "/game"
    assert Game_State["answers"] == {}


def test_silent_player_appears_under_did_not_answer(client: TestClient):
    login(client, "alice", wrangler=True)
    client.cookies.clear()
    login(client, "bob")
    play_round(client, {"alice": "cow"}, view_as="alice")

    response = client.get("/game/scoreboard")

    assert response.status_code == 200
    assert "Did not answer" in response.text
    assert "bob" in response.text
    assert "cow" in response.text


# ---------- Status polling and redirects ----------


def test_status_reports_the_clock(client: TestClient):
    login(client, "alice")
    start_clock(20)

    assert client.get("/game/status").json()["seconds_left"] > 0

    Game_State["round_ends_at"] = 0
    assert client.get("/game/status").json()["seconds_left"] == 0


def test_every_page_moves_to_the_scoreboard_once_the_clock_stops(
    logged_in_client: TestClient,
):
    play_round(logged_in_client, {"alice": "cow"}, view_as="alice")

    for page in ["/game", "/game/answered", "/"]:
        response = logged_in_client.get(page, follow_redirects=False)

        assert response.status_code == 303, page
        assert response.headers["location"] == "/game/scoreboard", page


def test_status_reports_round_over_after_the_deadline(client: TestClient):
    login(client, "alice")
    start_clock(-1)

    body = client.get("/game/status").json()

    assert body["revealed"] is True
    assert body["seconds_left"] == 0


def test_scoreboard_redirects_while_the_clock_runs(logged_in_client: TestClient):
    start_clock()

    # Unanswered players go back to the question.
    response = logged_in_client.get("/game/scoreboard", follow_redirects=False)
    assert response.headers["location"] == "/game"

    logged_in_client.post("/game/answer", data={"answer": "cow"})

    # Answered players go back to their waiting page.
    response = logged_in_client.get("/game/scoreboard", follow_redirects=False)
    assert response.headers["location"] == "/game/answered"


def test_pages_require_login_for_the_clock_endpoints(client: TestClient):
    for page in ["/game/scoreboard", "/game/status"]:
        response = client.get(page, follow_redirects=False)

        assert response.status_code == 303, page
        assert response.headers["location"] == "/", page


# ---------- The scoreboard ----------


def test_scoreboard_lists_every_player_and_answer(client: TestClient):
    login(client, "alice", wrangler=True)
    client.cookies.clear()
    login(client, "bob")
    play_round(client, {"alice": "cow", "bob": "cow"}, view_as="alice")

    response = client.get("/game/scoreboard")

    assert response.status_code == 200
    assert "alice" in response.text and "bob" in response.text
    assert "cow" in response.text


def test_scoreboard_groups_matching_answers_case_insensitively(client: TestClient):
    login(client, "alice")
    client.cookies.clear()
    login(client, "bob")
    play_round(client, {"alice": "Corn", "bob": "corn"}, view_as="alice")

    response = client.get("/game/scoreboard")

    # One group holding both players, shown with the first spelling given.
    assert "Corn" in response.text
    assert "alice" in response.text and "bob" in response.text


def test_scoreboard_marks_unique_answers_with_a_badge(client: TestClient):
    login(client, "alice")
    client.cookies.clear()
    login(client, "bob")
    client.cookies.clear()
    login(client, "carol")
    play_round(
        client,
        {"alice": "corn", "bob": "corn", "carol": "hay"},
        view_as="alice",
    )

    response = client.get("/game/scoreboard")

    # Only the lone "hay" answer is unique, so only carol gets the badge.
    assert response.text.count("badge-unique") == 1
    assert "Unique!" in response.text


def test_scoreboard_awards_medal_to_largest_herd(client: TestClient):
    login(client, "alice")
    client.cookies.clear()
    login(client, "bob")
    client.cookies.clear()
    login(client, "carol")
    play_round(
        client, {"alice": "corn", "bob": "corn", "carol": "hay"}, view_as="alice"
    )

    response = client.get("/game/scoreboard")

    assert response.text.count("medal") == 1
