import json
import sqlite3

import pytest

import ledger
from app import create_app


@pytest.fixture()
def db(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "ledger.sqlite3"),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
        }
    )
    with app.app_context():
        from db import get_db

        yield get_db()


def test_chain_verifies_after_multiple_events(db):
    db.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
        ("u@example.com", "x", "U"),
    )
    user_id = db.execute("SELECT id FROM users").fetchone()["id"]
    db.execute(
        "INSERT INTO objects (registration_id, owner_id, category, title)"
        " VALUES (?, ?, ?, ?)",
        ("CRN-AAAAA-BBBBB", user_id, "coin", "Test coin"),
    )
    object_id = db.execute("SELECT id FROM objects").fetchone()["id"]
    for i in range(5):
        ledger.append_event(db, object_id, user_id, "note", {"text": f"event {i}"})
    db.commit()
    ok, broken_at = ledger.verify_chain(db, object_id)
    assert ok is True
    assert broken_at is None


def test_tampering_with_details_breaks_chain(db):
    db.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
        ("u@example.com", "x", "U"),
    )
    user_id = db.execute("SELECT id FROM users").fetchone()["id"]
    db.execute(
        "INSERT INTO objects (registration_id, owner_id, category, title)"
        " VALUES (?, ?, ?, ?)",
        ("CRN-AAAAA-BBBBB", user_id, "coin", "Test coin"),
    )
    object_id = db.execute("SELECT id FROM objects").fetchone()["id"]
    ledger.append_event(db, object_id, user_id, "note", {"text": "original"})
    ledger.append_event(db, object_id, user_id, "note", {"text": "second"})
    db.commit()
    db.execute(
        "UPDATE events SET details_json = ? WHERE id = (SELECT MIN(id) FROM events)",
        (json.dumps({"text": "FORGED"}),),
    )
    ok, broken_at = ledger.verify_chain(db, object_id)
    assert ok is False
    assert broken_at == 1


def test_deleting_an_event_breaks_chain(db):
    db.execute(
        "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
        ("u@example.com", "x", "U"),
    )
    user_id = db.execute("SELECT id FROM users").fetchone()["id"]
    db.execute(
        "INSERT INTO objects (registration_id, owner_id, category, title)"
        " VALUES (?, ?, ?, ?)",
        ("CRN-AAAAA-BBBBB", user_id, "coin", "Test coin"),
    )
    object_id = db.execute("SELECT id FROM objects").fetchone()["id"]
    ledger.append_event(db, object_id, user_id, "note", {"text": "one"})
    ledger.append_event(db, object_id, user_id, "note", {"text": "two"})
    ledger.append_event(db, object_id, user_id, "note", {"text": "three"})
    db.commit()
    db.execute("DELETE FROM events WHERE id = (SELECT MIN(id) FROM events)")
    ok, broken_at = ledger.verify_chain(db, object_id)
    assert ok is False
    assert broken_at == 2
