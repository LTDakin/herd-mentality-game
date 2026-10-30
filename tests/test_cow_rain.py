"""Tests for the decorative falling cow emoji."""

from fastapi.testclient import TestClient

from herd_mentality.state import Game_State
from round_clock import start_clock

PAGES = ["login", "game", "answered", "scoreboard"]


def _render(client: TestClient, page: str) -> str:
    if page == "login":
        return client.get("/").text
    client.post("/login", data={"player_name": "alice", "wrangler": "on"})
    start_clock()
    if page == "game":
        return client.get("/game").text
    client.post("/game/answer", data={"answer": "cow"})
    if page == "answered":
        return client.get("/game/answered").text
    Game_State["round_ends_at"] = 0
    return client.get("/game/scoreboard").text


def test_every_page_has_the_cow_rain(client: TestClient):
    for page in PAGES:
        body = _render(client, page)
        assert 'class="cow-rain"' in body, page
        assert body.count("cow-rain-item") >= 8, page


def test_cow_rain_is_hidden_from_screen_readers(client: TestClient):
    body = _render(client, "login")

    start = body.index('class="cow-rain"')

    assert 'aria-hidden="true"' in body[start - 40 : start + 40]


def test_cow_rain_emojis_are_used(client: TestClient):
    body = _render(client, "login")

    assert "🐄" in body
    assert "🐮" in body
