"""Tests for answering and the answered page."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State


def test_answer_redirects_to_answered(logged_in_client: TestClient):
    response = logged_in_client.post(
        "/game/answer", data={"answer": "cow"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"


def test_answered_page_shows_answer(logged_in_client: TestClient):
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered", follow_redirects=False)

    assert response.status_code == 200
    assert "cow" in response.text


def test_answered_page_redirects_before_answering(logged_in_client: TestClient):
    response = logged_in_client.get("/game/answered", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"


def test_blank_answer_redirects_back_to_game(logged_in_client: TestClient):
    response = logged_in_client.post(
        "/game/answer", data={"answer": "  "}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/game"


def test_second_answer_is_not_recorded(logged_in_client: TestClient):
    logged_in_client.post("/game/answer", data={"answer": "cow"})
    logged_in_client.post("/game/answer", data={"answer": "sheep"})

    response = logged_in_client.get("/game/answered", follow_redirects=False)

    assert "cow" in response.text
    assert "sheep" not in response.text


def test_answered_redirects_after_reconnect(client: TestClient):
    """A player who drops off after answering lands back on the waiting page."""
    client.post("/login", data={"player_name": "alice"})
    client.post("/game/answer", data={"answer": "cow"})

    # Reconnecting with the same cookie should skip straight past the question.
    for page in ["/", "/game"]:
        response = client.get(page, follow_redirects=False)

        assert response.status_code == 303, page
        assert response.headers["location"] == "/game/answered", page
    assert "cow" in client.get("/game/answered").text


def test_reconnect_after_next_round_shows_the_question_again(client: TestClient):
    client.post("/login", data={"player_name": "alice"})
    client.post("/game/answer", data={"answer": "cow"})
    Game_State["answers"].clear()

    response = client.get("/game", follow_redirects=False)

    assert response.status_code == 200
    assert "Playing as alice" in response.text


def test_answers_are_separate_per_player(client: TestClient):
    client.post("/login", data={"player_name": "alice"})
    client.post("/game/answer", data={"answer": "cow"})

    client.cookies.clear()
    client.post("/login", data={"player_name": "bob"})
    response = client.get("/game/answered", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"
