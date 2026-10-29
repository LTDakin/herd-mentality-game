"""Tests for the cow facts shown while waiting for a reveal."""

import json
from html import escape
from pathlib import Path

from fastapi.testclient import TestClient

from herd_mentality.main import COW_FACTS

FACTS_FILE = (
    Path(__file__).parent.parent / "herd_mentality" / "static" / "cow_facts.json"
)


def test_facts_file_has_forty_entries():
    assert len(COW_FACTS) == 40


def test_every_entry_has_a_valid_type_and_text():
    for entry in COW_FACTS:
        assert set(entry) == {"type", "text"}
        assert entry["type"] in {"fact", "joke"}
        assert entry["text"].strip()


def test_entries_are_unique():
    texts = [entry["text"] for entry in COW_FACTS]

    assert len(texts) == len(set(texts))


def test_facts_file_is_valid_json_on_disk():
    data = json.loads(FACTS_FILE.read_text(encoding="utf-8"))

    assert len(data["facts"]) == 40


def test_answered_page_shows_a_cow_fact(logged_in_client: TestClient):
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered")

    assert 'class="cow-fact"' in response.text
    assert any(escape(entry["text"]) in response.text for entry in COW_FACTS)


def test_answered_page_labels_facts_and_jokes(logged_in_client: TestClient):
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered")

    assert "Cow fact" in response.text or "Cow joke" in response.text


def test_answered_page_escapes_fact_text(logged_in_client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "herd_mentality.main.COW_FACTS",
        [{"type": "fact", "text": "<script>alert(1)</script>"}],
    )
    logged_in_client.post("/game/answer", data={"answer": "cow"})

    response = logged_in_client.get("/game/answered")

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text
