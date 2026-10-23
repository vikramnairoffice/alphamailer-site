"""Offline coordinator evidence for independent browser accounts and tabs."""
from concurrent.futures import ThreadPoolExecutor
import re

import pytest
from sqlalchemy import select

from app import fleet_service as service
from app.auth import create_session_token
from app.fleet_models import Job, Worker
from app.fleet_schemas import Claim
from app.models import User


SESSION = "ten-tab-fixture-session"
ACCOUNTS = [f"browser{i}@example.test" for i in range(10)]


def pair(client, operator, capacity=10):
    response = client.post("/api/v1/workers", headers=operator, json={
        "name": "Independent browser accounts", "platform": "chrome",
        "capabilities": ["gmail.compose"], "accounts": ACCOUNTS,
        "max_parallel": capacity,
    })
    assert response.status_code == 201, response.text
    worker = response.json()
    worker["headers"] = {"Authorization": "Bearer " + worker["worker_token"]}
    response = client.post("/api/v1/worker/heartbeat", headers=worker["headers"],
                           json={"session_id": SESSION})
    assert response.status_code == 200, response.text
    return worker


def queue(client, operator, worker, index, account):
    response = client.post("/api/v1/jobs", headers=operator, json={
        "worker_id": worker["id"], "idempotency_key": f"ten-tab-fixture-{index}",
        "operation": "gmail.compose", "account_email": account,
        "message": {"to": ["recipient@example.test"], "subject": f"Account {index}", "body": "Offline fixture"},
    })
    assert response.status_code == 201, response.text


def claim(client, worker, account, slot):
    response = client.post("/api/v1/worker/claim", headers=worker["headers"], json={
        "session_id": SESSION, "account_email": account, "slot_id": slot,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_ten_account_claim_race_and_all_leases_renew(client, operator, database):
    worker = pair(client, operator)
    for index in range(30):
        queue(client, operator, worker, index, ACCOUNTS[index % 10])

    def concurrent(index):
        # Every request owns an independent database session, as separate HTTP
        # requests do. Repeated claims race for the same ten account/tab slots.
        with database() as db:
            return service.claim(db, worker["id"], Claim(
                session_id=SESSION, slot_id=f"gmail-tab-{index % 10}",
                account_email=ACCOUNTS[index % 10]))

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(concurrent, range(40)))
    leases = [result for result in results if result["job"]]
    jobs = [lease["job"] for lease in leases]
    assert len(jobs) == 10
    assert len({job["id"] for job in jobs}) == 10
    assert {job["account_email"] for job in jobs} == set(ACCOUNTS)
    assert {job["slot_id"] for job in jobs} == {f"gmail-tab-{index}" for index in range(10)}
    assert all(job["message"]["to"] == ["recipient@example.test"] for job in jobs)
    with database() as restarted:
        assert len(restarted.scalars(select(Job).where(Job.state == "leased")).all()) == 10
        assert len(restarted.scalars(select(Job).where(Job.state == "queued")).all()) == 20

    heartbeat = {"session_id": SESSION, "leases": [
        {"job_id": lease["job"]["id"], "lease_token": lease["lease_token"]}
        for lease in leases
    ]}
    response = client.post("/api/v1/worker/heartbeat", headers=worker["headers"], json=heartbeat)
    assert response.status_code == 200, response.text
    assert set(response.json()["renewed_job_ids"]) == {job["id"] for job in jobs}
    # Completing one account releases its slot without changing the nine other
    # accounts or replaying their assignments.
    lease = leases[0]
    report = {"session_id": SESSION, "job_id": lease["job"]["id"],
              "lease_token": lease["lease_token"], "state": "running"}
    assert client.post("/api/v1/worker/report", headers=worker["headers"], json=report).status_code == 200
    report["state"] = "failed"
    assert client.post("/api/v1/worker/report", headers=worker["headers"], json=report).status_code == 200
    replacement = claim(client, worker, lease["job"]["account_email"], lease["job"]["slot_id"])
    assert replacement["job"]["id"] not in {job["id"] for job in jobs}
    with database() as restarted:
        assert len(restarted.scalars(select(Job).where(Job.state == "leased")).all()) == 10


def test_distinct_accounts_and_slots_still_obey_lower_worker_capacity(client, operator):
    worker = pair(client, operator, capacity=2)
    for index in range(4):
        queue(client, operator, worker, index, ACCOUNTS[index % 3])
    assert claim(client, worker, ACCOUNTS[0], "gmail-tab-0")["job"]
    assert claim(client, worker, ACCOUNTS[0], "different-tab")["job"] is None
    assert claim(client, worker, ACCOUNTS[1], "gmail-tab-0")["job"] is None
    assert claim(client, worker, ACCOUNTS[1], "gmail-tab-1")["job"]
    assert claim(client, worker, ACCOUNTS[2], "gmail-tab-2")["job"] is None


@pytest.mark.parametrize("accounts,capacity", [(ACCOUNTS + ["eleven@example.test"], 10), (ACCOUNTS, 11)])
def test_pairing_rejects_more_than_ten_accounts_or_slots(client, operator, accounts, capacity):
    response = client.post("/api/v1/workers", headers=operator, json={
        "name": "Invalid capacity", "platform": "chrome", "capabilities": ["gmail.compose"],
        "accounts": accounts, "max_parallel": capacity,
    })
    assert response.status_code == 422


def test_heartbeat_rejects_more_than_ten_leases(client, operator):
    worker = pair(client, operator)
    response = client.post("/api/v1/worker/heartbeat", headers=worker["headers"], json={
        "session_id": SESSION,
        "leases": [{"job_id": f"fixture-{index}", "lease_token": "x" * 32} for index in range(11)],
    })
    assert response.status_code == 422


@pytest.mark.parametrize("platform,capacity,expected", [("chrome", 7, 7), ("firefox", 10, 10), ("android", 10, 1)])
def test_dashboard_pairs_ten_accounts_with_explicit_browser_capacity(
        client, database, platform, capacity, expected):
    with database() as db:
        user = User(email="operator@example.test", hashed_password="unused", is_admin=True)
        db.add(user)
        db.commit()
        token = create_session_token(user.id)
    client.cookies.set("url_registry_session", token)
    page = client.get("/admin/fleet")
    assert page.status_code == 200
    assert 'name="max_parallel" type="number" min="1" max="10"' in page.text
    csrf = re.search('name="csrf" value="([^"]+)"', page.text).group(1)
    response = client.post("/admin/fleet/pair", data={
        "csrf": csrf, "name": "Ten account browser", "platform": platform,
        "accounts": ",".join(ACCOUNTS), "max_parallel": capacity,
    })
    assert response.status_code == 200, response.text
    with database() as db:
        worker = db.scalar(select(Worker))
        assert worker.accounts == sorted(ACCOUNTS)
        assert worker.max_parallel == expected
