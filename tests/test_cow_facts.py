"""Tests for the cow facts shown while waiting for the clock to run out."""

from fastapi.testclient import TestClient

from herd_mentality.main import COW_FACTS
from round_clock import start_clock


def test_every_entry_has_a_valid_type_and_text():
    for entry in COW_FACTS:
        assert set(entry) == {"type", "text"}
        assert entry["type"] in {"fact", "joke"}
        assert entry["text"].strip()


def test_answered_page_shows_a_cow_fact_or_joke(logged_in_client: TestClient):
    start_clock()
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered")

    assert "Cow fact" in response.text or "Cow joke" in response.text


def test_answered_page_escapes_fact_text(logged_in_client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "herd_mentality.main.COW_FACTS",
        [{"type": "fact", "text": "<script>alert(1)</script>"}],
    )
    start_clock()
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered")

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text
