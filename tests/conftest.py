import pytest
from fastapi.testclient import TestClient

from herd_mentality.main import app
from herd_mentality.state import Game_State


@pytest.fixture(autouse=True)
def reset_game_state():
    """Give every test a clean game, so logins and answers never leak between tests."""
    Game_State["player_names"].clear()
    Game_State["answers"].clear()
    Game_State["wrangler"] = None
    Game_State["round"] = 0
    Game_State["question"] = None
    Game_State["questions_left"] = []
    Game_State["round_ends_at"] = None
    yield


@pytest.fixture
def client() -> TestClient:
    """A test client that does not follow redirects, so redirects are assertable."""
    return TestClient(app)


@pytest.fixture
def logged_in_client(client: TestClient) -> TestClient:
    """A client already logged in as 'alice'."""
    client.post("/login", data={"player_name": "alice"})
    return client
