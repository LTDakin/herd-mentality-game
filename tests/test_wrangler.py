"""Tests for the wrangler: claiming the role, the login checkbox, and the reveal button."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


def test_wrangler_is_none_at_start(client: TestClient):
    assert Game_State["wrangler"] is None


def test_login_with_checkbox_claims_wrangler(client: TestClient):
    login(client, "alice", wrangler=True)

    assert Game_State["wrangler"] == "alice"


def test_login_without_checkbox_does_not_claim_wrangler(client: TestClient):
    login(client, "alice")

    assert Game_State["wrangler"] is None


def test_first_wrangler_wins(client: TestClient):
    login(client, "alice", wrangler=True)
    login(client, "bob", wrangler=True)

    assert Game_State["wrangler"] == "alice"


def test_checkbox_is_shown_when_role_unclaimed(client: TestClient):
    response = client.get("/")

    assert 'name="wrangler"' in response.text


def test_checkbox_is_hidden_once_wrangler_exists(client: TestClient):
    login(client, "alice", wrangler=True)

    response = client.get("/")

    assert response.status_code == 200
    assert 'name="wrangler"' not in response.text


def test_checkbox_stays_hidden_on_login_error(client: TestClient):
    login(client, "alice", wrangler=True)

    response = client.post(
        "/login", data={"player_name": "alice"}, follow_redirects=False
    )

    assert response.status_code == 409
    assert 'name="wrangler"' not in response.text


def test_wrangler_sees_reveal_button(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})

    response = client.get("/game/answered")

    assert 'action="/game/reveal"' in response.text
    assert "Reveal" in response.text


def test_regular_player_sees_waiting_message(client: TestClient):
    login(client, "bob")
    client.post("/game/answer", data={"answer": "cow"})

    response = client.get("/game/answered")

    assert "Waiting for reveal" in response.text


def test_wrangler_does_not_see_waiting_message(client: TestClient):
    login(client, "alice", wrangler=True)
    client.post("/game/answer", data={"answer": "cow"})

    response = client.get("/game/answered")

    assert "Waiting for reveal" not in response.text


def test_wrangler_cannot_claim_role_from_another_player(client: TestClient):
    login(client, "alice", wrangler=True)
    login(client, "carol", wrangler=True)

    assert Game_State["wrangler"] == "alice"

    client.cookies.clear()
    login(client, "carol")
    client.post("/game/answer", data={"answer": "cow"})
    response = client.get("/game/answered")

    assert "/game/reveal" not in response.text
