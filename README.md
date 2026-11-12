# Chainpiece — Collectibles Registry (Milestone 1)

A web application where collectors create accounts, register collectible objects with
photographs, receive permanent registration IDs, and record a tamper-evident history
of ownership and custody events.

**Core principle:** everything recorded is a *claim* until verified evidence supports it.
Registration is never treated as proof of authenticity.

## What Milestone 1 includes

- Collector accounts (email + password, passwords stored hashed)
- Register objects: category, title, description, free-form details (date, mint mark,
  weight, distinguishing features), multiple photo uploads
- Permanent registration IDs in the format `CRN-XXXXX-XXXXX` (unambiguous characters only)
- Provenance events: registration, ownership claims, custody transfer claims,
  condition notes, general notes — each with optional evidence file
- **Tamper-evident ledger:** every event's hash includes the previous event's hash
  (a hash chain). Any edit or deletion of a historical record breaks the chain, and the
  object's public page shows a red warning with the exact event where the break occurs.
- Clear separation of `claim` vs `verified` status. Only accounts explicitly granted
  verifier status can mark an event verified, and every verification decision is itself
  recorded in the ledger.
- Public profile page for every object at `/objects/<registration-id>`

## Running it

```bash
pip install -r requirements.txt
python3 app.py
```

Then open http://127.0.0.1:5000 in a browser.

Set a real secret key before any real use:

```bash
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" python3 app.py
```

To designate a verifier account (founder decision, done from the command line):

```bash
flask --app app make-verifier
```

## Tests

```bash
python3 -m pytest tests/ -v
```

12 tests cover signup/login, unique registration IDs, public profiles, event recording,
permission checks (non-owners cannot modify records, non-verifiers cannot verify),
photo upload validation, and — most importantly — that tampering with or deleting any
ledger event is detected.

## Known gaps before accepting real custody records

This is a foundation, not a production system. Before real valuable objects are
registered, it needs (in order):

1. HTTPS and a real deployment (not a laptop)
2. CSRF protection on all forms
3. Rate limiting and brute-force protection on login
4. Migration from SQLite to PostgreSQL (e.g. Supabase) with backups
5. Photo integrity: store each photo's hash in the ledger so photos themselves are
   tamper-evident
6. A qualified developer security review
