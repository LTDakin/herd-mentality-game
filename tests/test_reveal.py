"""Tests for the reveal endpoint, the status endpoint, and the scoreboard."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


def answer(client: TestClient, name: str, value: str, wrangler: bool = False):
    login(client, name, wrangler=wrangler)
    client.post("/game/answer", data={"answer": value})


def relogin(client: TestClient, name: str):
    """Return to an existing player without hitting the name-taken guard."""
    client.cookies.set("player_name", name)


def test_status_reports_not_revealed(client: TestClient):
    login(client, "alice")

    response = client.get("/game/status")

    assert response.status_code == 200
    assert response.json()["revealed"] is False


def test_status_requires_login(client: TestClient):
    response = client.get("/game/status", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_wrangler_reveal_sets_state_and_redirects(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})

    response = client.post("/game/reveal", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/scoreboard"
    assert Game_State["revealed"] is True


def test_non_wrangler_cannot_reveal(client: TestClient):
    login(client, "bob")
    client.post("/game/answer", data={"answer": "cow"})

    response = client.post("/game/reveal", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"
    assert Game_State["revealed"] is False


def test_reveal_requires_login(client: TestClient):
    response = client.post("/game/reveal", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert Game_State["revealed"] is False


def test_answered_redirects_to_scoreboard_once_revealed(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})
    client.post("/game/reveal")

    response = client.get("/game/answered", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/scoreboard"


def test_answered_page_includes_status_polling_script(client: TestClient):
    login(client, "bob")
    client.post("/game/answer", data={"answer": "cow"})

    response = client.get("/game/answered")

    assert "/game/status" in response.text
    assert "/game/scoreboard" in response.text


def test_scoreboard_lists_every_player_and_answer(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})

    client.cookies.clear()
    login(client, "bob")
    client.post("/game/answer", data={"answer": "sheep"})

    client.cookies.clear()
    login(client, "carol", wrangler=True)  # does not take over the role
    client.post("/game/answer", data={"answer": "cow"})

    client.cookies.clear()
    relogin(client, "alice")
    client.post("/game/reveal")

    response = client.get("/game/scoreboard")

    assert response.status_code == 200
    assert "alice" in response.text and "cow" in response.text
    assert "bob" in response.text and "sheep" in response.text
    assert "carol" in response.text


def test_scoreboard_marks_players_who_did_not_answer(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})

    client.cookies.clear()
    login(client, "bob")  # never answers

    client.cookies.clear()
    relogin(client, "alice")
    client.post("/game/reveal")

    response = client.get("/game/scoreboard")

    assert "Did not answer" in response.text
    assert "bob" in response.text


def test_scoreboard_groups_matching_answers_case_insensitively(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "Corn"})

    client.cookies.clear()
    login(client, "bob")
    client.post("/game/answer", data={"answer": "corn"})

    client.cookies.clear()
    relogin(client, "alice")
    client.post("/game/reveal")

    response = client.get("/game/scoreboard")

    # One group heading, using the first spelling, with both players under it.
    assert response.text.count('<span class="group-answer">') == 1
    assert '<span class="group-answer">Corn</span>' in response.text
    assert "2 players" in response.text
    assert "badge-unique" not in response.text


def test_scoreboard_marks_unique_answers_with_a_badge(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "corn"})

    client.cookies.clear()
    login(client, "bob")
    client.post("/game/answer", data={"answer": "cows"})

    client.cookies.clear()
    relogin(client, "alice")
    client.post("/game/reveal")

    response = client.get("/game/scoreboard")

    # Both answers are unique, so both get the badge.
    assert response.text.count("badge-unique") == 2


def test_scoreboard_awards_medal_to_largest_herd(client: TestClient):
    for name, answer in [("alice", "corn"), ("bob", "corn"), ("carol", "hay")]:
        client.cookies.clear()
        if name == "alice":
            login(client, name, wrangler=True)
        else:
            login(client, name)
        client.post("/game/answer", data={"answer": answer})

    client.cookies.clear()
    relogin(client, "alice")
    client.post("/game/reveal")

    response = client.get("/game/scoreboard")

    assert response.text.count("medal") == 1
    assert '<span class="group-answer">corn</span>' in response.text



def test_scoreboard_redirects_before_reveal(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})

    response = client.get("/game/scoreboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"


def test_scoreboard_requires_login(client: TestClient):
    response = client.get("/game/scoreboard", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_second_reveal_is_harmless(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})
    client.post("/game/reveal")

    response = client.post("/game/reveal", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/scoreboard"
    assert Game_State["revealed"] is True
