import json

import pytest

import ledger
from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "UPLOAD_DIR": str(tmp_path / "uploads"),
        }
    )
    with app.test_client() as client:
        yield client


def signup(client, email="alice@example.com", name="Alice"):
    return client.post(
        "/signup",
        data={"email": email, "display_name": name, "password": "longpassword1"},
        follow_redirects=True,
    )


def register_object(client, title="1893-S Morgan Silver Dollar"):
    return client.post(
        "/objects/new",
        data={
            "category": "coin",
            "title": title,
            "description": "Key-date Morgan dollar",
            "attr_date": "1893",
            "attr_mint_mark": "S",
            "attr_weight": "26.73 g",
        },
        follow_redirects=True,
    )


def test_signup_and_login(client):
    response = signup(client)
    assert b"My collection" in response.data
    client.get("/logout")
    response = client.post(
        "/login",
        data={"email": "alice@example.com", "password": "longpassword1"},
        follow_redirects=True,
    )
    assert b"My collection" in response.data
    bad = client.post(
        "/login",
        data={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert b"Incorrect email or password" in bad.data


def test_signup_requires_long_password(client):
    response = client.post(
        "/signup",
        data={"email": "bob@example.com", "display_name": "Bob", "password": "short"},
    )
    assert b"at least 10 characters" in response.data


def test_registration_assigns_unique_permanent_id(client):
    signup(client)
    response = register_object(client)
    assert b"CRN-" in response.data
    response2 = register_object(client, title="Second object")
    assert b"CRN-" in response2.data
    import re

    ids = re.findall(rb"CRN-[A-Z2-9]{5}-[A-Z2-9]{5}", response.data + response2.data)
    assert len(set(ids)) >= 2


def test_object_public_profile_shows_details(client):
    signup(client)
    register_object(client)
    page = client.get("/dashboard")
    import re

    reg_id = re.search(rb"CRN-[A-Z2-9]{5}-[A-Z2-9]{5}", page.data).group(0).decode()
    profile = client.get(f"/objects/{reg_id}")
    assert b"1893-S Morgan Silver Dollar" in profile.data
    assert b"1893" in profile.data
    assert b"Custody chain intact" in profile.data
    assert b"registration" in profile.data
    assert b"claim" in profile.data


def test_owner_can_add_event_and_chain_stays_valid(client):
    signup(client)
    register_object(client)
    page = client.get("/dashboard")
    import re

    reg_id = re.search(rb"CRN-[A-Z2-9]{5}-[A-Z2-9]{5}", page.data).group(0).decode()
    response = client.post(
        f"/objects/{reg_id}/events",
        data={"event_type": "ownership_claim", "details": "Purchased from estate sale"},
        follow_redirects=True,
    )
    assert b"Purchased from estate sale" in response.data
    assert b"Custody chain intact" in response.data


def test_non_owner_cannot_add_event(client):
    signup(client, "owner@example.com", "Owner")
    register_object(client)
    page = client.get("/dashboard")
    import re

    reg_id = re.search(rb"CRN-[A-Z2-9]{5}-[A-Z2-9]{5}", page.data).group(0).decode()
    client.get("/logout")
    signup(client, "other@example.com", "Other")
    response = client.post(
        f"/objects/{reg_id}/events",
        data={"event_type": "note", "details": "sabotage"},
    )
    assert response.status_code == 403


def test_only_verifier_can_verify_event(client):
    signup(client, "owner@example.com", "Owner")
    register_object(client)
    page = client.get("/dashboard")
    import re

    reg_id = re.search(rb"CRN-[A-Z2-9]{5}-[A-Z2-9]{5}", page.data).group(0).decode()
    client.post(
        f"/objects/{reg_id}/events",
        data={"event_type": "ownership_claim", "details": "claim text"},
    )
    profile = client.get(f"/objects/{reg_id}")
    event_id = int(re.search(rb"/events/(\d+)/verify", profile.data).group(1))
    response = client.post(f"/objects/{reg_id}/events/{event_id}/verify")
    assert response.status_code == 403


def test_photo_upload(client, tmp_path):
    signup(client)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    response = client.post(
        "/objects/new",
        data={
            "category": "coin",
            "title": "Photo coin",
            "photos": [io_stream(png, "obverse.png")],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"img" in response.data
    import re

    matches = re.findall(rb'/uploads/([a-f0-9]+\.png)', response.data)
    assert matches
    served = client.get(f"/uploads/{matches[0].decode()}")
    assert served.status_code == 200


def io_stream(data, filename):
    from io import BytesIO

    return (BytesIO(data), filename)


def test_disallowed_file_extension_rejected(client):
    signup(client)
    response = client.post(
        "/objects/new",
        data={
            "category": "coin",
            "title": "Evil",
            "photos": [io_stream(b"malware", "evil.exe")],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"/uploads/" not in response.data
