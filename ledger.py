import hashlib
import json

GENESIS_HASH = "0" * 64


def canonical_payload(event_type, details, actor_id, evidence_filename, created_at):
    payload = {
        "event_type": event_type,
        "details": details,
        "actor_id": actor_id,
        "evidence_filename": evidence_filename,
        "created_at": created_at,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_hash(prev_hash, payload):
    record = f"{prev_hash}|{payload}"
    return hashlib.sha256(record.encode("utf-8")).hexdigest()


def append_event(db, object_id, actor_id, event_type, details,
                 evidence_filename=None, status="claim", created_at=None):
    row = db.execute(
        "SELECT hash FROM events WHERE object_id = ? ORDER BY id DESC LIMIT 1",
        (object_id,),
    ).fetchone()
    prev_hash = row["hash"] if row else GENESIS_HASH
    if created_at is None:
        created_at = db.execute(
            "SELECT strftime('%Y-%m-%dT%H:%M:%fZ','now') AS now"
        ).fetchone()["now"]
    payload = canonical_payload(
        event_type, details, actor_id, evidence_filename, created_at
    )
    event_hash = compute_hash(prev_hash, payload)
    cursor = db.execute(
        "INSERT INTO events (object_id, actor_id, event_type, details_json,"
        " evidence_filename, status, prev_hash, hash, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (object_id, actor_id, event_type, json.dumps(details, sort_keys=True),
         evidence_filename, status, prev_hash, event_hash, created_at),
    )
    return cursor.lastrowid, event_hash


def verify_chain(db, object_id):
    rows = db.execute(
        "SELECT * FROM events WHERE object_id = ? ORDER BY id", (object_id,)
    ).fetchall()
    prev_hash = GENESIS_HASH
    for row in rows:
        payload = canonical_payload(
            row["event_type"],
            json.loads(row["details_json"]),
            row["actor_id"],
            row["evidence_filename"],
            row["created_at"],
        )
        expected = compute_hash(prev_hash, payload)
        if row["prev_hash"] != prev_hash or row["hash"] != expected:
            return False, row["id"]
        prev_hash = row["hash"]
    return True, None
