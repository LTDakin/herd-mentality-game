"""Tests for answering and the answered page."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State
from round_clock import start_clock


def test_answer_redirects_to_answered(logged_in_client: TestClient):
    start_clock()

    response = logged_in_client.post(
        "/game/answer", data={"answer": "cow"}, follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/game/answered"


def test_answered_page_shows_answer(logged_in_client: TestClient):
    start_clock()
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered", follow_redirects=False)

    assert response.status_code == 200
    assert "cow" in response.text


def test_answered_page_redirects_before_answering(logged_in_client: TestClient):
    start_clock()

    response = logged_in_client.get("/game/answered", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/game"


def test_blank_answer_redirects_back_to_game(logged_in_client: TestClient):
    start_clock()

    response = logged_in_client.post(
        "/game/answer", data={"answer": "  "}, follow_redirects=False
    )

    assert response.headers["location"] == "/game"


def test_second_answer_is_not_recorded(logged_in_client: TestClient):
    start_clock()
    logged_in_client.post("/game/answer", data={"answer": "cow"})
    logged_in_client.post("/game/answer", data={"answer": "sheep"})

    response = logged_in_client.get("/game/answered", follow_redirects=False)

    assert "cow" in response.text
    assert "sheep" not in response.text


def test_reconnect_after_next_round_shows_the_question_again(client: TestClient):
    client.post("/login", data={"player_name": "alice"})
    start_clock()
    client.post("/game/answer", data={"answer": "cow"})
    Game_State["answers"].clear()
    start_clock()

    response = client.get("/game", follow_redirects=False)

    assert response.status_code == 200
    assert "Playing as alice" in response.text
