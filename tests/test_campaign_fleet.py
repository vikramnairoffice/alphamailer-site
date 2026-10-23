import datetime as dt

from sqlalchemy import select

from app import fleet_service
from app.fleet_models import (Campaign, CampaignAccountReservation, CampaignAssignment,
                              CampaignLeadIdentity, CampaignPace, Job)
from test_fleet import claim, report


def second_worker(client, operator):
    worker = client.post("/api/v1/workers", headers=operator, json={
        "name": "Second fixture", "platform": "test", "capabilities": ["gmail.compose"],
        "accounts": ["second@example.com"]}).json()
    worker["headers"] = {"Authorization": "Bearer " + worker["worker_token"]}
    assert client.post("/api/v1/worker/heartbeat", headers=worker["headers"],
                       json={"session_id": "fixture-session"}).status_code == 200
    return worker


def manifest(first, second, *, interval=0):
    return {"idempotency_key": "fleet-campaign-fixture", "min_interval_seconds": interval,
            "assignments": [
                {"lead_id": "lead-1", "worker_id": first["id"],
                 "account_email": "account0@example.com", "operation": "gmail.compose",
                 "message": {"to": ["recipient1@example.com"], "subject": "One", "body": "Frozen one"}},
                {"lead_id": "lead-2", "worker_id": first["id"],
                 "account_email": "account0@example.com", "operation": "gmail.compose",
                 "message": {"to": ["recipient2@example.com"], "subject": "Two", "body": "Frozen two"}},
                {"lead_id": "lead-3", "worker_id": second["id"],
                 "account_email": "second@example.com", "operation": "gmail.compose",
                 "message": {"to": ["recipient3@example.com"], "subject": "Three", "body": "Frozen three"}}]}


def test_manifest_is_durable_unique_and_aggregate_is_report_driven(client, operator, paired, database):
    second = second_worker(client, operator)
    body = manifest(paired, second)
    response = client.post("/api/v1/campaigns", headers=operator, json=body)
    assert response.status_code == 201, response.text
    campaign = response.json()
    assert campaign["counts"]["queued"] == 3
    assert len({a["id"] for a in campaign["assignments"]}) == 3
    assert client.post("/api/v1/campaigns", headers=operator, json=body).json()["id"] == campaign["id"]
    changed = manifest(paired, second)
    changed["assignments"][0]["message"]["subject"] = "Changed"
    assert client.post("/api/v1/campaigns", headers=operator, json=changed).status_code == 409
    with database() as restarted:
        assert restarted.get(Campaign, campaign["id"]) is not None
        assert len(restarted.scalars(select(CampaignAssignment)).all()) == 3
    first_lease = claim(client, paired, "account0@example.com").json()
    other_lease = claim(client, second, "second@example.com").json()
    assert first_lease["job"]["message"]["body"] == "Frozen one"
    assert first_lease["job"]["idempotency_key"].startswith("fleet:")
    assert report(client, paired, first_lease, "running").status_code == 200
    assert report(client, paired, first_lease, "succeeded", result={"prepared": True}).status_code == 200
    assert report(client, second, other_lease, "running").status_code == 200
    assert report(client, second, other_lease, "uncertain").status_code == 200
    status = client.get(f"/api/v1/campaigns/{campaign['id']}", headers=operator).json()
    assert status["counts"]["succeeded"] == 1
    assert status["counts"]["uncertain"] == 1
    assert status["counts"]["queued"] == 1
    assert status["state"] == "running"
    cancelled = client.post(f"/api/v1/campaigns/{campaign['id']}/cancel", headers=operator).json()
    assert cancelled["state"] == "uncertain"
    assert cancelled["counts"]["cancelled"] == 1
    assert claim(client, paired, "account0@example.com").json()["job"] is None


def test_campaign_rejects_duplicate_leads_and_cross_worker_account(client, operator, paired):
    second = second_worker(client, operator)
    body = manifest(paired, second)
    body["assignments"][1]["lead_id"] = "lead-1"
    assert client.post("/api/v1/campaigns", headers=operator, json=body).status_code == 422
    body = manifest(paired, second)
    body["assignments"][2]["account_email"] = "account0@example.com"
    assert client.post("/api/v1/campaigns", headers=operator, json=body).status_code == 422
    assert client.get("/api/v1/campaigns", headers=paired["headers"]).status_code == 401


def test_lead_identity_stays_owned_after_campaign_finishes(client, operator, paired, database):
    second = second_worker(client, operator)
    first = client.post("/api/v1/campaigns", headers=operator,
                        json=manifest(paired, second)).json()
    client.post(f"/api/v1/campaigns/{first['id']}/cancel", headers=operator)
    rerun = manifest(paired, second)
    rerun["idempotency_key"] = "another-campaign-key"
    response = client.post("/api/v1/campaigns", headers=operator, json=rerun)
    assert response.status_code == 409
    assert "Lead ID" in response.text
    with database() as db:
        assert len(db.scalars(select(CampaignLeadIdentity)).all()) == 3
        assert len(db.scalars(select(Campaign)).all()) == 1
        # Simulate a campaign written before the identity table was added.
        db.delete(db.get(CampaignLeadIdentity, "lead-1"))
        db.commit()
    assert client.post("/api/v1/campaigns", headers=operator,
                       json=rerun).status_code == 409


def test_account_pace_continues_across_campaigns(client, operator, paired, database):
    second = second_worker(client, operator)
    original = client.post("/api/v1/campaigns", headers=operator,
                           json=manifest(paired, second, interval=60)).json()
    first = claim(client, paired, "account0@example.com").json()
    assert first["job"] is not None
    assert report(client, paired, first, "running").status_code == 200
    assert report(client, paired, first, "succeeded").status_code == 200
    client.post(f"/api/v1/campaigns/{original['id']}/cancel", headers=operator)
    next_body = manifest(paired, second)
    next_body["idempotency_key"] = "second-account-campaign"
    next_body["assignments"] = [next_body["assignments"][0]]
    next_body["assignments"][0]["lead_id"] = "new-lead-1"
    next_campaign = client.post("/api/v1/campaigns", headers=operator,
                                json=next_body)
    assert next_campaign.status_code == 201, next_campaign.text
    # An account cannot be scheduled into another active campaign even when
    # its lead identity and submission key differ.
    overlap = manifest(paired, second)
    overlap["idempotency_key"] = "third-account-campaign"
    overlap["assignments"] = [overlap["assignments"][0]]
    overlap["assignments"][0]["lead_id"] = "new-lead-2"
    assert client.post("/api/v1/campaigns", headers=operator,
                       json=overlap).status_code == 409
    with database() as db:
        reservation = db.get(CampaignAccountReservation, "account0@example.com")
        assert reservation.campaign_id == next_campaign.json()["id"]
    assert claim(client, paired, "account0@example.com").json()["job"] is None
    with database() as db:
        pace = db.scalar(select(CampaignPace).where(CampaignPace.campaign_id == original["id"],
                      CampaignPace.account_email == "account0@example.com"))
        pace.last_claim_at = fleet_service.now() - dt.timedelta(seconds=61)
        db.commit()
    assert claim(client, paired, "account0@example.com").json()["job"] is not None


def test_account_pacing_and_expired_assignment_never_requeues(client, operator, paired, database):
    second = second_worker(client, operator)
    campaign = client.post("/api/v1/campaigns", headers=operator,
                           json=manifest(paired, second, interval=60)).json()
    first = claim(client, paired, "account0@example.com").json()
    report(client, paired, first, "running")
    report(client, paired, first, "succeeded")
    assert claim(client, paired, "account0@example.com").json()["job"] is None
    # A different account continues while this account is paced.
    other = claim(client, second, "second@example.com").json()
    assert other["job"] is not None
    with database() as db:
        job = db.get(Job, other["job"]["id"])
        job.lease_expires_at = fleet_service.now() - dt.timedelta(seconds=1)
        db.commit()
    assert claim(client, second, "second@example.com").json()["job"] is None
    status = client.get(f"/api/v1/campaigns/{campaign['id']}", headers=operator).json()
    assert status["counts"]["uncertain"] == 1


def test_cancel_does_not_relabel_inflight_assignment_as_finished(client, operator, paired):
    second = second_worker(client, operator)
    created = client.post("/api/v1/campaigns", headers=operator,
                          json=manifest(paired, second)).json()
    lease = claim(client, paired, "account0@example.com").json()
    cancelled = client.post(f"/api/v1/campaigns/{created['id']}/cancel", headers=operator).json()
    assert cancelled["state"] == "cancelling"
    assert cancelled["counts"]["leased"] == 1
    assert cancelled["counts"]["cancelled"] == 2
    assert report(client, paired, lease, "uncertain").status_code == 200
    final = client.get(f"/api/v1/campaigns/{created['id']}", headers=operator).json()
    assert final["state"] == "uncertain"
    assert final["counts"]["uncertain"] == 1


def test_mixed_engine_and_browser_assignments_keep_one_campaign_identity(client, operator):
    workers = []
    for name, platform, capability, account in [
        ("Device", "android", "engine.command", "device@example.test"),
        ("Browser", "firefox", "gmail.compose", "browser@example.test")]:
        worker = client.post("/api/v1/workers", headers=operator, json={
            "name": name, "platform": platform, "capabilities": [capability],
            "accounts": [account]}).json()
        worker["headers"] = {"Authorization": "Bearer " + worker["worker_token"]}
        assert client.post("/api/v1/worker/heartbeat", headers=worker["headers"],
                           json={"session_id": "fixture-session"}).status_code == 200
        workers.append(worker)
    manifest = {"idempotency_key": "mixed-fixture-campaign", "assignments": [
        {"lead_id": "android-lead", "worker_id": workers[0]["id"],
         "account_email": "device@example.test", "operation": "engine.command",
         "lead": "recipient1@example.test", "config": {"manual_config": {
             "enabled": True, "subject": "Mixed", "body": "Engine", "body_is_html": False}}},
        {"lead_id": "browser-lead", "worker_id": workers[1]["id"],
         "account_email": "browser@example.test", "operation": "gmail.compose",
         "message": {"to": ["recipient2@example.test"], "subject": "Mixed", "body": "Frozen"}}]}
    campaign = client.post("/api/v1/campaigns", headers=operator, json=manifest).json()
    engine_lease = claim(client, workers[0], "device@example.test").json()
    browser_lease = claim(client, workers[1], "browser@example.test").json()
    params = engine_lease["job"]["engine"]["parameters"]
    assert engine_lease["job"]["engine"]["command"] == "campaign.assignment"
    assert params["campaign_id"] == campaign["id"]
    assert params["assignment_id"] == engine_lease["job"]["idempotency_key"].removeprefix("fleet:")
    assert browser_lease["job"]["message"]["body"] == "Frozen"
    for worker, lease in [(workers[0], engine_lease), (workers[1], browser_lease)]:
        assert report(client, worker, lease, "running").status_code == 200
        assert report(client, worker, lease, "succeeded").status_code == 200
    final = client.get(f"/api/v1/campaigns/{campaign['id']}", headers=operator).json()
    assert final["state"] == "succeeded"
    assert final["counts"]["succeeded"] == 2


def test_direct_job_cannot_bypass_fleet_assignment_ownership(client, operator):
    worker = client.post("/api/v1/workers", headers=operator, json={
        "name": "Device", "platform": "android", "capabilities": ["engine.command"],
        "accounts": ["device@example.test"]}).json()
    response = client.post("/api/v1/jobs", headers=operator, json={
        "idempotency_key": "bypass-campaign-job", "worker_id": worker["id"],
        "operation": "engine.command", "account_email": "device@example.test",
        "engine": {"command": "campaign.assignment", "parameters": {}}})
    assert response.status_code == 422
    manifest = {"idempotency_key": "ownership-fleet", "assignments": [
        {"lead_id": "lead-1", "worker_id": worker["id"],
         "account_email": "device@example.test", "operation": "engine.command",
         "lead": "recipient@example.test", "config": {"manual_config": {
             "enabled": True, "subject": "Preview", "body": "Body", "body_is_html": False}}}]}
    assert client.post("/api/v1/campaigns", headers=operator, json=manifest).status_code == 201
    standalone = {"idempotency_key": "standalone-overlap", "worker_id": worker["id"],
                  "operation": "engine.command", "account_email": "device@example.test",
                  "engine": {"command": "campaign.start", "parameters": {"leads": ["recipient@example.test"]}}}
    assert client.post("/api/v1/jobs", headers=operator, json=standalone).status_code == 409
    campaign_id = client.get("/api/v1/campaigns", headers=operator).json()[0]["id"]
    client.post(f"/api/v1/campaigns/{campaign_id}/cancel", headers=operator)
    assert client.post("/api/v1/jobs", headers=operator, json=standalone).status_code == 201
    manifest["idempotency_key"] = "ownership-fleet-2"
    assert client.post("/api/v1/campaigns", headers=operator, json=manifest).status_code == 409
