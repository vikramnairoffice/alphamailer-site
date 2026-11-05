"""Dependency upgrades must preserve existing bcrypt login hashes."""

import bcrypt
import pytest

from app.auth import hash_password, verify_password


@pytest.mark.parametrize("password", ["test-only-password", "unicode-\u00e9-password", "x" * 90, "\u00e9" * 50])
def test_existing_bcrypt_hashes_and_new_hashes_remain_compatible(password):
    # Passlib's bcrypt scheme historically truncated UTF-8 input to 72 bytes.
    legacy = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=4)).decode("ascii")
    assert verify_password(password, legacy)
    assert not verify_password("wrong-password", legacy)

    created = hash_password(password)
    assert created.startswith("$2b$")
    assert verify_password(password, created)
    assert not verify_password("wrong-password", created)


def test_legacy_login_and_admin_templates(client, database):
    from app.models import User

    legacy = bcrypt.hashpw(b"test-only-password", bcrypt.gensalt(rounds=4)).decode("ascii")
    with database() as session:
        session.add(User(email="operator@example.test", hashed_password=legacy, is_admin=True))
        session.commit()

    assert client.get("/admin/login").status_code == 200
    rejected = client.post("/admin/login", data={
        "email": "operator@example.test", "password": "wrong-password",
    })
    assert rejected.status_code == 401
    assert "Invalid credentials" in rejected.text

    accepted = client.post("/admin/login", data={
        "email": "operator@example.test", "password": "test-only-password",
    }, follow_redirects=False)
    assert accepted.status_code == 302
    assert accepted.headers["location"] == "/admin/"
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/users").status_code == 200
