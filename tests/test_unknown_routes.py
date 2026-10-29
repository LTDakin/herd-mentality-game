"""Unknown URLs should recover to the page that matches the current game state."""

from fastapi.testclient import TestClient

from herd_mentality.auth import player_name_cookie_key
from herd_mentality.state import Game_State


def test_unknown_url_sends_logged_out_player_to_login(client: TestClient):
    response = client.get("/no-such-page", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_unknown_url_sends_player_to_game_before_answering(
    logged_in_client: TestClient,
):
    response = logged_in_client.get("/no-such-page", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"


def test_unknown_url_sends_answered_player_to_answered(logged_in_client: TestClient):
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/no-such-page", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"


def test_unknown_url_sends_everyone_to_scoreboard_once_revealed(
    logged_in_client: TestClient,
):
    logged_in_client.post("/game/answer", data={"answer": "cow"})
    Game_State["revealed"] = True

    for page in ["/no-such-page", "/game/typo"]:
        response = logged_in_client.get(page, follow_redirects=False)

        assert response.status_code == 303, page
        assert response.headers["location"] == "/game/scoreboard", page


def test_wrong_method_on_a_form_endpoint_recovers(client: TestClient):
    # Browsers re-request form targets with GET when a page is resubmitted.
    response = client.get("/game/reveal", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_unknown_static_file_is_still_a_404(client: TestClient):
    # Missing assets must fail loudly for the browser, not redirect into HTML.
    response = client.get("/static/no-such-file.css", follow_redirects=False)

    assert response.status_code == 404


def test_unknown_url_ignores_stale_cookie(client: TestClient):
    client.cookies.set(player_name_cookie_key, "ghost")

    response = client.get("/no-such-page", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"
