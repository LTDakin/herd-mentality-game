"""Tests for login, session cookies, and the login redirect on protected pages."""

from fastapi.testclient import TestClient

from herd_mentality.auth import player_name_cookie_key
from round_clock import start_clock

LOGIN_REQUIRED = ["/game", "/game/answered", "/game/scoreboard", "/game/status"]


def test_root_shows_login_when_logged_out(client: TestClient):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 200
    assert "Enter a name" in response.text


def test_login_sets_cookie_and_redirects_to_game(client: TestClient):
    response = client.post(
        "/login", data={"player_name": "alice"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/game"
    assert response.cookies[player_name_cookie_key] == "alice"


def test_login_strips_whitespace_around_name(client: TestClient):
    response = client.post(
        "/login", data={"player_name": "  alice  "}, follow_redirects=False
    )

    assert response.cookies[player_name_cookie_key] == "alice"


def test_login_rejects_blank_name(client: TestClient):
    response = client.post(
        "/login", data={"player_name": "   "}, follow_redirects=False
    )

    assert response.status_code == 422
    assert "Enter a name" in response.text
    assert player_name_cookie_key not in response.cookies


def test_login_rejects_duplicate_name(client: TestClient):
    client.post("/login", data={"player_name": "alice"})

    response = client.post(
        "/login", data={"player_name": "alice"}, follow_redirects=False
    )

    assert response.status_code == 409
    assert "already taken" in response.text


def test_root_redirects_to_game_when_logged_in(logged_in_client: TestClient):
    response = logged_in_client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"


def test_answered_player_is_sent_to_their_waiting_page(logged_in_client: TestClient):
    start_clock()
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    for page in ["/", "/game"]:
        response = logged_in_client.get(page, follow_redirects=False)

        assert response.status_code == 303, page
        assert response.headers["location"] == "/game/answered", page


def test_game_shows_player_name_when_logged_in(logged_in_client: TestClient):
    response = logged_in_client.get("/game", follow_redirects=False)

    assert response.status_code == 200
    assert "Playing as alice" in response.text


def test_protected_pages_redirect_when_logged_out(client: TestClient):
    for page in LOGIN_REQUIRED:
        response = client.get(page, follow_redirects=False)

        assert response.status_code == 303, page
        assert response.headers["location"] == "/", page


def test_game_redirects_for_unknown_or_empty_cookie(client: TestClient):
    for cookie in ["ghost", ""]:
        client.cookies.set(player_name_cookie_key, cookie)

        response = client.get("/game", follow_redirects=False)

        assert response.status_code == 303, cookie
        assert response.headers["location"] == "/", cookie


def test_answering_redirects_when_logged_out(client: TestClient):
    response = client.post(
        "/game/answer", data={"answer": "cow"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
