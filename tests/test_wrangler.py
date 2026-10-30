"""Tests for the wrangler: claiming the role and the login checkbox."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


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


def test_checkbox_is_shown_only_while_the_role_is_unclaimed(client: TestClient):
    assert 'name="wrangler"' in client.get("/").text

    login(client, "alice", wrangler=True)

    assert 'name="wrangler"' not in client.get("/").text


def test_checkbox_stays_hidden_on_login_error(client: TestClient):
    login(client, "alice", wrangler=True)

    response = client.post(
        "/login", data={"player_name": "alice"}, follow_redirects=False
    )

    assert response.status_code == 409
    assert 'name="wrangler"' not in response.text
