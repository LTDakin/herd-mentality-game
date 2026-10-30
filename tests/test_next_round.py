"""Tests for starting the next round from the scoreboard."""

from fastapi.testclient import TestClient

from herd_mentality.rounds import seconds_left
from herd_mentality.state import Game_State
from round_clock import start_clock


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


def play_round(client: TestClient):
    """Log in as the wrangler, answer, and let the clock run out."""
    login(client, "alice", wrangler=True)
    start_clock()
    client.post("/game/answer", data={"answer": "cow"})
    Game_State["round_ends_at"] = 0


def test_next_round_clears_answers_and_restarts_the_clock(client: TestClient):
    play_round(client)

    response = client.post("/game/next-round", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"
    assert Game_State["answers"] == {}
    assert seconds_left(Game_State["round_ends_at"]) > 0


def test_next_round_increments_round_and_keeps_players(client: TestClient):
    play_round(client)
    assert Game_State["round"] == 0

    client.post("/game/next-round")

    assert Game_State["round"] == 1
    assert Game_State["wrangler"] == "alice"
    assert "alice" in Game_State["player_names"]


def test_non_wrangler_cannot_start_next_round(client: TestClient):
    play_round(client)
    login(client, "bob")

    response = client.post("/game/next-round", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/scoreboard"
    assert Game_State["answers"] == {"alice": "cow"}
    assert Game_State["round"] == 0


def test_next_round_requires_login(client: TestClient):
    response = client.post("/game/next-round", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert Game_State["round"] == 0


def test_status_reports_the_new_round(client: TestClient):
    play_round(client)
    client.post("/game/next-round")

    body = client.get("/game/status").json()

    assert body["round"] == 1
    assert body["revealed"] is False


def test_only_the_wrangler_sees_the_next_round_button(client: TestClient):
    play_round(client)

    assert 'action="/game/next-round"' in client.get("/game/scoreboard").text

    login(client, "bob")

    response = client.get("/game/scoreboard")
    assert "/game/next-round" not in response.text
    assert "Waiting for the next round" in response.text


def test_players_can_answer_again_after_reset(client: TestClient):
    play_round(client)
    client.post("/game/next-round")

    response = client.post(
        "/game/answer", data={"answer": "sheep"}, follow_redirects=False
    )

    assert response.headers["location"] == "/game/answered"
    assert Game_State["answers"] == {"alice": "sheep"}


def test_scoreboard_unavailable_after_reset(client: TestClient):
    play_round(client)
    client.post("/game/next-round")

    response = client.get("/game/scoreboard", follow_redirects=False)

    # A fresh round has no answers, so nobody belongs on the scoreboard yet.
    assert response.headers["location"] == "/game"


def test_second_round_ends_on_its_own_clock(client: TestClient):
    play_round(client)
    client.post("/game/next-round")
    client.post("/game/answer", data={"answer": "sheep"})
    Game_State["round_ends_at"] = 0

    response = client.get("/game/scoreboard", follow_redirects=False)

    assert response.status_code == 200
    assert "sheep" in response.text
