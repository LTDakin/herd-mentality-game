"""Tests for starting the next round from the scoreboard."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


def play_round(client: TestClient):
    """Log in as the wrangler, answer, and reveal."""
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})
    client.post("/game/reveal")


def test_next_round_clears_answers_and_revealed(client: TestClient):
    play_round(client)

    response = client.post("/game/next-round", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"
    assert Game_State["answers"] == {}
    assert Game_State["revealed"] is False


def test_next_round_increments_round(client: TestClient):
    play_round(client)
    assert Game_State["round"] == 0

    client.post("/game/next-round")

    assert Game_State["round"] == 1


def test_next_round_keeps_players_and_wrangler(client: TestClient):
    play_round(client)

    client.post("/game/next-round")

    assert "alice" in Game_State["player_names"]
    assert Game_State["wrangler"] == "alice"


def test_non_wrangler_cannot_start_next_round(client: TestClient):
    play_round(client)
    login(client, "bob")
    client.post("/game/answer", data={"answer": "sheep"})

    response = client.post("/game/next-round", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/scoreboard"
    assert Game_State["answers"] == {"alice": "cow", "bob": "sheep"}
    assert Game_State["revealed"] is True
    assert Game_State["round"] == 0


def test_next_round_requires_login(client: TestClient):
    response = client.post("/game/next-round", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert Game_State["round"] == 0


def test_status_reports_round(client: TestClient):
    login(client, "alice", wrangler=True)

    assert client.get("/game/status").json() == {"revealed": False, "round": 0}

    play_round(client)
    client.post("/game/next-round")

    assert client.get("/game/status").json() == {"revealed": False, "round": 1}


def test_wrangler_sees_next_round_button(client: TestClient):
    play_round(client)

    response = client.get("/game/scoreboard")

    assert 'action="/game/next-round"' in response.text


def test_regular_player_does_not_see_next_round_button(client: TestClient):
    play_round(client)
    login(client, "bob")
    client.post("/game/answer", data={"answer": "sheep"})

    response = client.get("/game/scoreboard")

    assert response.status_code == 200
    assert "/game/next-round" not in response.text
    assert "Waiting for the next round" in response.text


def test_scoreboard_embeds_round_for_polling(client: TestClient):
    play_round(client)

    response = client.get("/game/scoreboard")

    assert "const currentRound = 0;" in response.text
    assert "/game/status" in response.text


def test_players_can_answer_again_after_reset(client: TestClient):
    play_round(client)
    client.post("/game/next-round")

    response = client.post(
        "/game/answer", data={"answer": "sheep"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"
    assert Game_State["answers"] == {"alice": "sheep"}


def test_scoreboard_unavailable_after_reset(client: TestClient):
    play_round(client)
    client.post("/game/next-round")

    response = client.get("/game/scoreboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"


def test_second_round_can_be_revealed_again(client: TestClient):
    play_round(client)
    client.post("/game/next-round")
    client.post("/game/answer", data={"answer": "sheep"})

    response = client.post("/game/reveal", follow_redirects=False)

    assert response.headers["location"] == "/game/scoreboard"
    assert "sheep" in client.get("/game/scoreboard").text
