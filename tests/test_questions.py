"""Tests for the shared prompt shown each round."""

import json
from html import escape
from pathlib import Path

from fastapi.testclient import TestClient

import herd_mentality.main as main
from herd_mentality.questions import pick_question
from herd_mentality.auth import player_name_cookie_key
from herd_mentality.state import Game_State
from round_clock import start_clock

QUESTIONS_FILE = (
    Path(__file__).parent.parent
    / "herd_mentality"
    / "static"
    / "herd_questions.json"
)
QUESTIONS = main.load_questions()


def rendered(text: str) -> str:
    """Escape a prompt the way Jinja2 does, so page text can be compared."""
    return escape(text, quote=True).replace("&#x27;", "&#39;")


def register(client: TestClient, name: str, wrangler: bool = False):
    """Create the player's session without following the login redirect."""
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    client.post("/login", data=data)
    client.cookies.set(player_name_cookie_key, name)


def login(client: TestClient, name: str, wrangler: bool = False):
    data = {"player_name": name}
    if wrangler:
        data["wrangler"] = "on"
    return client.post("/login", data=data, follow_redirects=False)


def use_pool(monkeypatch, questions: list[str]):
    """Serve a fixed prompt pool, as if the JSON file held only these."""
    monkeypatch.setattr(main, "load_questions", lambda: questions)


def test_questions_file_loads_non_empty_unique_strings():
    data = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    questions = data["questions"]

    assert questions
    for question in questions:
        assert isinstance(question, str)
        assert question.strip() == question
    assert len(questions) == len(set(questions))


def test_game_page_shows_the_round_question(logged_in_client: TestClient):
    Game_State["question"] = "Name a pizza topping."

    response = logged_in_client.get("/game", follow_redirects=False)

    assert response.status_code == 200
    assert "Name a pizza topping." in response.text
    assert "Your answer" not in response.text


def test_game_page_escapes_question_text(client: TestClient, monkeypatch):
    use_pool(monkeypatch, ["<script>alert(1)</script>"])
    login(client, "alice")

    response = client.get("/game", follow_redirects=False)

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_first_login_picks_a_question(client: TestClient):
    login(client, "alice")

    assert Game_State["question"] in QUESTIONS


def test_question_is_the_same_for_every_player(client: TestClient):
    register(client, "alice")
    question = Game_State["question"]
    alice_page = client.get("/game").text

    client.cookies.set(player_name_cookie_key, "bob")
    bob_page = client.get("/game").text

    assert rendered(question) in alice_page
    assert rendered(question) in bob_page


def test_reloading_the_game_page_keeps_the_question(logged_in_client: TestClient):
    Game_State["question"] = "Name a colour."

    logged_in_client.get("/game")
    logged_in_client.get("/game")

    assert Game_State["question"] == "Name a colour."


def test_next_round_picks_a_new_question(client: TestClient, monkeypatch):
    login(client, "alice", wrangler=True)
    start_clock()
    client.post("/game/answer", data={"answer": "cow"})
    Game_State["round_ends_at"] = 0
    use_pool(monkeypatch, ["Brand new prompt?"])
    # Forget anything left over from the round just played.
    Game_State["questions_left"] = []

    client.post("/game/next-round")

    assert Game_State["question"] == "Brand new prompt?"


def test_scoreboard_shows_the_question(client: TestClient):
    login(client, "alice", wrangler=True)
    start_clock()
    client.post("/game/answer", data={"answer": "cow"})
    Game_State["question"] = "Name a pizza topping."
    Game_State["round_ends_at"] = 0

    response = client.get("/game/scoreboard")

    assert "Name a pizza topping." in response.text


def test_pick_question_uses_every_prompt_before_repeating():
    pool = ["one", "two", "three"]
    remaining: list[str] = []
    seen = []
    previous = None

    for _ in range(12):
        question, remaining = pick_question(remaining, pool, previous)
        seen.append(question)
        previous = question

    # Twelve picks over a three-prompt pool cover all of them, and the same
    # prompt never lands twice in a row, including across a reshuffle.
    assert set(seen) == set(pool)
    assert all(earlier != later for earlier, later in zip(seen, seen[1:]))


def test_pick_question_handles_a_single_prompt():
    question, remaining = pick_question([], ["only one"], "only one")

    assert question == "only one"
    assert remaining == []


def test_pick_question_does_not_mutate_the_pool():
    pool = ["one", "two", "three"]
    pick_question([], pool, None)

    assert pool == ["one", "two", "three"]
